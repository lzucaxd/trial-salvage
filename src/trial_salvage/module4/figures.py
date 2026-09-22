"""Figures for module 4: power vs responder fraction + screening burden.

Styling follows module 1 (same rcParams ladder, palette and panel letters) so the
two modules' figures sit together in one report.
"""

from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

C_UNSEL, C_ENRICH, C_PROXY, C_META = "#4d4d4d", "#b2182b", "#2166ac", "#777777"

_RC = {
    "font.size": 8, "axes.titlesize": 8, "axes.labelsize": 8, "xtick.labelsize": 7,
    "ytick.labelsize": 7, "legend.fontsize": 6, "axes.spines.top": False, "axes.spines.right": False,
}


def power_and_screening(
    grid: list,
    assumptions,
    hr_pos: float,
    hr_neg: float,
    enriched_requirement: dict,
    out_png: str,
    asset_name: str = "the asset",
    gene: str = "the biomarker",
    target_power: float = 0.8,
    crossing_fraction: float | None = None,
    biomarker_phrase: str | None = None,
    positive_label: str | None = None,
    surrogate_label: str | None = None,
) -> None:
    """Panel a: power vs responder fraction by design. Panel b: screening burden."""
    plt.rcParams.update(_RC)
    # The marker is a genotype for some assets and a stain intensity for others, so the
    # wording is supplied by the caller rather than assumed to be a "variant".
    phrase = biomarker_phrase or f"a positive {gene} biomarker result"
    pos_lab = positive_label or f"{gene}-positive"
    rows = [r if isinstance(r, dict) else r.to_dict() for r in grid]
    sizes = sorted({r["total_randomized"] for r in rows})
    fig, (axA, axB) = plt.subplots(1, 2, figsize=(11, 4.2), gridspec_kw={"width_ratios": [1.15, 1]})

    # -- panel a ---------------------------------------------------------
    greys = ["#8c8c8c", "#4d4d4d", "#1a1a1a"]
    for i, n in enumerate(sizes):
        sel = sorted([r for r in rows if r["design"] == "unselected" and r["total_randomized"] == n],
                     key=lambda r: r["responder_fraction"])
        if not sel:
            continue
        x = [r["responder_fraction"] for r in sel]
        y = [r["simulated_power"] for r in sel]
        axA.plot(x, y, marker="o", ms=3.5, lw=1.3, color=greys[i % len(greys)],
                 label=f"unselected, n={n:,}")

    enr = sorted([r for r in rows if r["design"] == "enriched"], key=lambda r: r["responder_fraction"])
    if enr:
        n_enr = min(r["total_randomized"] for r in enr)
        sel = [r for r in enr if r["total_randomized"] == n_enr]
        x = [r["responder_fraction"] for r in sel]
        y = [r["simulated_power"] for r in sel]
        axA.plot(x, y, marker="s", ms=3.5, lw=1.6, color=C_ENRICH,
                 label=f"{pos_lab}-enriched, n={n_enr:,}")

    prox = sorted([r for r in rows if r["design"] == "clinical_surrogate"],
                  key=lambda r: r["total_randomized"])
    for r in prox:
        axA.plot(r["responder_fraction"], r["simulated_power"], marker="D", ms=4.5,
                 color=C_PROXY, mfc="white", mew=1.2)
    if prox:
        r = prox[-1]
        axA.annotate(surrogate_label or "clinical proxy", xy=(r["responder_fraction"], r["simulated_power"]),
                     xytext=(0.30, 0.66), fontsize=6, color=C_PROXY, ha="center",
                     arrowprops={"arrowstyle": "-", "lw": 0.6, "color": C_PROXY})

    axA.axhline(target_power, color=C_META, lw=0.7, ls=":")
    axA.text(0.015, target_power + 0.02, f"{target_power:.0%} power", fontsize=6, color=C_META)
    if crossing_fraction is not None:
        axA.axvline(crossing_fraction, color=C_META, lw=0.7, ls="--")
        # Below the rising curves, clear of the x ticks it would otherwise collide with.
        axA.text(crossing_fraction + 0.015, 0.11, f"unselected needs\n{crossing_fraction:.0%} positive",
                 fontsize=6, color=C_META, ha="left", va="center")
    axA.set_xlabel(f"Fraction of enrolled population with {phrase}")
    axA.set_ylabel("Simulated power (one-sided log-rank), higher = better")
    axA.set_ylim(-0.03, 1.10)
    axA.set_xlim(0, 1.02)
    axA.set_xticks([0.0, 0.2, 0.4, 0.6, 0.8, 1.0])
    axA.legend(frameon=False, loc="center right", bbox_to_anchor=(1.0, 0.44), handlelength=1.6)
    axA.set_title(
        f"An unselected re-run of {asset_name} stays underpowered until most\n"
        f"of the population is {pos_lab}; enrichment wins at a fraction of the size",
        loc="left")

    # -- panel b ---------------------------------------------------------
    n_req = enriched_requirement.get("n_randomized")
    fr = [r["responder_fraction"] for r in enr] if enr else []
    if n_req and fr:
        f_dense = np.linspace(max(min(fr), 0.05), max(fr), 100)
        screened = n_req / f_dense
        axB.plot(f_dense, screened, lw=1.6, color=C_ENRICH)
        axB.axhline(n_req, color=C_META, lw=0.7, ls=":")
        axB.text(0.015, n_req * 1.06, f"randomised, n={n_req:,}", fontsize=6, color=C_META, va="bottom")
        for f_mark in (0.1, 0.25, 0.5):
            if f_mark >= f_dense[0]:
                s = n_req / f_mark
                axB.plot([f_mark], [s], marker="o", ms=4, color=C_ENRICH)
                axB.annotate(f"{s:,.0f} screened\nat {f_mark:.0%} prevalence",
                             xy=(f_mark, s), xytext=(f_mark + 0.06, s),
                             fontsize=6, color=C_ENRICH, va="center",
                             arrowprops={"arrowstyle": "-", "lw": 0.6, "color": C_ENRICH})
        axB.set_ylim(0, float(n_req / f_dense[0]) * 1.12)
    axB.set_xlabel(f"Prevalence of {phrase} in the screened population")
    axB.set_ylabel("Participants screened to randomise the trial")
    axB.set_xlim(0, max(fr) + 0.02 if fr else 1.0)
    axB.set_title(
        "Enrichment moves the cost from sample size to screening:\n"
        "the rarer the marker, the more patients tested per one randomised",
        loc="left")

    for ax, letter in ((axA, "a"), (axB, "b")):
        ax.text(-0.02, 1.10, letter, transform=ax.transAxes, fontweight="bold", fontsize=10, ha="right")
    fig.tight_layout(w_pad=2.5)
    fig.savefig(out_png, dpi=300, bbox_inches="tight")
    plt.close(fig)
