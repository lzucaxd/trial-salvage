"""Structural-analog branch: ChEMBL similarity search against the DRUG TARGET.

For a same-protein case (gefitinib/EGFR) the analog branch and the variant branch describe one
protein. For a synthetic-lethality case (olaparib: variants in BRCA1/BRCA2, drug target PARP1)
they describe different proteins and cannot be joined at the variant level at all -- across 209
PARP1 assays none carries a variant annotation, whereas EGFR assays annotate the mutation on the
assay record via ``variant_sequence``.

RDKit is optional: without it the ChEMBL similarity ranking is still returned, only the
independent fingerprint and scaffold columns are omitted.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

import pandas as pd

CHEMBL = "https://www.ebi.ac.uk/chembl/api/data"
TIMEOUT = 180
POTENCY_TYPES = ("IC50", "Ki", "Kd")


def _get(path: str, **params) -> dict:
    url = f"{CHEMBL}/{path}?" + urllib.parse.urlencode({**params, "format": "json"})
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as fh:
        return json.loads(fh.read().decode())


def _paged(path: str, key: str, cap: int = 8000, **params) -> list:
    got: list = []
    while True:
        page = _get(path, offset=len(got), limit=1000, **params)
        got += page[key]
        if not (page.get("page_meta") or {}).get("next") or len(got) >= cap or not page[key]:
            return got


def target_chembl_id(uniprot: str) -> str:
    targets = _get("target", target_components__accession=uniprot, organism="Homo sapiens",
                   target_type="SINGLE PROTEIN")["targets"]
    if not targets:
        raise ValueError(f"no single-protein ChEMBL target for {uniprot}")
    return targets[0]["target_chembl_id"]


def _rdkit():
    try:
        from rdkit import Chem, RDLogger
        from rdkit.Chem import DataStructs, Descriptors, rdFingerprintGenerator
        from rdkit.Chem.Scaffolds import MurckoScaffold
    except ImportError:
        return None
    RDLogger.DisableLog("rdApp.*")
    return {"Chem": Chem, "DataStructs": DataStructs, "Descriptors": Descriptors,
                "MurckoScaffold": MurckoScaffold,
                "gen": rdFingerprintGenerator.GetMorganGenerator(radius=2, fpSize=2048)}


def analog_table(drug_chembl_id: str, target_uniprot: str, *, similarity: int = 70) -> pd.DataFrame:
    """Analogs at >= ``similarity``% with per-EGFR-genotype potency where ChEMBL annotates it."""
    rd = _rdkit()
    ref = _get(f"molecule/{drug_chembl_id}")
    smiles = ref["molecule_structures"]["canonical_smiles"]
    target = target_chembl_id(target_uniprot)
    hits = _paged(f"similarity/{urllib.parse.quote(smiles, safe='')}/{similarity}", "molecules", cap=1200)
    ids = [m["molecule_chembl_id"] for m in hits]
    acts: list = []
    for i in range(0, len(ids), 15):
        acts += _paged("activity", "activities", molecule_chembl_id__in=",".join(ids[i:i + 15]),
                       target_chembl_id=target)
    assay_ids = sorted({a["assay_chembl_id"] for a in acts})
    assays: list = []
    for i in range(0, len(assay_ids), 20):
        assays += _get("assay", assay_chembl_id__in=",".join(assay_ids[i:i + 20]), limit=1000)["assays"]
    genotype = {a["assay_chembl_id"]: ((a.get("variant_sequence") or {}).get("mutation") or "wild-type")
                for a in assays}
    potency: dict = {}
    for a in acts:
        if a.get("pchembl_value") and a.get("standard_type") in POTENCY_TYPES:
            k = (a["molecule_chembl_id"], genotype.get(a["assay_chembl_id"], "wild-type"))
            potency.setdefault(k, []).append(float(a["pchembl_value"]))
    ref_fp = ref_scaffold = None
    if rd:
        ref_mol = rd["Chem"].MolFromSmiles(smiles)
        ref_fp = rd["gen"].GetFingerprint(ref_mol)
        ref_scaffold = rd["MurckoScaffold"].MurckoScaffoldSmiles(mol=ref_mol)
    rows = []
    for m in hits:
        struct = m.get("molecule_structures") or {}
        smi = struct.get("canonical_smiles")
        if not smi:
            continue
        mid = m["molecule_chembl_id"]
        wt = potency.get((mid, "wild-type"), [])
        mutants = sorted({g for (mm, g) in potency if mm == mid and g != "wild-type"})
        row = {"reference_drug_chembl_id": drug_chembl_id, "drug_target_uniprot": target_uniprot,
                   "drug_target_chembl_id": target, "molecule_chembl_id": mid, "pref_name": m.get("pref_name"),
                   "max_phase": m.get("max_phase"), "is_reference": mid == drug_chembl_id,
                   "canonical_smiles": smi, "inchikey": struct.get("standard_inchi_key"),
                   "chembl_similarity_pct": round(float(m["similarity"]), 2),
                   "target_wt_median_pchembl": round(pd.Series(wt).median(), 2) if wt else None,
                   "target_wt_n_measurements": len(wt),
                   "mutant_genotypes_assayed": "; ".join(mutants) or None,
                   "n_mutant_genotypes": len(mutants)}
        if rd:
            mol = rd["Chem"].MolFromSmiles(smi)
            if mol is not None:
                scaffold = rd["MurckoScaffold"].MurckoScaffoldSmiles(mol=mol)
                row.update(
                    rdkit_tanimoto_ecfp4=round(rd["DataStructs"].TanimotoSimilarity(
                        ref_fp, rd["gen"].GetFingerprint(mol)), 4),
                    murcko_scaffold=scaffold, shares_reference_scaffold=scaffold == ref_scaffold,
                    mw=round(rd["Descriptors"].MolWt(mol), 2),
                    clogp=round(rd["Descriptors"].MolLogP(mol), 2))
        rows.append(row)
    return pd.DataFrame(rows).sort_values("chembl_similarity_pct", ascending=False).reset_index(drop=True)
