"""Curated effect estimates + provenance checking against retrieved abstracts."""
from __future__ import annotations

import math

import pandas as pd


def load_effects(path: str) -> pd.DataFrame:
    df = pd.read_csv(path, dtype={"pmid": str, "p": str, "n": str})
    for c in ("hr", "ci_lo", "ci_hi"):
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df["significant"] = (df.ci_lo.notna()) & ((df.ci_hi < 1) | (df.ci_lo > 1))
    df["direction"] = df.hr.apply(lambda h: "favours_drug" if h < 1 else "favours_comparator")
    return df


def provenance_check(effects: pd.DataFrame, abstracts: dict[str, dict]) -> pd.DataFrame:
    """For every row, is the HR value literally present in the abstract of its PMID?

    Returns the effects frame with an ``hr_in_abstract`` column. A False is not
    necessarily an error (the number may only be in the full text) but must be reviewed.
    """
    def check(row):
        ab = (abstracts.get(str(row.pmid)) or {}).get("abstract") or ""
        return f"{row.hr:.2f}" in ab
    out = effects.copy()
    out["hr_in_abstract"] = out.apply(check, axis=1)
    return out


def mixture_hr(f: float, hr_pos: float, hr_neg: float) -> float:
    """Log-linear mixture of subgroup hazard ratios at responder fraction f.

    Approximation: the marginal HR of a proportional-hazards mixture is not constant over
    time; this is a first-order check, good enough to ask 'could the ITT trial have won?'.
    """
    return math.exp(f * math.log(hr_pos) + (1 - f) * math.log(hr_neg))


def fraction_for_target_hr(target: float, hr_pos: float, hr_neg: float) -> float | None:
    """Responder fraction at which the mixture HR equals ``target`` (None if unreachable)."""
    if not (hr_pos < target < hr_neg):
        return None
    return math.log(target / hr_neg) / math.log(hr_pos / hr_neg)
