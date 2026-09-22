"""Module 4: rescue-strategy tiering and ranking. No network."""
from __future__ import annotations

import json

from trial_salvage.module4.strategies import TIERS, rank_strategies

M1 = {
    "asset": {"name": "gefitinib"},
    "target": {"symbol": "EGFR"},
    "failure_diagnosis": {
        "failure_mode": "population_dilution_qualitative_interaction",
        "evidence": [
            {"rule": "primary_endpoint_missed", "fired": True, "detail": "HR 0.89"},
            {"rule": "prespecified_subgroup_benefit", "fired": True, "detail": "never-smokers"},
            {"rule": "qualitative_interaction_in_rescue_trial", "fired": True, "detail": "0.48 vs 2.85"},
            {"rule": "os_confounded_by_crossover", "fired": False, "detail": ""},
        ],
    },
    "salvage_strategies": [
        {"strategy": "biomarker_enrichment_new_inclusion_criteria", "used": True, "evidence": "subgroup split"},
        {"strategy": "clinical_surrogate_enrichment", "used": True, "evidence": "histology/smoking"},
        {"strategy": "new_endpoint", "used": True, "evidence": "OS -> PFS"},
        {"strategy": "molecule_modification", "used": False, "evidence": "not for this asset"},
    ],
}


def test_enrichment_is_tier_1_and_ranked_first():
    out = rank_strategies(M1)
    assert out[0].strategy == "biomarker_enrichment_new_inclusion_criteria"
    assert out[0].tier == TIERS[0]
    assert out[0].rank == 1
    # It must cite the diagnosis rules that put it on clinical footing.
    assert "qualitative_interaction_in_rescue_trial" in out[0].supporting_rules


def test_unfired_rule_does_not_grant_tier_1():
    """new_endpoint's only supporting rule did not fire here, so it cannot be tier 1."""
    out = {s.strategy: s for s in rank_strategies(M1)}
    assert out["new_endpoint"].supporting_rules == []
    assert out["new_endpoint"].tier == TIERS[1]
    assert any("no diagnosis rule" in n for n in out["new_endpoint"].notes)


def test_molecule_modification_is_tier_4_and_defers_to_module2():
    out = {s.strategy: s for s in rank_strategies(M1)}
    s = out["molecule_modification"]
    assert s.tier == TIERS[3]
    assert "module 2" in s.next_experiment


def test_every_strategy_has_a_next_experiment_and_a_falsifier():
    for s in rank_strategies(M1):
        assert s.next_experiment.strip(), f"{s.strategy} has no next experiment"
        assert s.would_be_undermined_by.strip(), f"{s.strategy} has no falsifying observation"


def test_ranking_is_tier_ordered_and_ranks_are_dense():
    out = rank_strategies(M1)
    order = {t: i for i, t in enumerate(TIERS)}
    tiers = [order[s.tier] for s in out]
    assert tiers == sorted(tiers)
    assert [s.rank for s in out] == list(range(1, len(out) + 1))


def test_no_numeric_probability_of_rescue_is_emitted():
    """The spec forbids a success probability; only tiers are allowed to rank."""
    blob = json.dumps([s.to_dict() for s in rank_strategies(M1)]).lower()
    for banned in ("probability_of_rescue", "success_probability", "p_success", "rescue_probability"):
        assert banned not in blob


def test_design_consequence_is_attached_only_when_supplied():
    plain = {s.strategy: s for s in rank_strategies(M1)}
    assert plain["biomarker_enrichment_new_inclusion_criteria"].design_consequence is None

    req = {"n_randomized": 100, "expected_screened": 400, "responder_fraction": 0.25}
    withsim = {s.strategy: s for s in rank_strategies(M1, enrichment_design=req)}
    assert withsim["biomarker_enrichment_new_inclusion_criteria"].design_consequence == req


def test_unselected_reference_is_quoted_on_the_enrichment_entry():
    ref = {"simulated_power": 0.12, "total_randomized": 400, "responder_fraction": 0.3}
    out = {s.strategy: s for s in rank_strategies(M1, unselected_reference=ref)}
    notes = " ".join(out["biomarker_enrichment_new_inclusion_criteria"].notes)
    assert "0.12" in notes and "400" in notes
