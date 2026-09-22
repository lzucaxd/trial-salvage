"""Module 4: log-rank test, arm simulation, and design power. No network."""
from __future__ import annotations

import math

import numpy as np
import pytest

from trial_salvage.module4.simulate import (
    Assumptions,
    calibrate,
    min_fraction_for_power,
    power_enriched,
    power_grid,
    power_single_hr,
    power_unselected,
    required_n_enriched,
)
from trial_salvage.module4.survival import logrank, simulate_arm

FAST = Assumptions(n_simulations=150, seed=11)


# ------------------------------------------------------------------ log-rank


def test_logrank_matches_hand_computed_two_by_two():
    """Four participants, one event each arm at distinct times -> checkable by hand.

    Event times 1 (arm A) and 2 (arm B), both arms starting with 2 at risk.
    t=1: n_a=2, n_b=2, d=1 -> E_a = 0.5, V = 1*(2/4)*(2/4)*(3/3) = 0.25
    t=2: n_a=1, n_b=2, d=1 -> E_a = 1/3, V = 1*(1/3)*(2/3)*(2/2) = 2/9
    O_a = 1, E_a = 0.5 + 1/3 = 5/6, V = 0.25 + 2/9 = 17/36
    """
    t_a, e_a = np.array([1.0, 3.0]), np.array([True, False])
    t_b, e_b = np.array([2.0, 3.0]), np.array([True, False])
    r = logrank(t_a, e_a, t_b, e_b)
    assert r.observed_events_treatment == 1
    assert math.isclose(r.expected_events_treatment, 5 / 6, rel_tol=1e-12)
    assert math.isclose(r.variance, 17 / 36, rel_tol=1e-12)
    assert math.isclose(r.z, (1 - 5 / 6) / math.sqrt(17 / 36), rel_tol=1e-12)


def test_logrank_direction_and_pvalue_tails():
    """Fewer events in arm A must give a negative z and a small one-sided p."""
    rng = np.random.default_rng(3)
    lam = math.log(2) / 6.0
    t_a, e_a = simulate_arm(300, lam * 0.4, 24.0, rng)
    t_b, e_b = simulate_arm(300, lam, 24.0, rng)
    r = logrank(t_a, e_a, t_b, e_b)
    assert r.z < 0
    assert r.favours_treatment
    assert r.p_one_sided < 0.001
    assert math.isclose(r.p_two_sided, 2 * min(r.p_one_sided, 1 - r.p_one_sided), rel_tol=1e-9)


def test_logrank_no_events_is_neutral():
    t = np.array([5.0, 5.0])
    no = np.array([False, False])
    r = logrank(t, no, t, no)
    assert r.z == 0.0 and r.p_one_sided == 0.5 and r.variance == 0.0


def test_logrank_handles_ties_without_nan():
    t_a, e_a = np.array([1.0, 1.0, 2.0]), np.array([True, True, False])
    t_b, e_b = np.array([1.0, 2.0, 2.0]), np.array([True, True, False])
    r = logrank(t_a, e_a, t_b, e_b)
    assert not math.isnan(r.z) and r.variance > 0


# -------------------------------------------------------------- arm sampling


def test_simulate_arm_censors_at_follow_up_and_flags_events():
    rng = np.random.default_rng(0)
    t, e = simulate_arm(500, math.log(2) / 6.0, 10.0, rng)
    assert t.max() <= 10.0 + 1e-9
    assert e.sum() < 500  # some must be censored at 10 months
    assert np.all(t[~e] == pytest.approx(10.0))


def test_simulate_arm_rejects_non_positive_hazard():
    with pytest.raises(ValueError, match="hazard"):
        simulate_arm(10, 0.0, 12.0, np.random.default_rng(0))


# ------------------------------------------------------------ design power


def test_power_rises_with_sample_size():
    rng = np.random.default_rng(5)
    small = power_single_hr(100, 0.6, FAST, rng).simulated_power
    large = power_single_hr(600, 0.6, FAST, rng).simulated_power
    assert large > small


def test_enrichment_beats_unselected_when_negatives_are_harmed():
    """With hr_neg > 1 the mixture dilutes and can reverse the effect."""
    rng = np.random.default_rng(7)
    unsel = power_unselected(400, 0.3, 0.48, 2.85, FAST, rng)
    enr = power_enriched(400, 0.3, 0.48, FAST, rng)
    assert enr.simulated_power > unsel.simulated_power
    assert unsel.simulated_power < 0.2


def test_enriched_screening_burden_is_n_over_prevalence():
    rng = np.random.default_rng(1)
    r = power_enriched(200, 0.25, 0.48, FAST, rng)
    assert r.expected_screened == 800
    unsel = power_unselected(200, 0.25, 0.48, 2.85, FAST, rng)
    assert unsel.expected_screened == 200  # nobody screened out


def test_responder_fraction_must_be_a_probability():
    rng = np.random.default_rng(1)
    with pytest.raises(ValueError, match="responder fraction"):
        power_unselected(100, 1.4, 0.48, 2.85, FAST, rng)


def test_power_grid_covers_both_designs_and_optional_surrogate():
    grid = power_grid([0.3, 0.6], [100], 0.48, 2.85, FAST, include_surrogate_fraction=0.6)
    designs = {r.design for r in grid}
    assert designs == {"unselected", "enriched", "clinical_surrogate"}
    assert len([r for r in grid if r.design == "unselected"]) == 2


def test_min_fraction_reports_none_when_size_cannot_reach_target():
    res = min_fraction_for_power(20, 0.48, 2.85, FAST, target_power=0.8)
    assert res["fraction"] is None
    assert "cannot reach" in res["note"]


def test_min_fraction_is_a_probability_when_achievable():
    res = min_fraction_for_power(800, 0.48, 2.85, FAST, target_power=0.8)
    assert res["fraction"] is not None
    assert 0.0 <= res["fraction"] <= 1.0


def test_required_n_enriched_reports_screening_burden():
    res = required_n_enriched(0.48, 0.25, FAST, target_power=0.8)
    assert res["n_randomized"] is not None
    assert res["expected_screened"] == round(res["n_randomized"] / 0.25)


def test_calibration_reproduces_miss_versus_win_ordering():
    cal = calibrate(1692, 0.89, 1329, 0.74, FAST)
    assert cal["failed_trial"]["simulated_power"] < cal["rescue_trial"]["simulated_power"]
    assert cal["ordering_reproduced"] is True
    assert cal["caveat"]  # the endpoint mismatch must be stated, not implied


def test_assumptions_are_declared_and_control_hazard_follows_the_median():
    a = Assumptions(control_median_months=5.8)
    assert math.isclose(a.control_hazard, math.log(2) / 5.8)
    joined = " ".join(a.notes()).lower()
    # The prohibition on converting hazard ratios must travel with the output.
    assert "never converted into response" in joined
    assert "exponential" in joined and "dropout" in joined


def test_design_result_carries_no_response_rate_field():
    """Guard against a hazard ratio being silently turned into a response probability."""
    rng = np.random.default_rng(2)
    d = power_unselected(100, 0.5, 0.48, 2.85, FAST, rng).to_dict()
    assert not any("response" in k or "responder_rate" in k for k in d)
    assert "hr_positive" in d and "hr_negative" in d
