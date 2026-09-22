"""Rank statistics with no SciPy dependency.

The repo's runtime dependencies are requests/pandas/matplotlib/pyyaml/jsonschema; adding SciPy
just for two rank tests is not worth it, so AUROC and its normal-approximation p-value are
computed directly from midrank sums.
"""
from __future__ import annotations

import math

import pandas as pd

MIN_GROUP = 5


def _midranks(values: pd.Series) -> pd.Series:
    return values.rank(method="average")


def auroc(score: pd.Series, positive: pd.Series, negative: pd.Series) -> dict:
    """P(random positive scores LOWER than random negative), ties counted as half.

    Orientation: ESM masked-marginal scores are negative for implausible substitutions, so a
    predictor that ranks pathogenic variants as less plausible gives AUROC > 0.5.
    """
    a = score[positive].dropna()
    b = score[negative].dropna()
    n1, n2 = len(a), len(b)
    if n1 < MIN_GROUP or n2 < MIN_GROUP:
        return {"auroc": None, "p_value": None, "n_positive": n1, "n_negative": n2,
                    "note": f"fewer than {MIN_GROUP} variants in one class; not computable"}
    pooled = pd.concat([a, b])
    ranks = _midranks(pooled)
    u_a = float(ranks.iloc[:n1].sum()) - n1 * (n1 + 1) / 2.0
    area = 1.0 - u_a / (n1 * n2)
    mu = n1 * n2 / 2.0
    sigma = math.sqrt(n1 * n2 * (n1 + n2 + 1) / 12.0)
    z = (u_a - mu) / sigma if sigma > 0 else 0.0
    p = math.erfc(abs(z) / math.sqrt(2.0))
    return {"auroc": area, "p_value": p, "n_positive": n1, "n_negative": n2, "note": None}


def spearman(x: pd.Series, y: pd.Series) -> float:
    """Spearman rank correlation via Pearson on midranks."""
    xr, yr = _midranks(pd.Series(list(x))), _midranks(pd.Series(list(y)))
    return float(xr.corr(yr))
