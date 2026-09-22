"""Parse biomarker selection out of free-text eligibility criteria.

Given a gene symbol, flag whether a trial mentions mutations in that gene, whether it
*requires* a mutation for entry, and whether it selects wild-type/negative patients.
Deliberately conservative regexes; validated on gefitinib/EGFR (see tests).
"""
from __future__ import annotations

import re


def _patterns(gene: str) -> dict[str, re.Pattern]:
    g = re.escape(gene.lower())
    mut = r"(mutat|del(etion)? ?19|exon ?(19|20|21)|l858r|t790m|activating|sensiti[sz]ing)"
    return {
        "mentioned": re.compile(rf"{g}.{{0,60}}{mut}|{mut}.{{0,60}}{g}"),
        "required": re.compile(
            rf"(activating|sensiti[sz]ing|positive|documented|confirmed|known|presence of|harbou?r(ing)?|with)\s+"
            rf"(an?\s+)?({g}[\s-]*(mutation|activating)|(exon ?19|l858r))"
            rf"|{g}\s*(mutation|-mutant|\+|positive|m\b)"
        ),
        "negated": re.compile(rf"{g}[\s-]*(wild[\s-]*type|negative|wt\b|unknown|status not required|regardless)"),
    }


def biomarker_selection(eligibility_text: str, gene: str) -> dict:
    """Return {mentioned, required, wt_or_negative, t790m} booleans for one eligibility text."""
    e = (eligibility_text or "").lower()
    p = _patterns(gene)
    mentioned = bool(p["mentioned"].search(e))
    negated = bool(p["negated"].search(e))
    required = bool(p["required"].search(e)) and not negated
    return {"mentioned": mentioned, "required": required, "wt_or_negative": negated, "t790m": "t790m" in e}
