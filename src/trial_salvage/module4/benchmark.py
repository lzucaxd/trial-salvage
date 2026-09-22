"""Does module 4's ranking principle predict real rescue outcomes?

Module 4 tiers a strategy by the *provenance* of the evidence behind it — whether a
module 1 diagnosis rule fired on prespecified or mechanistic evidence — and
explicitly not by the size of the reported effect. That is a testable claim, and
``data/benchmark/rescue_benchmark_v0.csv`` is the test: 40 curated failed-trial /
retry pairs with adjudicated outcomes.

Two contrasts are computed, both offline and both from the committed CSV:

1. **provenance**  — prespecified/mechanistic vs post-hoc-subgroup motivation.
2. **effect class** — the kind of biomarker the retry selected on.

The EGFR-mutant NSCLC pairs form one biology and are flagged in the CSV's
``same_driver_cluster`` column. Module 3's genomic-regime verdict lost its outcome
signal when that cluster was removed, so the same leave-the-cluster-out test is
applied here rather than reported only on the full set. A contrast that survives it
is evidence about rescue attempts in general; one that does not is evidence about
EGFR.

Counts are small. The output reports them, not a model.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import pandas as pd
from scipy.stats import fisher_exact

__all__ = ["DECIDED", "evaluate", "load_benchmark", "provenance_contrast"]

DECIDED = ("success", "fail")
PROVENANCE_COL = "motivating_signal"
STRONG = "prespecified_or_mechanistic"
WEAK = "post_hoc_subgroup"


def load_benchmark(path: str | Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = {PROVENANCE_COL, "outcome", "same_driver_cluster"} - set(df.columns)
    if missing:
        raise ValueError(f"benchmark is missing required columns: {sorted(missing)}")
    return df


def _two_by_two(sub: pd.DataFrame) -> dict:
    """Success/fail counts for strong vs weak provenance, with Fisher's exact test."""
    counts = {}
    for label, key in ((STRONG, "strong"), (WEAK, "weak")):
        rows = sub[sub[PROVENANCE_COL] == label]
        counts[key] = {
            "success": int((rows.outcome == "success").sum()),
            "fail": int((rows.outcome == "fail").sum()),
        }
    table = [
        [counts["strong"]["success"], counts["strong"]["fail"]],
        [counts["weak"]["success"], counts["weak"]["fail"]],
    ]
    odds, p = fisher_exact(table)
    n_strong = sum(table[0])
    n_weak = sum(table[1])
    # A zero cell sends the odds ratio to 0 or inf; report it as null rather than
    # serialising a non-finite float into JSON.
    odds_out = round(float(odds), 3) if math.isfinite(odds) else None
    return {
        "n_pairs": len(sub),
        "prespecified_or_mechanistic": {
            **counts["strong"], "n": n_strong,
            "success_rate": round(table[0][0] / n_strong, 3) if n_strong else None,
        },
        "post_hoc_subgroup": {
            **counts["weak"], "n": n_weak,
            "success_rate": round(table[1][0] / n_weak, 3) if n_weak else None,
        },
        "odds_ratio": odds_out,
        "fisher_p": round(float(p), 4),
    }


def provenance_contrast(df: pd.DataFrame) -> dict:
    """The provenance contrast on all decided pairs and with the driver cluster removed."""
    decided = df[df.outcome.isin(DECIDED)]
    clustered = decided.same_driver_cluster.notna()
    clusters = sorted(decided.loc[clustered, "same_driver_cluster"].unique().tolist())

    out = {
        "all_decided": _two_by_two(decided),
        "cluster_removed": _two_by_two(decided[~clustered]),
        "clusters_removed": clusters,
        "excluded_outcomes": {
            str(k): int(v) for k, v in df.loc[~df.outcome.isin(DECIDED), "outcome"].value_counts().items()
        },
    }
    a, c = out["all_decided"], out["cluster_removed"]
    def _favours_strong(box: dict) -> bool:
        s_rate = box["prespecified_or_mechanistic"]["success_rate"]
        w_rate = box["post_hoc_subgroup"]["success_rate"]
        return s_rate is not None and w_rate is not None and s_rate > w_rate

    out["survives_cluster_removal"] = bool(
        c["fisher_p"] < 0.05 and _favours_strong(c) and _favours_strong(a)
    )
    out["interpretation"] = (
        "The provenance contrast holds with the one large driver cluster removed, so it is evidence "
        "about rescue attempts generally rather than about EGFR."
        if out["survives_cluster_removal"] else
        "The provenance contrast does not survive removing the driver cluster, so on this benchmark it "
        "is evidence about that one biology and must not be presented as a general rule."
    )
    return out


def effect_class_breakdown(df: pd.DataFrame, column: str = "biomarker_group") -> list[dict]:
    """Outcome counts per biomarker class, to show which kinds of marker delivered."""
    if column not in df.columns:
        return []
    decided = df[df.outcome.isin(DECIDED)]
    rows = []
    for val, grp in decided.groupby(column, dropna=False):
        rows.append({
            "class": "unspecified" if pd.isna(val) else str(val),
            "n": len(grp),
            "success": int((grp.outcome == "success").sum()),
            "fail": int((grp.outcome == "fail").sum()),
        })
    return sorted(rows, key=lambda r: (-r["success"], r["class"]))


def evaluate(path: str | Path) -> dict:
    df = load_benchmark(path)
    return {
        "benchmark": str(path),
        "n_rows": len(df),
        "claim_under_test": (
            "Module 4 tiers strategies by evidence provenance rather than by reported effect size. "
            "If that principle carries information, retries motivated by prespecified or mechanistic "
            "evidence should succeed more often than retries motivated by a post-hoc subgroup."
        ),
        "provenance_contrast": provenance_contrast(df),
        "by_biomarker_group": effect_class_breakdown(df),
        "caveats": [
            "Counts are small; the contrast is descriptive and the confidence intervals on these rates are wide.",
            (
                "Outcome adjudication and provenance labelling are curated by hand in the benchmark CSV, "
                "and the labels were assigned with the outcomes visible in the same file."
            ),
            "A pair is counted only when its outcome is decided; contested and pending pairs are listed and excluded.",
        ],
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", default="data/benchmark/rescue_benchmark_v0.csv")
    ap.add_argument("-o", "--out", default=None)
    a = ap.parse_args(argv)
    res = evaluate(a.benchmark)
    print(json.dumps(res["provenance_contrast"], indent=1))
    if a.out:
        Path(a.out).write_text(json.dumps(res, indent=1))
        print(f"\nwrote {a.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
