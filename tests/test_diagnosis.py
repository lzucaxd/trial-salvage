import yaml

from trial_salvage.module1.effects import load_effects
from trial_salvage.module1.failure_analysis import diagnose


def test_gefitinib_diagnosis_is_population_dilution():
    with open("config/assets/gefitinib.yaml") as fh:
        cfg = yaml.safe_load(fh)
    eff = load_effects("data/curated/gefitinib_effects.csv")
    d = diagnose(eff, cfg)
    assert d["failure_mode"] == "population_dilution_qualitative_interaction"
    fired = {e["rule"] for e in d["evidence"] if e["fired"]}
    assert {"primary_endpoint_missed", "prespecified_subgroup_benefit", "qualitative_interaction_in_rescue_trial"} <= fired
    assert 0.55 < d["mixture_model"]["fraction_for_hr_1.00"] < 0.62  # ln(1/2.85)/ln(0.48/2.85) = 0.588
