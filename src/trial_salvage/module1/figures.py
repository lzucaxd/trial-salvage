"""Figures for module 1: forest plot of effect estimates + biomarker-selection adoption timeline."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

C_FAILED, C_RESCUE, C_BIO = "#4d4d4d", "#b2182b", "#2166ac"


def forest_and_timeline(effects: pd.DataFrame, family: pd.DataFrame, cfg: dict, out_png: str) -> None:
    plt.rcParams.update({"font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7,
                         "ytick.labelsize": 6, "legend.fontsize": 6, "axes.spines.top": False, "axes.spines.right": False})
    failed, rescue = cfg["trials"]["failed"]["label"], cfg["trials"]["rescue"]["label"]
    gene = cfg["biomarker"]["gene"]
    plot = effects[effects.trial.isin([failed, rescue]) & ~effects.analysis_type.str.contains("post hoc")].reset_index(drop=True)

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.4), gridspec_kw={"width_ratios": [1.35, 1]})
    ypos = np.arange(len(plot))[::-1]
    for yi, r in zip(ypos, plot.itertuples()):
        col = C_FAILED if r.trial == failed else C_RESCUE
        if r.trial == failed and "biomarker" in r.analysis_type:
            col = C_BIO
        has_ci = not (np.isnan(r.ci_lo) or np.isnan(r.ci_hi))
        mk = "s" if (r.trial == rescue and r.endpoint == "OS") else "o"
        if has_ci:
            axA.plot([r.ci_lo, r.ci_hi], [yi, yi], color=col, lw=1.2)
            axA.plot(r.hr, yi, marker=mk, color=col, ms=5)
            label = f"{r.hr:.2f} ({r.ci_lo:.2f}-{r.ci_hi:.2f})"
        else:
            axA.plot(r.hr, yi, marker=mk, color=col, ms=4, mfc="white")
            label = f"{r.hr:.2f} (CI n/a)"
        axA.text(4.6, yi, label, va="center", fontsize=6)
    axA.axvline(1, color="#999999", lw=0.8)
    axA.set_xscale("log"); axA.set_xlim(0.3, 12)
    axA.set_xticks([0.4, 0.6, 1, 2, 4]); axA.set_xticklabels(["0.4", "0.6", "1", "2", "4"])
    axA.set_yticks(ypos)
    axA.set_yticklabels([f"{r.trial} \u00b7 {r.population}" + (f"  [{r.endpoint}]" if r.trial == rescue else "") for r in plot.itertuples()])
    axA.set_xlabel(f"Hazard ratio, {cfg['asset']['name']} vs comparator (log scale)")
    axA.set_title(f"{failed} missed on {cfg['trials']['failed']['primary_endpoint']}; its subgroups and {rescue}'s "
                  f"{gene}-mutant subgroup\nshow large, opposite-signed effects", loc="left")
    axA.text(0.31, ypos[0] + 0.9, "favours drug \u2190", fontsize=6, color="#555555")
    axA.text(11.5, ypos[0] + 0.9, "\u2192 favours comparator", fontsize=6, ha="right", color="#555555")
    axA.set_ylim(-0.8, len(plot) + 1.0)
    n_failed = int((plot.trial == failed).sum())
    if 0 < n_failed < len(plot):
        axA.axhline(ypos[n_failed - 1] - 0.5, color="#cccccc", lw=0.6, ls="--")

    fam = family.dropna(subset=["start_year"])
    fam = fam[(fam.start_year >= 2000) & (fam.start_year <= 2023) & fam.in_indication]
    by = fam.groupby("start_year").agg(total=("nct", "size"), req=("biomarker_required", "sum")).reset_index()
    axB.bar(by.start_year, by.total, color="#d9d9d9", width=0.8, label=f"All {cfg['asset']['name']} trials in indication")
    axB.bar(by.start_year, by.req, color=C_RESCUE, width=0.8, label=f"{gene} mutation required in eligibility")
    ymax = max(by.total.max() * 1.25, 5)
    for lab, date in [(f"{failed}\nstarts", cfg["_dates"]["failed_start"]), (f"{rescue}\nstarts", cfg["_dates"]["rescue_start"]),
                      (f"{rescue}\npublished", cfg["_dates"]["rescue_published"])]:
        if date:
            axB.axvline(date, color="#777777", lw=0.6, ls=":")
            axB.text(date, ymax * 0.97, lab, fontsize=6, ha="center", va="top", color="#555555")
    axB.set_xlabel("Trial start year"); axB.set_ylabel(f"Interventional {cfg['asset']['name']} trials")
    axB.set_title(f"After {rescue}, {cfg['asset']['name']} trials became\n{gene}-mutation-selected by default", loc="left")
    axB.legend(frameon=False, loc="upper right", bbox_to_anchor=(1, 0.82))
    axB.set_ylim(0, ymax); axB.margins(x=0.02)
    for ax, letter in ((axA, "a"), (axB, "b")):
        ax.text(-0.02, 1.08, letter, transform=ax.transAxes, fontweight="bold", fontsize=10, ha="right")
    fig.tight_layout(w_pad=2.5)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
