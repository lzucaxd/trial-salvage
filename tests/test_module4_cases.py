"""Module 4: retrospective replication check, benchmark validation, curated cases. Offline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from trial_salvage.module4.benchmark import evaluate, load_benchmark, provenance_contrast
from trial_salvage.module4.compare import comparison_table
from trial_salvage.module4.retrospect import crosses_no_effect, retrospective_check
from trial_salvage.module4.simulate import Assumptions

BENCH = "data/benchmark/rescue_benchmark_v0.csv"
CASES = Path("data/cases")
FAST = Assumptions(n_simulations=120, seed=5)


# ------------------------------------------------- retrospective check


def test_circular_comparison_is_refused_not_scored():
    """An estimate measured in the trial that checks it carries no predictive information."""
    r = retrospective_check(0.48, 0.48, 1329, FAST, independent_test=False)
    assert r["verdict"] == "not_an_independent_test"
    assert "implied_distribution" not in r
    assert "no predictive information" in r["note"]


def test_inverted_effect_does_not_replicate():
    """onartuzumab's shape: prior 0.37, retry returned 1.27 at n=499."""
    r = retrospective_check(0.37, 1.27, 499, FAST, independent_test=True)
    assert r["verdict"] == "did_not_replicate"
    d = r["implied_distribution"]
    assert d["hr_2.5_pct"] < 0.37 < d["hr_97.5_pct"]
    assert 1.27 > d["hr_97.5_pct"]
    assert r["observed_percentile_of_implied"] == pytest.approx(1.0, abs=1e-6)
    assert "did not survive its prospective test" in r["note"]


def test_consistent_effect_replicates():
    r = retrospective_check(0.60, 0.62, 800, FAST, independent_test=True)
    assert r["verdict"] == "replicated"
    assert "survived its prospective test" in r["note"]


def test_missing_inputs_are_not_assessable():
    for args in [(None, 1.2, 400), (0.5, None, 400), (0.5, 1.2, None)]:
        assert retrospective_check(*args, FAST, independent_test=True)["verdict"] == "not_assessable"


def test_crosses_no_effect_detects_sign_change():
    assert crosses_no_effect(0.37, 1.27)
    assert not crosses_no_effect(0.48, 0.74)
    assert not crosses_no_effect(1.2, 1.5)


# ------------------------------------------------------- benchmark


def test_benchmark_requires_its_columns():
    with pytest.raises(ValueError, match="missing required columns"):
        load_benchmark_stub()


def load_benchmark_stub():
    import pandas as pd
    tmp = Path("/tmp/_bad_bench.csv")
    pd.DataFrame({"asset": ["x"], "outcome": ["fail"]}).to_csv(tmp, index=False)
    return load_benchmark(tmp)


def test_provenance_contrast_favours_prespecified_and_survives_cluster_removal():
    """The claim module 4's tiering rests on, tested on the committed benchmark."""
    pc = provenance_contrast(load_benchmark(BENCH))
    strong = pc["all_decided"]["prespecified_or_mechanistic"]
    weak = pc["all_decided"]["post_hoc_subgroup"]
    assert strong["success_rate"] > weak["success_rate"]
    assert pc["all_decided"]["fisher_p"] < 0.05
    # Module 3's genomic verdict lost its signal here; this contrast must not.
    assert pc["cluster_removed"]["fisher_p"] < 0.05
    assert pc["survives_cluster_removal"] is True
    assert pc["clusters_removed"] == ["EGFR-mut NSCLC"]
    assert pc["cluster_removed"]["n_pairs"] < pc["all_decided"]["n_pairs"]


def test_undecided_pairs_are_excluded_and_listed():
    pc = provenance_contrast(load_benchmark(BENCH))
    assert set(pc["excluded_outcomes"]) <= {"contested", "pending"}
    counted = (pc["all_decided"]["prespecified_or_mechanistic"]["n"]
               + pc["all_decided"]["post_hoc_subgroup"]["n"])
    assert counted == pc["all_decided"]["n_pairs"]


def test_evaluate_reports_the_claim_and_its_caveats():
    res = evaluate(BENCH)
    assert "provenance" in res["claim_under_test"]
    assert any("small" in c for c in res["caveats"])
    groups = {r["class"]: r for r in res["by_biomarker_group"]}
    # Driver mutations delivered; protein-expression markers did not.
    assert groups["somatic_driver_mutation"]["fail"] == 0
    assert groups["protein_expression"]["success"] == 0


# ------------------------------------------------------ curated cases


@pytest.mark.parametrize("name", ["gefitinib_module4.json", "onartuzumab_module4.json"])
def test_case_files_carry_provenance_and_an_outcome(name):
    c = json.loads((CASES / name).read_text())
    assert c["outcome"]["class"] in ("fail_then_retry_then_succeed", "fail_then_retry_then_fail_again",
                                     "fail_then_not_retried")
    assert c["outcome"]["source"]
    eq = c["evidence_quality"]
    assert eq["motivating_signal"] in ("prespecified_or_mechanistic", "post_hoc_subgroup")
    assert isinstance(eq["hr_pos_measured_in_retry_trial"], bool)
    # Every pre-retry row and the retry row must name where the number came from.
    for row in c.get("pre_retry_evidence", []) + [c["retry_result"]]:
        assert row["source"], f"{name}: {row.get('label')} has no source"
        assert row["hr"] > 0


def test_onartuzumab_case_is_runnable_by_module4():
    c = json.loads((CASES / "onartuzumab_module4.json").read_text())
    h = c["handoff"]["module4"]
    for k in ("endpoint", "hr_pos", "hr_neg", "failed_trial_n", "rescue_trial_n"):
        assert h.get(k) is not None, f"handoff missing {k}"
    assert h["hr_pos"] < 1 < h["hr_neg"]  # the qualitative interaction it was retried on
    assert c["assumption_overrides"]["control_median_months"] > 0


def test_comparison_table_pairs_design_evidence_against_outcome():
    cases = [json.loads((CASES / n).read_text())
             for n in ("gefitinib_module4.json", "onartuzumab_module4.json")]
    rows = comparison_table(cases)
    assert [r["asset"] for r in rows] == ["gefitinib", "onartuzumab"]
    gef, onart = rows
    assert gef["outcome_class"] == "retried, succeeded"
    assert onart["outcome_class"] == "retried, failed again"
    # Both entered their retry with a comparable subgroup signal...
    assert gef["best_pre_retry_hr"] < 1 and onart["best_pre_retry_hr"] < 1
    # ...and only onartuzumab's retry landed on the wrong side of 1.
    assert gef["retry_observed_hr"] < 1 < onart["retry_observed_hr"]
    assert onart["cutoff_chosen_on_outcome"] is True
    assert gef["replicated_independently"] is True


def test_case_metadata_combines_with_module1_handoff(tmp_path):
    """--module1 supplies the handoff; --case adds the outcome and provenance."""
    from trial_salvage.module4.run import main as run_main
    m1 = Path("outputs/module1/module1_output.json")
    if not m1.exists():
        pytest.skip("run `make module1-offline` first")
    rc = run_main(["--module1", str(m1), "--case", str(CASES / "gefitinib_module4.json"),
                   "--outdir", str(tmp_path), "--quick"])
    assert rc == 0
    out = json.loads((tmp_path / "module4_output.json").read_text())
    # Handoff came from module 1 ...
    assert out["inputs"]["hr_pos"] == 0.48
    # ... while the outcome and provenance came from the case file.
    assert out["observed_outcome"]["class"] == "fail_then_retry_then_succeed"
    assert out["evidence_quality"]["motivating_signal"] == "prespecified_or_mechanistic"
    assert out["retrospective_check"]["verdict"] == "not_an_independent_test"
