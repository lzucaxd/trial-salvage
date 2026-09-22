#!/usr/bin/env python
"""Score one module-2 case with ESM-1v on a GPU and write the tables module 2 reads offline.

Needs torch + transformers + a GPU; not exercised by CI. The runs behind the committed tables
under data/module2 were executed on Modal A10G sandboxes, one per model shard (~95 s for SOD1's
154 positions up to ~720 s for BRCA2's 3418 positions across 5 overlapping windows).

    python scripts/score_module2_case.py --gene BRCA2 --uniprot P51587 \
        --case-id CASE-BRCA2-OLA-OV-005 --drug olaparib --drug-target PARP1 \
        --relationship synthetic_lethality --outdir data/module2 --overlap-qc

Numbering checks are mandatory: pass --check "D2723H:2723:D" for each literature label you rely
on. The run aborts if any expected residue does not match the reference sequence.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from trial_salvage.module2 import evaluate, scoring
from trial_salvage.module2.cases import build_case, parse_missense


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--gene", required=True)
    ap.add_argument("--uniprot", required=True)
    ap.add_argument("--case-id", required=True)
    ap.add_argument("--drug")
    ap.add_argument("--drug-target", required=True)
    ap.add_argument("--relationship", default="same_protein_drug_target")
    ap.add_argument("--indication")
    ap.add_argument("--check", action="append", default=[],
                    help='numbering assertion "LABEL:POSITION:RESIDUE", repeatable')
    ap.add_argument("--literature-offset", type=int, default=0)
    ap.add_argument("--numbering-note", default="")
    ap.add_argument("--models", default=",".join(scoring.ESM1V_MODELS))
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--overlap-qc", action="store_true")
    ap.add_argument("--cache-dir", default="data/raw/module2")
    ap.add_argument("--outdir", default="data/module2")
    a = ap.parse_args(argv)

    checks = []
    for spec in a.check:
        label, pos, residue = spec.split(":")
        checks.append((label, int(pos), residue))
    case = build_case(a.case_id, a.gene, a.uniprot, drug_id=a.drug, drug_target=a.drug_target,
                      relationship=a.relationship, numbering_checks=checks,
                      numbering_note=a.numbering_note, literature_offset=a.literature_offset,
                      indication=a.indication, cache_dir=Path(a.cache_dir))
    print(f"{a.gene}: {case['length']} aa, {case['n_tiles']} tile(s) {case['tiles']}, "
          f"{len(checks)} numbering check(s) passed")

    matrices, meta = scoring.score_case(case, a.models.split(","), batch=a.batch,
                                        overlap_qc=a.overlap_qc)
    scores = evaluate.score_frame(case["positions"], matrices, case["sequence"])
    missense = parse_missense(a.uniprot, case["sequence"], cache_dir=Path(a.cache_dir))
    annotated = evaluate.annotate(scores, missense, a.gene)

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    keep = [c for c in ("variant_id", "position_uniprot", "wt_aa", "mut_aa", "esm1v_ensemble",
                        "esm1v_member_sd", "position_mean", "residual", "clinvar_class", "polyphen",
                        "sift", "max_population_frequency") if c in annotated.columns]
    subset = annotated[annotated.clinvar_class.ne("unannotated")][keep].round(4)
    subset.insert(0, "selection_gene", a.gene)
    subset.to_csv(outdir / f"{a.gene.lower()}_annotated_scores.csv.gz", index=False, compression="gzip")
    positions = annotated.groupby("position_uniprot").agg(
        wt_aa=("wt_aa", "first"), mean_score=("esm1v_ensemble", "mean"),
        min_score=("esm1v_ensemble", "min"), max_score=("esm1v_ensemble", "max")).round(4).reset_index()
    positions.insert(0, "selection_gene", a.gene)
    positions.to_csv(outdir / f"{a.gene.lower()}_position_constraint.csv.gz", index=False,
                     compression="gzip")
    (outdir / f"{a.gene.lower()}_run_meta.json").write_text(json.dumps({
        "case_id": a.case_id, "selection_gene": a.gene, "uniprot": a.uniprot, "length": case["length"],
        "sha256": case["sha256"], "crc64": case["crc64"], "sequence_version": case["sequence_version"],
        "numbering": case["numbering"], "numbering_note": case["numbering_note"],
        "literature_offset": case["literature_offset"], "numbering_checks": case["numbering_checks"],
        "tiles": case["tiles"], "n_tiles": case["n_tiles"], "per_model": meta}, indent=1))

    validation = evaluate.validate(annotated)
    gate = evaluate.verdict(validation)
    print(f"verdict: {gate['verdict']} -- {gate['reason']}")
    print(pd.Series({k: v["auroc"] for k, v in validation["matched_subset"].items()
                     if isinstance(v, dict)}).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
