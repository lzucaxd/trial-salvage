"""Did the subgroup effect a retry was designed on actually replicate in that retry?

This is the check that separates a pipeline which explains a known winner from one
that would have called the outcome. For a retry enrolling only biomarker-positive
patients, the sponsor's design rested on a prior estimate ``hr_prior``. If that
estimate were the truth, the retry at its actual size would produce observed
hazard ratios in a predictable range. We simulate that range and ask where the
retry's actual result fell.

Two honest constraints are enforced:

* **Circularity is refused, not hidden.** When the prior estimate was measured in
  the retry itself — as with a prespecified biomarker analysis inside the rescue
  trial — the comparison is not an independent test, and the verdict says so
  instead of reporting a spurious agreement.
* **No outcome is predicted.** The output says whether a prior estimate survived
  its own prospective test. It does not assign any probability to a future rescue.
"""

from __future__ import annotations

import math

import numpy as np

from .simulate import Assumptions, _split
from .survival import logrank, simulate_arm

__all__ = ["VERDICTS", "retrospective_check"]

VERDICTS = ("replicated", "did_not_replicate", "not_an_independent_test", "not_assessable")


def _simulate_hr_distribution(
    n_total: int,
    hr_true: float,
    a: Assumptions,
    rng: np.random.Generator,
    n_simulations: int,
) -> np.ndarray:
    """Sampling distribution of the estimated hazard ratio if ``hr_true`` holds."""
    n_t, n_c = _split(n_total, a.allocation_ratio)
    lam_c = a.control_hazard
    out = np.empty(n_simulations, dtype=float)
    for i in range(n_simulations):
        t_t, e_t = simulate_arm(n_t, lam_c * hr_true, a.follow_up_months, rng, a.accrual_months)
        t_c, e_c = simulate_arm(n_c, lam_c, a.follow_up_months, rng, a.accrual_months)
        out[i] = logrank(t_t, e_t, t_c, e_c).hazard_ratio
    return out[np.isfinite(out)]


def retrospective_check(
    hr_prior: float | None,
    observed_retry_hr: float | None,
    n_retry: int | None,
    a: Assumptions,
    independent_test: bool,
    prior_source: str = "",
    observed_source: str = "",
    n_simulations: int | None = None,
) -> dict:
    """Locate the retry's observed hazard ratio in the distribution the prior implies.

    ``independent_test`` must be False when ``hr_prior`` was estimated in the same
    trial that produced ``observed_retry_hr``.
    """
    base = {
        "hr_prior": hr_prior,
        "prior_source": prior_source,
        "observed_retry_hr": observed_retry_hr,
        "observed_source": observed_source,
        "n_retry": n_retry,
        "independent_test": independent_test,
    }

    if hr_prior is None or observed_retry_hr is None or not n_retry:
        return {**base, "verdict": "not_assessable",
                "note": "Needs a prior subgroup estimate, the retry's observed ratio and its size."}

    if not independent_test:
        return {
            **base,
            "verdict": "not_an_independent_test",
            "note": ("The prior estimate was measured in the same trial that produced the observed result, "
                     "so agreement between them carries no predictive information. A prospective test "
                     "requires the estimate to predate the trial that checks it."),
        }

    n_sim = n_simulations or a.n_simulations
    rng = np.random.default_rng(a.seed + 17)
    dist = _simulate_hr_distribution(n_retry, hr_prior, a, rng, n_sim)
    if dist.size == 0:
        return {**base, "verdict": "not_assessable", "note": "No events simulated; check the assumptions."}

    pct = float((dist <= observed_retry_hr).mean())
    lo, med, hi = (float(np.percentile(dist, q)) for q in (2.5, 50, 97.5))
    # A prior survives its prospective test if the observed value is inside the
    # central 95% of what the prior implies at that sample size.
    replicated = lo <= observed_retry_hr <= hi
    out = {
        **base,
        "implied_distribution": {
            "hr_2.5_pct": round(lo, 3),
            "hr_median": round(med, 3),
            "hr_97.5_pct": round(hi, 3),
            "n_simulations": int(dist.size),
        },
        "observed_percentile_of_implied": round(pct, 4),
        "verdict": "replicated" if replicated else "did_not_replicate",
    }
    if replicated:
        out["note"] = (
            f"The retry's observed ratio {observed_retry_hr} lies inside the central 95% interval "
            f"[{lo:.2f}, {hi:.2f}] that a true ratio of {hr_prior} implies at n={n_retry}, so the prior "
            "estimate survived its prospective test."
        )
    else:
        side = "above" if observed_retry_hr > hi else "below"
        out["note"] = (
            f"The retry's observed ratio {observed_retry_hr} lies {side} the central 95% interval "
            f"[{lo:.2f}, {hi:.2f}] implied by a true ratio of {hr_prior} at n={n_retry}. The prior "
            "subgroup estimate did not survive its prospective test, so any power computed from it "
            "was answering the wrong question."
        )
    return out


def crosses_no_effect(hr_prior: float, observed_retry_hr: float) -> bool:
    """True when the prior and the observed result fall on opposite sides of 1."""
    return (hr_prior - 1.0) * (observed_retry_hr - 1.0) < 0 and not math.isclose(observed_retry_hr, 1.0)
