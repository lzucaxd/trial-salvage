"""Paired comparison of rescue cases with known outcomes.

The point of this figure is that the *size* of a subgroup effect does not tell you
whether a rescue will work. Gefitinib and onartuzumab both failed an unselected
trial, both showed a biomarker-positive subgroup with a hazard ratio near 0.4-0.5
and a biomarker-negative subgroup above 1, and both were retried in a
biomarker-enriched population. One was approved; the other was stopped for
futility with the drug arm numerically worse.

What separated them is the provenance of the subgroup estimate, which is what
module 4 tiers on and what ``benchmark.py`` tests across all 40 curated pairs.

Usage::

    python -m trial_salvage.module4.compare \\
        --case data/cases/gefitinib_module4.json \\
        --case data/cases/onartuzumab_module4.json \\
        --benchmark data/benchmark/rescue_benchmark_v0.csv \\
        --outdir outputs/module4_comparison
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from .benchmark import evaluate as evaluate_benchmark

C_HELD, C_INVERTED, C_PRIOR, C_META = "#2166ac", "#b2182b", "#4d4d4d", "#777777"

_RC = {
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 6, "axes.spines.top": False, "axes.spines.right": False,
}

__all__ = ["comparison_table", "main", "paired_figure"]


def _class_short(cls: str) -> str:
    return {
        "fail_then_retry_then_succeed": "retried, succeeded",
        "fail_then_retry_then_fail_again": "retried, failed again",
        "fail_then_not_retried": "not retried",
    }.get(cls, cls or "unknown")


def comparison_table(cases: list[dict]) -> list[dict]:
    """One row per case: the design-time evidence, its provenance, and the real outcome."""
    rows = []
    for c in cases:
        eq = c.get("evidence_quality") or {}
        oc = c.get("outcome") or {}
        rr = c.get("retry_result") or {}
        pre = c.get("pre_retry_evidence") or []
        best = min((p for p in pre if p.get("hr") is not None), key=lambda p: p["hr"], default={})
        rows.append({
            "asset": (c.get("asset") or {}).get("name", c.get("case_id", "?")),
            "target": (c.get("target") or {}).get("symbol"),
            "outcome_class": _class_short(oc.get("class", "")),
            "lever": "biomarker enrichment",
            "best_pre_retry_hr": best.get("hr"),
            "pre_retry_ci": (None if best.get("ci_lo") is None
                             else f"{best['ci_lo']}-{best['ci_hi']}"),
            "pre_retry_n": best.get("n"),
            "retry_observed_hr": rr.get("hr", oc.get("observed_retry_hr")),
            "retry_ci": (None if rr.get("ci_lo") is None else f"{rr['ci_lo']}-{rr['ci_hi']}"),
            "retry_n": rr.get("n"),
            "motivating_signal": eq.get("motivating_signal"),
            "biomarker_class": eq.get("biomarker_class"),
            "replicated_independently": eq.get("replicated_in_an_independent_trial"),
            "cutoff_chosen_on_outcome": eq.get("assay_threshold_selected_on_outcome"),
            "ci_reported_for_best_hr": eq.get("ci_reported_for_hr_pos"),
            "retry_registry_results_posted": eq.get("registry_results_posted_for_retry"),
        })
    return rows


def paired_figure(cases: list[dict], bench: dict, out_png: str) -> None:
    plt.rcParams.update(_RC)
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11.5, 4.6), gridspec_kw={"width_ratios": [1.5, 1]})

    # -- panel a: design-time evidence vs what the retry returned --------
    ypos, ylabels, y = [], [], 0.0
    for c in cases:
        name = (c.get("asset") or {}).get("name", "?")
        succeeded = (c.get("outcome") or {}).get("class") == "fail_then_retry_then_succeed"
        retry_col = C_HELD if succeeded else C_INVERTED
        rows = list(c.get("pre_retry_evidence") or [])
        rr = c.get("retry_result")

        for p in rows:
            _draw(axA, y, p, C_PRIOR, marker="o", filled=False)
            ylabels.append(f"{p['label']}  (n={p.get('n','?')})")
            ypos.append(y); y -= 1.0
        if rr:
            _draw(axA, y, rr, retry_col, marker="s", filled=True)
            ylabels.append(f"\u25b6 {rr['label']}  (n={rr.get('n','?')})")
            ypos.append(y); y -= 1.0
        axA.text(0.055, y + 0.55, f"{name} — {_class_short((c.get('outcome') or {}).get('class',''))}",
                 fontsize=7, fontweight="bold", color=retry_col, va="center")
        y -= 0.9

    axA.axvline(1.0, color="#999999", lw=0.8)
    axA.set_xscale("log")
    axA.set_xlim(0.05, 3.2)
    axA.set_xticks([0.1, 0.25, 0.5, 1, 2])
    axA.set_xticklabels(["0.1", "0.25", "0.5", "1", "2"])
    axA.set_yticks(ypos)
    axA.set_yticklabels(ylabels)
    axA.set_ylim(y + 0.6, 1.4)
    axA.set_xlabel("Hazard ratio vs comparator (log scale)")
    axA.text(0.06, 1.05, "favours drug \u2190", fontsize=6, color=C_META)
    axA.text(3.1, 1.05, "\u2192 favours comparator", fontsize=6, color=C_META, ha="right")
    axA.set_title("Both drugs entered their retry with a subgroup hazard ratio near 0.4;\n"
                  "only one of them held when the retry measured it prospectively", loc="left")
    axA.plot([], [], "o", mfc="white", mec=C_PRIOR, color=C_PRIOR, ms=5, label="evidence available before the retry")
    axA.plot([], [], "s", color="#666666", ms=5, label="what the retry actually returned")
    axA.legend(frameon=False, loc="lower right", handlelength=1.4)

    # -- panel b: does provenance predict outcome across all 40 pairs? ---
    pc = bench["provenance_contrast"]
    groups = [("all decided\npairs", pc["all_decided"]), ("EGFR cluster\nremoved", pc["cluster_removed"])]
    x = np.arange(len(groups))
    width = 0.34
    for i, (key, col, lab) in enumerate([
        ("prespecified_or_mechanistic", C_HELD, "prespecified / mechanistic"),
        ("post_hoc_subgroup", C_INVERTED, "post-hoc subgroup"),
    ]):
        vals = [g[1][key]["success_rate"] or 0.0 for g in groups]
        ns = [g[1][key]["n"] for g in groups]
        succ = [g[1][key]["success"] for g in groups]
        bars = axB.bar(x + (i - 0.5) * width, vals, width, color=col, label=lab)
        for b, v, n, sc in zip(bars, vals, ns, succ):
            axB.text(b.get_x() + b.get_width() / 2, v + 0.018, f"{v:.0%}\n{sc}/{n}",
                     ha="center", va="bottom", fontsize=6, color=col)
    axB.set_xticks(x)
    axB.set_xticklabels([f"{g[0]}\nn={g[1]['n_pairs']}, Fisher p={g[1]['fisher_p']:.3f}" for g in groups])
    axB.set_ylim(0, 0.85)
    axB.set_ylabel("Retries that succeeded")
    axB.set_yticks([0, 0.2, 0.4, 0.6, 0.8])
    axB.set_yticklabels(["0%", "20%", "40%", "60%", "80%"])
    axB.set_title("Across 40 curated failed-trial/retry pairs, evidence provenance\n"
                  "predicts the outcome — and survives removing the EGFR cluster", loc="left")
    axB.legend(frameon=False, loc="upper right")

    for ax, letter in ((axA, "a"), (axB, "b")):
        ax.text(-0.02, 1.10, letter, transform=ax.transAxes, fontweight="bold", fontsize=10, ha="right")
    fig.tight_layout(w_pad=2.2)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)


def _draw(ax, y, row, colour, marker="o", filled=True):
    hr, lo, hi = row.get("hr"), row.get("ci_lo"), row.get("ci_hi")
    if hr is None:
        return
    if lo is not None and hi is not None:
        ax.plot([lo, hi], [y, y], color=colour, lw=1.3)
        label = f"{hr:.2f} ({lo:.2f}\u2013{hi:.2f})"
    else:
        label = f"{hr:.2f} (CI not reported)"
    ax.plot([hr], [y], marker=marker, color=colour, ms=5.5,
            mfc=colour if filled else "white", mew=1.3)
    ax.text(3.15, y, label, fontsize=6, va="center", ha="right", color=colour)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", action="append", required=True,
                    help="Case JSON; repeat for each asset. Order is preserved in the figure.")
    ap.add_argument("--benchmark", default="data/benchmark/rescue_benchmark_v0.csv")
    ap.add_argument("--outdir", default="outputs/module4_comparison")
    a = ap.parse_args(argv)

    cases = [json.loads(Path(p).read_text()) for p in a.case]
    bench = evaluate_benchmark(a.benchmark)
    out = Path(a.outdir)
    out.mkdir(parents=True, exist_ok=True)

    fig_path = out / "fig_case_comparison.png"
    paired_figure(cases, bench, str(fig_path))
    table = comparison_table(cases)
    payload = {"cases": table, "ranking_principle_validation": bench, "figure": fig_path.name}
    (out / "case_comparison.json").write_text(json.dumps(payload, indent=1))

    import csv
    with (out / "case_comparison.csv").open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader()
        w.writerows(table)

    print(json.dumps({"cases": [r["asset"] for r in table],
                      "outcomes": [r["outcome_class"] for r in table],
                      "provenance_survives_cluster_removal": bench["provenance_contrast"]["survives_cluster_removal"],
                      "outdir": str(out)}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
