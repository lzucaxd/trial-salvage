"""Module 2 -- protein variants and ESM.

OWNER: module 2. Consumes either an asset config (config/assets/*.yaml) or module 1's handoff
(``handoff.module2`` of outputs/module1/module1_output.json).

Contract
--------
Input : --config config/assets/<asset>.yaml  (uniprot + gene + drug, the same file every module
        reads), or --module1 outputs/module1/module1_output.json for the handoff path.
Output: outputs/module2/module2_output.json conforming to schemas/module2_output.schema.json.

What this module does and does not claim
----------------------------------------
It scores every single-residue substitution in a selection gene with an ESM-1v five-model
ensemble (masked marginals) and validates those scores against independently retrieved ClinVar
labels. It then emits an ``applicability.verdict`` decided by measured performance. Across the six
genes scored so far the verdict is ``rank_residues_only`` on two and ``do_not_rank`` or
``not_validated`` on four, so a consumer must read the verdict before the scores.

The selection gene is NOT assumed to be the drug target. ``target_id`` stays the drug target, so
module 4's chemistry handoff is unchanged, and ``selection_gene_id`` says where the variants live.
For olaparib the variants are in BRCA1/BRCA2 while the drug target is PARP1 (synthetic lethality).

--offline reads the committed tables under data/module2 and needs no network and no GPU; that is
the path CI and a clean clone take. Scoring from scratch needs a GPU: see
scripts/score_module2_case.py.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import pandas as pd

from . import evaluate

SCHEMA_VERSION = "2.0"


def _article(modality: str | None) -> str:
    text = modality or "non-small-molecule agent"
    return f"{'an' if text[:1].lower() in 'aeiou' else 'a'} {text}"
DATA_DIR = Path("data/module2")
SOURCES = {
    "uniprot": "UniProt (reviewed, Swiss-Prot), rest.uniprot.org",
    "variation": "EBI Proteins API variation endpoint (aggregates ClinVar, COSMIC, dbSNP, gnomAD)",
    "chembl": "ChEMBL REST API, www.ebi.ac.uk/chembl",
}
MECHANISM_NOTE = (
    "ESM scores evolutionary plausibility. It has no access to gain-of-function, misfolding or "
    "aggregation mechanisms and cannot infer the direction of a functional effect. SOD1-ALS "
    "(misfolding) scored at chance and APOE epsilon-4 -- the ancestral mammalian residue and the "
    "strongest common risk allele in Alzheimer disease -- scored as more plausible than wild type."
)
LIMITATIONS = [
    ("Single-residue substitutions only. In-frame deletions and insertions (including EGFR exon-19 "
    "deletions and exon-20 insertions), nonsense/stop and splice variants are not scored and are "
    "absent from this file, so a consumer must not read absence as evidence of tolerance."),
    ("ClinVar is not a fully independent benchmark: ACMG interpretation formally admits computational "
    "evidence, so the reported discrimination is likely optimistic. Restricting to variants with "
    "submitted review criteria left it essentially unchanged, so the circularity is structural."),
    ("The substitution-specific residual carried no reliable signal in any case with a validation set "
    "(EGFR 0.463, BRCA1 0.390, BRCA2 0.410 -- all at or below chance). Use the score to rank "
    "residues, not substitutions at a residue."),
    ("Scores are in log-probability-ratio units. Do not average them with pChEMBL values, germline "
    "burden scores or any other model output."),
    "Structural similarity to the reference drug carries no efficacy claim.",
]


def resolve_case(args) -> dict:
    if args.config:
        import yaml
        cfg = yaml.safe_load(Path(args.config).read_text())
        gene = cfg["target"]["symbol"]
        return {
            "case_id": cfg.get("case_id") or f"{cfg['asset']['name']}-{gene}",
            "selection_gene": cfg.get("selection_gene", {}).get("symbol", gene),
            "selection_uniprot": cfg.get("selection_gene", {}).get("uniprot", cfg["target"]["uniprot"]),
            "drug_id": cfg["asset"]["name"], "drug_chembl_id": cfg["asset"].get("chembl_id"),
            "drug_modality": cfg["asset"].get("modality"), "target_id": gene,
            "target_uniprot": cfg["target"]["uniprot"],
            "selection_target_relationship": cfg.get("selection_gene", {}).get("relationship",
                                                                            "same_protein_drug_target"),
            "indication": cfg.get("disease", {}).get("name")}
    payload = json.loads(Path(args.module1).read_text())
    handoff = payload["handoff"]["module2"]
    gene = handoff["gene"]
    return {"case_id": f"{payload.get('asset', 'asset')}-{gene}", "selection_gene": gene,
                "selection_uniprot": handoff["uniprot"], "drug_id": payload.get("asset"),
                "drug_chembl_id": None, "drug_modality": None, "target_id": gene,
                "target_uniprot": handoff["uniprot"],
                "selection_target_relationship": "same_protein_drug_target",
                "indication": payload.get("disease"), "module1_handoff": handoff}


def load_offline(gene: str, data_dir: Path = DATA_DIR) -> tuple[pd.DataFrame, pd.DataFrame]:
    scores = data_dir / f"{gene.lower()}_annotated_scores.csv.gz"
    positions = data_dir / f"{gene.lower()}_position_constraint.csv.gz"
    if not scores.exists():
        available = sorted(p.name.split("_")[0] for p in data_dir.glob("*_annotated_scores.csv.gz"))
        raise SystemExit(f"no committed scores for {gene}. Available: {', '.join(available) or 'none'}. "
                         f"Score it on a GPU first: scripts/score_module2_case.py --gene {gene}")
    return pd.read_csv(scores), pd.read_csv(positions)


def build_output(case: dict, scored: pd.DataFrame, positions: pd.DataFrame, *,
                 analogs: pd.DataFrame | None = None) -> dict:
    validation = evaluate.validate(scored, position_constraint=positions)
    gate = evaluate.verdict(validation)
    constrained = positions.nsmallest(15, "mean_score")
    tolerant = positions.nlargest(15, "mean_score")
    analog_block = None
    if analogs is not None and len(analogs):
        ref = analogs[analogs.is_reference]
        mutant = int((analogs.n_mutant_genotypes > 0).sum())
        analog_block = {
            "reference_drug": case["drug_id"], "drug_chembl_id": case.get("drug_chembl_id"),
            "drug_target": case["target_id"], "n_analogs": len(analogs),
            "n_with_target_potency": int((analogs.target_wt_n_measurements > 0).sum()),
            "n_with_any_mutant_genotype_data": mutant,
            "reference_target_median_pchembl": (None if not len(ref) else
                                             ref.target_wt_median_pchembl.iloc[0]),
            "note": ("for a synthetic-lethality case the analog branch is scored against the drug target "
                  "while the variant branch is scored on the selection gene; the two are different "
                  "proteins and cannot be joined at the variant level"
                  if case["selection_target_relationship"] == "synthetic_lethality" else None),
            "evidence_type": "observed_assay + computed_descriptor", "source": SOURCES["chembl"]}
    return {
        "schema_version": SCHEMA_VERSION, "module": "module2_protein_variants_esm",
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "case_id": case["case_id"], "drug_id": case.get("drug_id"), "target_id": case["target_id"],
        "selection_gene_id": case["selection_gene"],
        "selection_target_relationship": case["selection_target_relationship"],
        "indication": case.get("indication"),
        "applicability": {
            "variant_branch": "applicable",
            "analog_branch": "applicable" if analog_block else "not_applicable",
            "analog_branch_reason": (None if analog_block else
                                  f"{case.get('drug_id')} is {_article(case.get('drug_modality'))}; "
                                  f"no small-molecule structure exists, so no analog set can be built"),
            "verdict": gate["verdict"], "verdict_reason": gate["reason"],
            "verdict_rule": "do_not_rank if a classical predictor (PolyPhen/SIFT) beats ESM-1v on the "
                         "matched subset of variants all three cover, or if ESM AUROC <= 0.60; "
                         "not_validated if too few benign-classified variants exist to measure "
                         "discrimination; otherwise rank_residues_only.",
            "scope_exclusions": ["single-residue substitutions only"]},
        "reference_sequence": {"uniprot": case["selection_uniprot"], "source": SOURCES["uniprot"]},
        "model_version": {
            "protocol": "masked marginals (Meier et al. 2021, NeurIPS)",
            "primary_score": "esm1v_ensemble = mean of five ESM-1v masked-marginal scores",
            "models": [f"facebook/esm1v_t33_650M_UR90S_{i}" for i in range(1, 6)],
            "compute": "Modal A10G, one sandbox per model shard"},
        "validation": validation,
        "disease_mechanism": {"relevance": MECHANISM_NOTE, "evidence_type": "curated_literature",
                               "source": "curated by module author; not retrieved from a database"},
        "saturation_scan": {
            "positions_scanned": len(positions),
            "substitutions_scored": int(validation["n_substitutions_scored"]),
            "most_constrained_positions": constrained.to_dict("records"),
            "most_tolerant_positions": tolerant.to_dict("records")},
        "analogs": analog_block,
        "handoff": {
            "to": "module4",
            "read_verdict_first": "applicability.verdict is decided by measured performance. On "
                               "do_not_rank or not_validated, do not use these scores to rank "
                               "variants; the residue-level constraint map may still be used.",
            "score_units_warning": "log-probability-ratio units; never average with pChEMBL or "
                                "germline burden scores",
            "join_keys": ["case_id", "drug_id", "target_id", "selection_gene_id", "variant_id"]},
        "limitations": LIMITATIONS}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Module 2 -- ESM variant scoring with an applicability gate")
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--config", help="asset config, e.g. config/assets/gefitinib.yaml")
    src.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--selection-gene",
                    help="override the config's selection gene (olaparib has two: BRCA1 and BRCA2)")
    ap.add_argument("--outdir", default="outputs/module2")
    ap.add_argument("--data-dir", default=str(DATA_DIR))
    ap.add_argument("--offline", action="store_true",
                    help="read committed score tables instead of computing (no network, no GPU)")
    ap.add_argument("--analogs", action="store_true", help="also run the ChEMBL analog branch (network)")
    a = ap.parse_args(argv)

    case = resolve_case(a)
    if a.selection_gene:
        case["selection_gene"] = a.selection_gene
        case["case_id"] = f"{case['case_id']}-{a.selection_gene}"
    if not a.offline:
        raise SystemExit(
            "online scoring needs a GPU and is not run from this CLI. Score the case with "
            "scripts/score_module2_case.py, commit the tables under data/module2, then re-run "
            "with --offline. Everything reported in docs/module2_esm_variant_scoring.md is "
            "reproducible from the committed tables.")
    scored, positions = load_offline(case["selection_gene"], Path(a.data_dir))
    analogs = None
    if a.analogs and case.get("drug_chembl_id"):
        from .analogs import analog_table
        analogs = analog_table(case["drug_chembl_id"], case["target_uniprot"])
    out = build_output(case, scored, positions, analogs=analogs)

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    path = outdir / "module2_output.json"
    path.write_text(json.dumps(out, indent=1))
    schema = Path("schemas/module2_output.schema.json")
    if schema.exists():
        import jsonschema
        jsonschema.validate(out, json.loads(schema.read_text()))
        print(f"validated against {schema}")
    print(f"wrote {path}")
    print(f"case {out['case_id']}: selection gene {out['selection_gene_id']} / drug target "
          f"{out['target_id']} ({out['selection_target_relationship']})")
    print(f"verdict: {out['applicability']['verdict']} -- {out['applicability']['verdict_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
