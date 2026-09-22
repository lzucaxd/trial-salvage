"""Score all 209 failed-trial targets (182 first-drug + 27 second-drug) with the v1 germline score (offline).

PYTHONPATH=src python scripts/score_all_failed_trial_targets.py
-> data/candidates/failed_trial_target_scores_v1_all.csv

Raw columns are taken from failed_trial_target_scores_v1.csv (v0/v1 score columns dropped, recomputed here) and
second_drug_targets_raw_v0.csv, aligned on the score_targets input contract. ``source`` records which list a gene came
from; ``status`` is the second-drug fetch status (empty for first-drug targets). The low_exp_lof flag is applied by
score_targets.score_table before scoring.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from trial_salvage.module3.score_targets import ADDED, score_table

ROOT = Path(__file__).resolve().parents[1]
CAND = ROOT / "data" / "candidates"
RAW_COLS = ["symbol", "gene_id", "LOEUF", "oe_lof", "pLI", "mis_z", "obs_lof", "exp_lof", "obs_mis", "exp_mis",
            "obs_syn", "exp_syn", "n_variants", "n_common", "n_common_func", "n_common_lof", "cum_maf_func",
            "trials", "n_trials"]


def build_raw() -> pd.DataFrame:
    first = pd.read_csv(CAND / "failed_trial_target_scores_v1.csv")
    second = pd.read_csv(CAND / "second_drug_targets_raw_v0.csv")
    first = first[RAW_COLS].assign(source="first_drug", status=None)
    second = second[RAW_COLS + ["status"]].assign(source="second_drug")
    raw = pd.concat([first, second], ignore_index=True)
    if raw.symbol.duplicated().any():
        raise ValueError(f"duplicate symbols: {raw.symbol[raw.symbol.duplicated()].tolist()}")
    assert not set(ADDED) & set(raw.columns)
    return raw


def main() -> int:
    raw = build_raw()
    out = score_table(raw)
    dst = CAND / "failed_trial_target_scores_v1_all.csv"
    out.to_csv(dst, index=False)
    print(f"{len(out)} rows, {int(out.score_v1.notna().sum())} scored, "
          f"{int(out.low_exp_lof.map(lambda x: x is True).sum())} low_exp_lof -> {dst.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
