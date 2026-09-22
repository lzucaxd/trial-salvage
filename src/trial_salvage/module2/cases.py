"""Build a module-2 case: reference sequence, verified numbering, tiling, variant panel.

Two data sources, both retrieved rather than hardcoded:
  UniProt REST          -- canonical sequence, isoform, checksums, domain features
  EBI Proteins API      -- variation records aggregating ClinVar, COSMIC, dbSNP, gnomAD

Numbering is the part that silently breaks a variant pipeline. Literature nomenclature does not
agree with UniProt precursor numbering for every gene: SOD1 is +1 (initiator Met cleaved, so the
canonical A4V is position 5), APOE is +18 (signal peptide, so the epsilon-4 C112R is position
130), BRCA1/BRCA2/EGFR are identity. Every case therefore carries an explicit offset and a list
of assertions checked against the actual residue.
"""
from __future__ import annotations

import hashlib
import json
import urllib.request
from pathlib import Path

from .tiling import ESM1V_WINDOW, make_tiles

AA20 = list("ACDEFGHIKLMNPQRSTVWY")
UNIPROT = "https://rest.uniprot.org/uniprotkb/{acc}.json"
EBI_VAR = "https://www.ebi.ac.uk/proteins/api/variation/{acc}"
TIMEOUT = 180


def _get_json(url: str, cache: Path | None) -> dict:
    if cache is not None and cache.exists():
        return json.loads(cache.read_text())
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as fh:
        data = json.loads(fh.read().decode())
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_text(json.dumps(data))
    return data


def fetch_reference(acc: str, cache_dir: Path | None = None) -> dict:
    cache = None if cache_dir is None else Path(cache_dir) / f"uniprot_{acc}.json"
    rec = _get_json(UNIPROT.format(acc=acc), cache)
    seq = rec["sequence"]["value"]
    return {
        "uniprot": acc, "isoform": f"{acc}-1 (canonical)", "sequence": seq, "length": len(seq),
        "sequence_version": rec["entryAudit"]["sequenceVersion"], "crc64": rec["sequence"]["crc64"],
        "sha256": hashlib.sha256(seq.encode()).hexdigest(),
        "features": [{"type": f["type"], "description": f.get("description", ""),
                       "start": f["location"]["start"]["value"], "end": f["location"]["end"]["value"]}
                  for f in rec.get("features", [])],
    }


def verify_numbering(sequence: str, checks: list[tuple[str, int, str]]) -> list[dict]:
    """Assert that each (literature_label, uniprot_position, expected_residue) triple holds.

    Raises ValueError on the first mismatch: a numbering error invalidates every downstream score,
    so this is a hard failure rather than a warning.
    """
    out = []
    for label, pos, expected in checks:
        if not 1 <= pos <= len(sequence):
            raise ValueError(f"{label}: position {pos} outside 1..{len(sequence)}")
        got = sequence[pos - 1]
        if got != expected:
            raise ValueError(f"numbering check failed: {label} -> position {pos} expected {expected}, got {got}")
        out.append({"literature_label": label, "uniprot_position": pos, "residue": got, "verified": True})
    return out


def parse_missense(acc: str, sequence: str, cache_dir: Path | None = None) -> dict:
    """Retrieved single-residue substitutions keyed by (position, wt, mut).

    Records whose wild-type residue disagrees with the reference sequence are dropped, which also
    filters variants annotated against a different isoform.
    """
    cache = None if cache_dir is None else Path(cache_dir) / f"ebi_variation_{acc}.json"
    var = _get_json(EBI_VAR.format(acc=acc), cache)
    recs: dict[tuple[int, str, str], dict] = {}
    for f in var.get("features", []):
        if f.get("type") != "VARIANT":
            continue
        wt, mut = f.get("wildType"), f.get("mutatedType")
        try:
            begin, end = int(f["begin"]), int(f["end"])
        except (KeyError, ValueError, TypeError):
            continue
        if begin != end or not wt or not mut or wt not in AA20 or mut not in AA20 or wt == mut:
            continue
        if not 1 <= begin <= len(sequence) or sequence[begin - 1] != wt:
            continue
        r = recs.setdefault((begin, wt, mut), {
            "position": begin, "wt_aa": wt, "mut_aa": mut, "clinical_significance": set(), "review_status": set(),
            "diseases": set(), "descriptions": set(), "rsids": set(), "cosmic": set(), "pubmed": set(),
            "polyphen": [], "sift": [], "max_population_frequency": 0.0})
        for cs in f.get("clinicalSignificances") or []:
            r["clinical_significance"].add(cs.get("type"))
            if cs.get("reviewStatus"):
                r["review_status"].add(cs["reviewStatus"])
        for d in f.get("descriptions") or []:
            if d.get("value"):
                r["descriptions"].add(d["value"])
        for assoc in f.get("association") or []:
            if assoc.get("name"):
                r["diseases"].add(assoc["name"])
            for db in assoc.get("dbReferences") or []:
                if (db.get("name") or "").lower() == "pubmed":
                    r["pubmed"].add(db.get("id"))
        for ev in f.get("evidences") or []:
            src = ev.get("source") or {}
            if (src.get("name") or "").lower() == "pubmed":
                r["pubmed"].add(src.get("id"))
        for x in f.get("xrefs") or []:
            name, xid = (x.get("name") or "").lower(), x.get("id") or ""
            if name.startswith("dbsnp") or xid.startswith("rs"):
                r["rsids"].add(xid)
            elif "cosmic" in name:
                r["cosmic"].add(xid)
        for pred in f.get("predictions") or []:
            alg = pred.get("predAlgorithmNameType") or ""
            if pred.get("score") is not None:
                if "PolyPhen" in alg:
                    r["polyphen"].append(float(pred["score"]))
                elif "SIFT" in alg:
                    r["sift"].append(float(pred["score"]))
        for pf in f.get("populationFrequencies") or []:
            try:
                r["max_population_frequency"] = max(r["max_population_frequency"],
                                                    float(pf.get("frequency") or 0))
            except (TypeError, ValueError):
                pass
    return recs


def build_case(case_id: str, gene: str, acc: str, *, drug_id: str | None, drug_target: str,
               relationship: str, numbering_checks: list[tuple[str, int, str]],
               numbering_note: str, literature_offset: int, indication: str | None = None,
               cache_dir: Path | None = None, window: int = ESM1V_WINDOW) -> dict:
    ref = fetch_reference(acc, cache_dir)
    verified = verify_numbering(ref["sequence"], numbering_checks)
    tiles, assignment = make_tiles(ref["length"], window=window)
    return dict(
        case_id=case_id, selection_gene=gene, drug_id=drug_id, drug_target=drug_target,
        selection_target_relationship=relationship, indication=indication,
        numbering=f"UniProt {acc} canonical precursor numbering",
        numbering_note=numbering_note, literature_offset=literature_offset,
        numbering_checks=verified, tiles=[list(t) for t in tiles], n_tiles=len(tiles),
        assignment={str(k): v for k, v in assignment.items()},
        positions=list(range(1, ref["length"] + 1)), window=window, **ref)
