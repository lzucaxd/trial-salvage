"""Trial designs simulated under module 1's hazard ratios.

Three designs are compared for a re-run of a failed trial:

``unselected``
    Enrol from the whole population. A fraction ``f`` carry the sensitising
    biomarker and experience ``hr_pos``; the rest experience ``hr_neg``. Nobody
    is screened out, so screening burden equals the randomised count.
``enriched``
    Enrol only biomarker-positive participants, so every participant
    experiences ``hr_pos``. Screening burden is ``n / f`` because ``1 - f`` of
    those tested are turned away.
``clinical_surrogate``
    Enrol on a clinical proxy (histology, smoking history) that is enriched for
    the biomarker but imperfect: the enrolled population is a mixture with
    positive fraction ``f_proxy > f``. This is what IPASS actually did, before a
    validated assay existed.

What is an assumption and what is data
--------------------------------------
``hr_pos``, ``hr_neg`` and the trial sizes come from module 1 and are observed.
Everything in :class:`Assumptions` is supplied by a human — in particular the
control-arm event rate, taken from the posted IPASS control median PFS of 5.8
months. Exponential survival, no dropout and a perfect assay are simplifying
assumptions, listed in the output so no reader mistakes them for findings.

No quantity here is a "probability of rescue". Power is the probability that a
trial of a stated size detects a stated effect, conditional on the assumptions.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .survival import logrank, simulate_arm

__all__ = [
    "Assumptions",
    "DesignResult",
    "calibrate",
    "min_fraction_for_power",
    "power_enriched",
    "power_grid",
    "power_single_hr",
    "power_unselected",
    "required_n_enriched",
]

DESIGNS = ("unselected", "enriched", "clinical_surrogate")


@dataclass(frozen=True)
class Assumptions:
    """Human-supplied simulation inputs. Not derived from any model score."""

    control_median_months: float = 5.8
    control_median_source: str = (
        "IPASS NCT00322452 posted control-arm (carboplatin/paclitaxel) median PFS, 5.8 months"
    )
    follow_up_months: float = 24.0
    accrual_months: float = 12.0
    alpha_one_sided: float = 0.025
    allocation_ratio: float = 1.0  # treatment : control
    n_simulations: int = 2000
    seed: int = 20260922

    @property
    def control_hazard(self) -> float:
        return math.log(2.0) / self.control_median_months

    def notes(self) -> list[str]:
        return [
            (f"Control-arm event rate from an exponential fit to a median of "
                f"{self.control_median_months} months ({self.control_median_source})."),
            ("Exponential (constant-hazard) survival in both arms; a real PFS curve is not exponential, "
                "so absolute power is indicative rather than a design-grade calculation."),
            "No dropout, no loss to follow-up, and a perfect biomarker assay (no misclassification).",
            (f"Uniform accrual over {self.accrual_months} months with administrative censoring at "
                f"{self.follow_up_months} months."),
            f"One-sided log-rank test at alpha = {self.alpha_one_sided}.",
            ("Hazard ratios are taken as given from module 1 and are never converted into response "
                "probabilities."),
        ]


@dataclass
class DesignResult:
    design: str
    total_randomized: int
    responder_fraction: float | None
    simulated_power: float
    monte_carlo_se: float
    expected_screened: int
    mean_events: float
    hr_positive: float
    hr_negative: float | None
    n_simulations: int

    def to_dict(self) -> dict:
        return asdict(self)


def _split(n_total: int, ratio: float) -> tuple[int, int]:
    n_t = round(n_total * ratio / (1.0 + ratio))
    return n_t, n_total - n_t


def _run(
    n_total: int,
    hazard_treatment_fn,
    a: Assumptions,
    rng: np.random.Generator,
) -> tuple[float, float, float]:
    """Return (power, mc_se, mean_events). ``hazard_treatment_fn(n, rng)`` gives per-participant hazards."""
    n_t, n_c = _split(n_total, a.allocation_ratio)
    lam0 = a.control_hazard
    wins = 0
    events = 0
    for _ in range(a.n_simulations):
        h_t = hazard_treatment_fn(n_t, rng)
        t_t, e_t = simulate_arm(n_t, h_t, a.follow_up_months, rng, a.accrual_months)
        t_c, e_c = simulate_arm(n_c, lam0, a.follow_up_months, rng, a.accrual_months)
        res = logrank(t_t, e_t, t_c, e_c)
        wins += res.p_one_sided <= a.alpha_one_sided
        events += int(e_t.sum() + e_c.sum())
    p = wins / a.n_simulations
    se = math.sqrt(max(p * (1.0 - p), 0.0) / a.n_simulations)
    return p, se, events / a.n_simulations


def power_single_hr(n_total: int, hr: float, a: Assumptions, rng: np.random.Generator) -> DesignResult:
    """Homogeneous population: every participant experiences the same hazard ratio."""
    lam0 = a.control_hazard
    p, se, ev = _run(n_total, lambda n, r: lam0 * hr, a, rng)
    return DesignResult(
        design="homogeneous",
        total_randomized=n_total,
        responder_fraction=None,
        simulated_power=p,
        monte_carlo_se=se,
        expected_screened=n_total,
        mean_events=ev,
        hr_positive=hr,
        hr_negative=None,
        n_simulations=a.n_simulations,
    )


def power_unselected(
    n_total: int, f: float, hr_pos: float, hr_neg: float, a: Assumptions, rng: np.random.Generator,
    design: str = "unselected",
) -> DesignResult:
    """Mixture population: fraction ``f`` get ``hr_pos``, the rest ``hr_neg``."""
    if not 0.0 <= f <= 1.0:
        raise ValueError(f"responder fraction must be in [0, 1], got {f}")
    lam0 = a.control_hazard

    def hazards(n: int, r: np.random.Generator) -> np.ndarray:
        pos = r.random(n) < f
        return np.where(pos, lam0 * hr_pos, lam0 * hr_neg)

    p, se, ev = _run(n_total, hazards, a, rng)
    return DesignResult(
        design=design,
        total_randomized=n_total,
        responder_fraction=f,
        simulated_power=p,
        monte_carlo_se=se,
        expected_screened=n_total,  # nobody is screened out
        mean_events=ev,
        hr_positive=hr_pos,
        hr_negative=hr_neg,
        n_simulations=a.n_simulations,
    )


def power_enriched(
    n_total: int, f: float, hr_pos: float, a: Assumptions, rng: np.random.Generator
) -> DesignResult:
    """Only biomarker-positive participants enrol; screening burden is n / f."""
    res = power_single_hr(n_total, hr_pos, a, rng)
    res.design = "enriched"
    res.responder_fraction = f
    res.expected_screened = round(n_total / f) if f > 0 else 0
    return res


def power_grid(
    fractions: list[float],
    sizes: list[int],
    hr_pos: float,
    hr_neg: float,
    a: Assumptions,
    include_surrogate_fraction: float | None = None,
) -> list[DesignResult]:
    """Power for the unselected mixture and the enriched design over f x n."""
    rng = np.random.default_rng(a.seed)
    out: list[DesignResult] = []
    for n in sizes:
        for f in fractions:
            out.append(power_unselected(n, f, hr_pos, hr_neg, a, rng))
            out.append(power_enriched(n, f, hr_pos, a, rng))
        if include_surrogate_fraction is not None:
            out.append(
                power_unselected(
                    n, include_surrogate_fraction, hr_pos, hr_neg, a, rng, design="clinical_surrogate"
                )
            )
    return out


def calibrate(
    failed_trial_n: int,
    failed_trial_itt_hr: float,
    rescue_trial_n: int,
    rescue_trial_itt_hr: float,
    a: Assumptions,
) -> dict:
    """Does the simulator reproduce the failed trial's miss and the rescue trial's win?

    Each trial is simulated as a homogeneous population at its *observed* ITT
    hazard ratio and its actual randomised size. The check is directional: the
    failed trial should be underpowered and the rescue trial well powered. It is
    not a claim of absolute agreement — the failed trial's endpoint was overall
    survival in a refractory population, whose event rate differs from the
    control median assumed here.
    """
    rng = np.random.default_rng(a.seed + 1)
    failed = power_single_hr(failed_trial_n, failed_trial_itt_hr, a, rng)
    rescue = power_single_hr(rescue_trial_n, rescue_trial_itt_hr, a, rng)
    return {
        "failed_trial": {
            "n": failed_trial_n,
            "observed_itt_hr": failed_trial_itt_hr,
            "simulated_power": failed.simulated_power,
            "monte_carlo_se": failed.monte_carlo_se,
        },
        "rescue_trial": {
            "n": rescue_trial_n,
            "observed_itt_hr": rescue_trial_itt_hr,
            "simulated_power": rescue.simulated_power,
            "monte_carlo_se": rescue.monte_carlo_se,
        },
        "ordering_reproduced": failed.simulated_power < rescue.simulated_power,
        "caveat": (
            "Directional check only. The failed trial reported overall survival in a refractory "
            "population; the control event rate assumed here comes from first-line PFS, so absolute "
            "power is not comparable between the two rows."
        ),
    }


def min_fraction_for_power(
    n_total: int,
    hr_pos: float,
    hr_neg: float,
    a: Assumptions,
    target_power: float = 0.8,
    tol: float = 0.01,
) -> dict:
    """Smallest responder fraction at which an unselected trial of size n reaches target power.

    Bisection on f. Returns ``None`` for the fraction when even f = 1 falls short.
    """
    rng = np.random.default_rng(a.seed + 2)
    top = power_unselected(n_total, 1.0, hr_pos, hr_neg, a, rng)
    if top.simulated_power < target_power:
        return {
            "n_total": n_total,
            "target_power": target_power,
            "fraction": None,
            "note": (
                f"Even an all-positive population reaches only {top.simulated_power:.2f} power at "
                f"n={n_total}; this trial size cannot reach the target at any responder fraction."
            ),
        }
    lo, hi = 0.0, 1.0
    while hi - lo > tol:
        mid = (lo + hi) / 2.0
        if power_unselected(n_total, mid, hr_pos, hr_neg, a, rng).simulated_power >= target_power:
            hi = mid
        else:
            lo = mid
    return {"n_total": n_total, "target_power": target_power, "fraction": round(hi, 3), "note": ""}


def required_n_enriched(
    hr_pos: float,
    f: float,
    a: Assumptions,
    target_power: float = 0.8,
    candidates: tuple[int, ...] = (60, 100, 150, 200, 300, 400, 600, 800, 1200),
) -> dict:
    """Smallest candidate size at which the enriched design reaches target power."""
    rng = np.random.default_rng(a.seed + 3)
    for n in candidates:
        res = power_enriched(n, f, hr_pos, a, rng)
        if res.simulated_power >= target_power:
            return {
                "n_randomized": n,
                "expected_screened": res.expected_screened,
                "simulated_power": res.simulated_power,
                "target_power": target_power,
                "responder_fraction": f,
            }
    return {
        "n_randomized": None,
        "expected_screened": None,
        "simulated_power": None,
        "target_power": target_power,
        "responder_fraction": f,
        "note": f"No candidate size up to {candidates[-1]} reached {target_power:.0%} power.",
    }
