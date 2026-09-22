"""Small clients for Open Targets, Reactome and cBioPortal (all open, no auth).

Schema notes (Sep 2026): Open Targets ``Drug`` has ``maximumClinicalStage`` (not ``maximumClinicalTrialPhase``) and
no ``isApproved`` / ``hasBeenWithdrawn``; ``synonyms`` / ``tradeNames`` need a ``{ label }`` sub-selection.
cBioPortal sample-list objects carry no ``sampleCount`` -- use ``/studies/{id}/samples`` for the denominator.
"""
from __future__ import annotations

import json
import re

import requests

OT = "https://api.platform.opentargets.org/api/v4/graphql"
REACTOME = "https://reactome.org/ContentService"
CBIO = "https://www.cbioportal.org/api"


# ---------------------------------------------------------------- Open Targets
def _ot(query: str, variables: dict | None = None) -> dict:
    js = requests.post(OT, json={"query": query, "variables": variables or {}}, timeout=120).json()
    if "data" not in js:
        raise RuntimeError(str(js.get("errors"))[:300])
    return js["data"]


def search_drug(name: str) -> dict | None:
    q = 'query($q: String!) { search(queryString: $q, entityNames: ["drug"], page: {index: 0, size: 1}) ' \
        '{ hits { id name } } }'
    hits = _ot(q, {"q": name})["search"]["hits"]
    return hits[0] if hits else None


def drug_record(chembl_id: str) -> dict | None:
    q = """query($id: String!) { drug(chemblId: $id) { id name maximumClinicalStage drugType
      synonyms { label } tradeNames { label }
      mechanismsOfAction { rows { mechanismOfAction actionType targets { id approvedSymbol } } } } }"""
    return _ot(q, {"id": chembl_id})["drug"]


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def name_matches(query: str, rec: dict | None) -> bool:
    """Guard against fuzzy-search false hits (e.g. '0.9% sodium chloride' -> MIDAZOLAM).

    Accept only when the query equals, contains, or is contained in the drug's name, a synonym or a trade name.
    Code names (abx464 -> obefazimod) pass through the synonym list.
    """
    if not rec:
        return False
    qn = _norm(query)
    pool = [rec["name"]] + [x["label"] for x in rec.get("synonyms") or []] + \
           [x["label"] for x in rec.get("tradeNames") or []]
    for p in pool:
        pn = _norm(p)
        if pn and (pn == qn or (len(pn) >= 5 and pn in qn) or (len(qn) >= 5 and qn in pn)):
            return True
    return False


def drug_targets(rec: dict) -> list[str]:
    rows = (rec.get("mechanismsOfAction") or {}).get("rows") or []
    return sorted({t["approvedSymbol"] for r in rows for t in r.get("targets") or []})


# ---------------------------------------------------------------- Reactome
def pathways_for_gene(ensembl_id: str) -> list[dict]:
    r = requests.get(f"{REACTOME}/data/mapping/ENSEMBL/{ensembl_id}/pathways", params={"species": 9606},
                     timeout=60)
    return r.json() if r.ok else []


def pathway_genes(st_id: str) -> list[str]:
    r = requests.get(f"{REACTOME}/data/participants/{st_id}/referenceEntities", timeout=90)
    r.raise_for_status()
    return sorted({e["geneName"][0] for e in r.json()
                   if e.get("databaseName") == "UniProt" and e.get("geneName")})


# ---------------------------------------------------------------- cBioPortal
def somatic_mutations(study_id: str, entrez_id: int) -> list[dict]:
    r = requests.post(f"{CBIO}/molecular-profiles/{study_id}_mutations/mutations/fetch",
                      params={"projection": "DETAILED"},
                      json={"sampleListId": f"{study_id}_sequenced", "entrezGeneIds": [entrez_id]}, timeout=120)
    r.raise_for_status()
    return r.json()


def study_sample_count(study_id: str) -> int:
    r = requests.get(f"{CBIO}/studies/{study_id}/samples", timeout=120)
    r.raise_for_status()
    return len(r.json())


def somatic_frequency(study_id: str, entrez_id: int, protein_changes: list[str]) -> dict:
    """Fraction of all samples in the study carrying each protein change (samples, not mutation calls)."""
    muts = somatic_mutations(study_id, entrez_id)
    n = study_sample_count(study_id)
    by_change: dict[str, set] = {}
    for m in muts:
        by_change.setdefault(m.get("proteinChange"), set()).add(m["sampleId"])
    out = {"study": study_id, "n_samples": n,
           "any_mutation": len({m["sampleId"] for m in muts}) / n if n else None}
    out["variants"] = {p: {"n": len(by_change.get(p, ())), "freq": len(by_change.get(p, ())) / n if n else None}
                       for p in protein_changes}
    return out


def dump(obj, path) -> None:
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1)
