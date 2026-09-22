import math

import pandas as pd

from trial_salvage.module1.effects import fraction_for_target_hr, load_effects, mixture_hr, provenance_check


def test_mixture_endpoints():
    assert math.isclose(mixture_hr(1.0, 0.48, 2.85), 0.48)
    assert math.isclose(mixture_hr(0.0, 0.48, 2.85), 2.85)


def test_fraction_for_target():
    f = fraction_for_target_hr(1.0, 0.48, 2.85)
    assert 0.5 < f < 0.7
    assert fraction_for_target_hr(0.3, 0.48, 2.85) is None


def test_provenance_check_uses_abstract_text():
    eff = pd.DataFrame({"trial": ["X"], "population": ["p"], "endpoint": ["OS"], "hr": [0.89],
                        "ci_lo": [0.77], "ci_hi": [1.02], "p": ["0.087"], "n": ["1692"], "pmid": ["1"],
                        "nct": ["NCT0"], "analysis_type": ["prespecified primary"], "note": [""]})
    ok = provenance_check(eff, {"1": {"abstract": "hazard ratio 0.89 [95% CI 0.77-1.02]"}})
    bad = provenance_check(eff, {"1": {"abstract": "hazard ratio 0.79"}})
    assert ok.hr_in_abstract.iloc[0] and not bad.hr_in_abstract.iloc[0]


def test_curated_gefitinib_effects_load(tmp_path):
    df = load_effects("data/curated/gefitinib_effects.csv")
    assert len(df) >= 16 and df.hr.gt(0).all()
    assert df[df.population.str.contains("mutation-negative") & (df.endpoint == "PFS")].significant.all()
