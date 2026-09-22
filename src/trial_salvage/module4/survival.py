"""Exponential time-to-event simulation and a log-rank test.

Module 1 hands module 4 *hazard ratios* (``hr_pos``, ``hr_neg``), so the trial
being simulated is a time-to-event trial and the test is the log-rank test. The
alternative — converting a hazard ratio into a binary response probability — is
not a defined operation and is deliberately not attempted anywhere in this
module.

Two notes on method:

* **The mixture is simulated, not approximated.** Module 1's
  ``mixture_hr_by_fraction`` is a log-linear approximation and says so. Here each
  participant is drawn with their own stratum hazard and the log-rank test is run
  unstratified on the pooled sample, which is what an unselected trial actually
  does. Hazard ratios are not collapsible across strata, so the pooled estimate
  is not the weighted mean of the stratum ratios — simulating avoids having to
  assume it is.
* **No new dependency.** The log-rank statistic is the standard
  observed-minus-expected form with hypergeometric variance, and the p-value
  comes from the normal approximation via ``math.erfc``. This keeps module 4
  installable from the repo's existing dependency set.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

__all__ = ["LogrankResult", "logrank", "simulate_arm", "simulate_two_arm_trial"]


@dataclass(frozen=True)
class LogrankResult:
    z: float
    p_one_sided: float
    p_two_sided: float
    observed_events_treatment: int
    expected_events_treatment: float
    variance: float

    @property
    def favours_treatment(self) -> bool:
        """True when the treatment arm accrued fewer events than expected."""
        return self.observed_events_treatment < self.expected_events_treatment


def _norm_sf(z: float) -> float:
    """Upper-tail standard normal probability."""
    return 0.5 * math.erfc(z / math.sqrt(2.0))


def logrank(
    time_a: np.ndarray,
    event_a: np.ndarray,
    time_b: np.ndarray,
    event_b: np.ndarray,
) -> LogrankResult:
    """Two-sample log-rank test. Arm A is the arm the statistic is reported for.

    ``p_one_sided`` is the probability of an effect at least this favourable to
    arm A, i.e. the tail in which A has *fewer* events than expected.
    """
    time_a, event_a = np.asarray(time_a, float), np.asarray(event_a, bool)
    time_b, event_b = np.asarray(time_b, float), np.asarray(event_b, bool)

    times = np.concatenate([time_a, time_b])
    events = np.concatenate([event_a, event_b])
    event_times = np.unique(times[events])
    if event_times.size == 0:
        return LogrankResult(0.0, 0.5, 1.0, 0, 0.0, 0.0)

    # Risk sets and event counts at each distinct event time, via searchsorted:
    # O((n + k) log n) rather than the O(n * k) broadcast a power grid cannot afford.
    sa, sb = np.sort(time_a), np.sort(time_b)
    n_a = (time_a.size - np.searchsorted(sa, event_times, side="left")).astype(float)
    n_b = (time_b.size - np.searchsorted(sb, event_times, side="left")).astype(float)

    ea, eb = np.sort(time_a[event_a]), np.sort(time_b[event_b])
    d_a = (
        np.searchsorted(ea, event_times, side="right") - np.searchsorted(ea, event_times, side="left")
    ).astype(float)
    d_b = (
        np.searchsorted(eb, event_times, side="right") - np.searchsorted(eb, event_times, side="left")
    ).astype(float)

    n = n_a + n_b
    d = d_a + d_b
    # Expected events in arm A and hypergeometric variance, guarding n == 1.
    # np.where evaluates both branches, so the guards go in the denominators too:
    # a risk set of size 1 would otherwise produce 0/0 and a RuntimeWarning.
    n_safe = np.where(n > 0, n, 1.0)
    n_minus_1_safe = np.where(n > 1, n - 1.0, 1.0)
    expected_a = np.where(n > 0, d * n_a / n_safe, 0.0)
    var = np.where(n > 1, d * (n_a / n_safe) * (n_b / n_safe) * ((n - d) / n_minus_1_safe), 0.0)

    o_minus_e = float(d_a.sum() - expected_a.sum())
    v = float(var.sum())
    if v <= 0:
        return LogrankResult(0.0, 0.5, 1.0, int(d_a.sum()), float(expected_a.sum()), 0.0)

    z = o_minus_e / math.sqrt(v)  # negative when arm A has fewer events than expected
    return LogrankResult(
        z=z,
        p_one_sided=_norm_sf(-z),
        p_two_sided=2.0 * _norm_sf(abs(z)),
        observed_events_treatment=int(d_a.sum()),
        expected_events_treatment=float(expected_a.sum()),
        variance=v,
    )


def simulate_arm(
    n: int,
    hazard: np.ndarray | float,
    follow_up_months: float,
    rng: np.random.Generator,
    accrual_months: float = 0.0,
) -> tuple[np.ndarray, np.ndarray]:
    """Exponential event times with administrative censoring.

    ``hazard`` may be scalar or per-participant (for a mixture population). With
    ``accrual_months > 0``, entry is uniform over the accrual window and each
    participant is censored at their own remaining follow-up.
    """
    if n <= 0:
        return np.empty(0), np.empty(0, dtype=bool)
    h = np.broadcast_to(np.asarray(hazard, float), (n,))
    if np.any(h <= 0):
        raise ValueError("hazard must be positive")
    t_event = rng.exponential(1.0 / h)
    if accrual_months > 0:
        entry = rng.uniform(0.0, accrual_months, size=n)
        censor_at = np.maximum(follow_up_months - entry, 0.0)
    else:
        censor_at = np.full(n, float(follow_up_months))
    observed = np.minimum(t_event, censor_at)
    event = t_event <= censor_at
    return observed, event


def simulate_two_arm_trial(
    n_treatment: int,
    n_control: int,
    hazard_treatment: np.ndarray | float,
    hazard_control: np.ndarray | float,
    follow_up_months: float,
    rng: np.random.Generator,
    accrual_months: float = 0.0,
) -> LogrankResult:
    """One simulated trial; the statistic is reported for the treatment arm."""
    t_t, e_t = simulate_arm(n_treatment, hazard_treatment, follow_up_months, rng, accrual_months)
    t_c, e_c = simulate_arm(n_control, hazard_control, follow_up_months, rng, accrual_months)
    return logrank(t_t, e_t, t_c, e_c)
