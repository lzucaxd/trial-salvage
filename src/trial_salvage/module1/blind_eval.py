"""Module 1 blind evaluation against the rescue benchmark.

PRE-REGISTERED RULE — committed before any effect estimate was extracted or any outcome joined.

Inputs per benchmark pair: effect estimates extracted ONLY from publications about the FAILED trial that
appeared before the RETRY trial's registry start date (pre-retry information). Each row carries
``analysis_type`` taken from the abstract's own wording, ``favours_drug`` and ``significant`` computed from
the estimate's direction and CI/p, and ``in_abstract`` (the number appears literally in the cited abstract).

Rules (generalised from failure_analysis.py to any effect type: HR/RR/OR < 1, MD/RD favouring drug):
  primary_endpoint_missed          primary/co-primary estimate not significant in favour of drug, or the trial
                                   was stopped for futility/efficacy with no significant primary.
  prespecified_subgroup_benefit    a subgroup labelled prespecified / preplanned / stratification factor /
                                   co-primary shows significant benefit.
  biomarker_heterogeneity          biomarker-defined subgroups on opposite sides of the null, or a reported
                                   significant treatment-by-biomarker interaction — from a PRESPECIFIED or
                                   PREPLANNED biomarker analysis.
  post_hoc_signal_only             the only favourable subgroup/biomarker estimates are labelled post hoc /
                                   exploratory / retrospective / unplanned.

Verdict (first match):
  retry_supported   primary_endpoint_missed AND (prespecified_subgroup_benefit OR biomarker_heterogeneity)
  retry_weak        primary_endpoint_missed AND post_hoc_signal_only
  not_supported     primary_endpoint_missed AND no favourable subgroup/biomarker estimate at all
  not_evaluable     no primary estimate could be extracted from pre-retry abstracts

Pre-stated expectation: success rate retry_supported > retry_weak >= not_supported. Falsified as a decision
aid if the ordering does not hold, or if it holds only through the EGFR-mutant NSCLC cluster (4 pairs).
Blinding caveat: benchmark outcomes and headline rates were already known to the author; this guards only
against tuning the rule or the abstract set after the join.
"""
from __future__ import annotations

import pandas as pd

PRESPEC = ("prespecified", "pre-specified", "preplanned", "pre-planned", "co-primary", "stratif", "planned")
POSTHOC = ("post hoc", "post-hoc", "exploratory", "retrospective", "unplanned", "hypothesis-generating")


def _kind(analysis_type: str) -> str:
    a = (analysis_type or "").lower()
    if "primary" in a and "co-primary" not in a:
        return "primary"
    if any(k in a for k in POSTHOC):
        return "post_hoc"
    if any(k in a for k in PRESPEC):
        return "prespecified"
    return "unspecified"


def favours_drug(effect_type: str, estimate: float, direction_note: str | None = None) -> bool | None:
    """HR/RR/OR: < 1 favours drug unless the note says higher is better (e.g. response OR)."""
    if estimate is None or pd.isna(estimate):
        return None
    et = (effect_type or "").upper()
    higher_better = bool(direction_note) and "higher" in direction_note.lower()
    if et in ("HR", "RR", "OR", "IRR"):
        return estimate > 1 if higher_better else estimate < 1
    if et in ("MD", "RD", "DIFF", "SMD"):
        return estimate < 0 if (direction_note and "lower" in direction_note.lower()) else estimate > 0
    return None


def evaluate_pair(effects: pd.DataFrame) -> dict:
    e = effects.copy()
    e["kind"] = e.analysis_type.map(_kind)
    e["is_bio"] = e.analysis_type.str.contains("biomarker", case=False) | e.population.str.contains(
        "mutation|positive|negative|high|low|carrier|expression|genotype", case=False, regex=True)
    prim = e[e.kind == "primary"]
    if len(prim) == 0:
        return {"verdict": "not_evaluable", "primary_missed": None, "prespec_benefit": False,
                "bio_heterogeneity": False, "post_hoc_only": False, "n_rows": len(e)}
    primary_missed = not bool((prim.significant & prim.favours_drug.fillna(False)).any())
    sub = e[e.kind != "primary"]
    fav_sig = sub[sub.significant.fillna(False) & sub.favours_drug.fillna(False)]
    prespec_benefit = bool((fav_sig.kind == "prespecified").any())
    bio_pre = sub[sub.is_bio & (sub.kind == "prespecified")]
    bio_het = bool(len(bio_pre) >= 2 and bio_pre.favours_drug.fillna(False).any() and (~bio_pre.favours_drug.fillna(True)).any()) \
        or bool(sub[sub.is_bio & (sub.kind == "prespecified")].note.fillna("").str.contains("interaction", case=False).any()
                and sub[sub.is_bio & (sub.kind == "prespecified")].significant.fillna(False).any())
    post_hoc_only = bool(len(fav_sig)) and bool((fav_sig.kind.isin(["post_hoc", "unspecified"])).all()) and not prespec_benefit
    if primary_missed and (prespec_benefit or bio_het):
        v = "retry_supported"
    elif primary_missed and post_hoc_only:
        v = "retry_weak"
    elif primary_missed:
        v = "not_supported"
    else:
        v = "primary_not_missed"
    return {"verdict": v, "primary_missed": primary_missed, "prespec_benefit": prespec_benefit,
            "bio_heterogeneity": bio_het, "post_hoc_only": post_hoc_only, "n_rows": len(e),
            "n_favourable_sig": int(len(fav_sig))}
