"""Score a raw target table with the v1 germline stratification score (offline, no network).

Usage
-----
python -m trial_salvage.module3.score_targets --in RAW.csv --out SCORED.csv [--syn-excess 1.35]

Input contract (CSV, one row per gene symbol)
---------------------------------------------
required : symbol, LOEUF, exp_mis, exp_syn, n_common_func
optional : obs_syn  -- enables the synonymous-excess QC gate; without it qc_syn_excess is empty and no gene is demoted
any other column is passed through unchanged. Empty cells mean "missing"; such rows are kept with empty scores.
LOEUF / exp_* / obs_syn come from ``gnomad.gene_constraint`` (gnomAD v4 constraint); n_common_func from
``germline.summarize_variants`` (common = folded MAF > 1 %, functional = missense / LoF / inframe).

Output
------
The input columns plus rate_syn, rate_mis, oe_syn, qc_syn_excess, tolerance, burden_v1, score_v1, rank_v1, sorted by
rank_v1 (1 = most stratifiable). Input columns with these names are overwritten. See germline.stratification_scores_v1
and docs/module3_normalization.md for the definition and its validation.
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from trial_salvage.module3.germline import SYN_EXCESS_OE, stratification_scores_v1

REQUIRED = ("symbol", "LOEUF", "exp_mis", "exp_syn", "n_common_func")
ADDED = ("rate_syn", "rate_mis", "oe_syn", "qc_syn_excess", "tolerance", "burden_v1", "score_v1", "rank_v1")


def score_table(df: pd.DataFrame, syn_excess: float = SYN_EXCESS_OE) -> pd.DataFrame:
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"input lacks required column(s): {', '.join(missing)}")
    base = df.drop(columns=[c for c in ADDED if c in df.columns])
    rows = base.astype(object).where(base.notna(), None).to_dict("records")
    out = pd.DataFrame(stratification_scores_v1(rows, syn_excess=syn_excess))
    return out.sort_values("rank_v1").reset_index(drop=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    ap.add_argument("--in", dest="inp", required=True, help="raw CSV (see module docstring for columns)")
    ap.add_argument("--out", required=True, help="scored CSV")
    ap.add_argument("--syn-excess", type=float, default=SYN_EXCESS_OE, help="oe_syn above which a gene is demoted")
    a = ap.parse_args(argv)
    try:
        out = score_table(pd.read_csv(a.inp), syn_excess=a.syn_excess)
    except ValueError as e:
        ap.error(str(e))
    out.to_csv(a.out, index=False)
    n_scored = int(out.score_v1.notna().sum())
    n_flag = int(out.qc_syn_excess.map(lambda x: x is not None and not pd.isna(x) and bool(x)).sum())
    print(f"scored {n_scored}/{len(out)} rows, {n_flag} flagged qc_syn_excess -> {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
