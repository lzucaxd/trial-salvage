import pandas as pd
import pytest

from trial_salvage.module3 import benchmark_eval as be


def rec(name, targets, syn=()):
    return {"name": name, "drugType": "Small molecule", "synonyms": [{"label": s} for s in syn], "tradeNames": [],
            "mechanismsOfAction": {"rows": [{"targets": [{"approvedSymbol": t} for t in targets]}]}}


def test_asset_query_strips_parenthetical():
    assert be.asset_query("ocrelizumab (after rituximab)") == "ocrelizumab"
    assert be.asset_query("gefitinib") == "gefitinib"


def test_mapping_statuses():
    hit = {"id": "CHEMBL1"}
    assert be.mapping_row("x", None, None)["mapping"] == "unmapped_no_hit"
    assert be.mapping_row("MAGE-A3 vaccine", hit, rec("MIDAZOLAM", ["GABRA1"]))["mapping"] == "unmapped_name_mismatch"
    assert be.mapping_row("pirfenidone", hit, rec("PIRFENIDONE", []))["mapping"] == "mapped_no_targets"
    big = rec("ATALUREN", [f"RPL{i}" for i in range(be.MAX_TARGETS + 1)])
    assert be.mapping_row("ataluren", hit, big)["mapping"] == "complex_target"
    ok = be.mapping_row("gefitinib", hit, rec("GEFITINIB", ["EGFR"]))
    assert ok["mapping"] == "mapped" and ok["targets"] == ["EGFR"]


def test_target_lane_thresholds_and_order():
    assert be.target_lane(True, 0.01, 0.1, 0) == "somatic"
    assert be.target_lane(False, 0.5, 0.1, 0) == "none_detected"  # somatic lane is oncology-only
    assert be.target_lane(True, 0.009, 0.6, 3) == "germline_common"
    assert be.target_lane(False, None, 0.59, 10) == "none_detected"  # constrained
    assert be.target_lane(False, None, 1.2, 2) == "none_detected"
    assert be.target_lane(False, None, float("nan"), float("nan")) == "none_detected"


def test_asset_lane_any_target_first_lane():
    assert be.asset_lane(["none_detected", "germline_common", "somatic"], "mapped") == "somatic"
    assert be.asset_lane(["none_detected", "germline_common"], "mapped") == "germline_common"
    assert be.asset_lane(["somatic"], "complex_target") == "not_evaluable"
    assert be.asset_lane([], "mapped") == "not_evaluable"


def test_regime_match():
    assert be.regime_match("somatic", "somatic_driver_mutation") == "match"
    assert be.regime_match("none_detected", "somatic_alteration") == "miss"
    assert be.regime_match("somatic", "clinical") == "lane_without_genomic_retry"
    assert be.regime_match("none_detected", "circulating_biomarker") == "retry_not_genomic"
    assert be.regime_match("somatic", "germline_monogenic") == "monogenic_not_modelled"
    assert be.regime_match("not_evaluable", "clinical") == "not_evaluable"


def test_somatic_summary_counts_samples_not_calls():
    raw = {"study": "s", "n_samples": 100, "mutations": [
        {"sampleId": "a", "proteinChange": "L858R"}, {"sampleId": "a", "proteinChange": "T790M"},
        {"sampleId": "b", "proteinChange": "L858R"}, {"sampleId": "b", "proteinChange": "L858R"},
        {"sampleId": "c", "proteinChange": None}]}
    s = be.somatic_summary(raw)
    assert s["frac_any_mut"] == pytest.approx(0.03)
    assert (s["top_change"], s["top_change_n"]) == ("L858R", 2)
    assert s["top_change_freq"] == pytest.approx(0.02)
    empty = be.somatic_summary({"study": "s", "n_samples": 10, "mutations": []})
    assert empty["top_change"] is None and empty["top_change_freq"] == 0


def test_fisher_matches_known_values():
    assert be.fisher_2x2(3, 1, 1, 3) == pytest.approx(0.4857, abs=1e-4)
    assert be.fisher_2x2(4, 0, 0, 4) == pytest.approx(0.02857, abs=1e-4)
    assert be.fisher_2x2(0, 5, 0, 5) == pytest.approx(1.0)


def test_overlap_by_nct_and_name():
    bench = pd.DataFrame({"asset": ["Aducanumab", "foo (x)"], "failed_nct": ["N1", "N9"],
                          "retry_nct": ["N2", "N8"]})
    cands = pd.DataFrame({"nct": ["N2", "N5"], "drug": ["ADUCANUMAB", "FOO"], "cond": ["AD", "c"]})
    o = be.overlap(bench, cands)
    assert set(zip(o.asset, o.match)) == {("Aducanumab", "retry_nct"), ("Aducanumab", "asset_name"),
                                          ("foo (x)", "asset_name")}


def test_parse_constraint_keeps_missing_genes():
    js = {"data": {"g0": {"gene_id": "E1", "gnomad_constraint": {"oe_lof_upper": 0.7, "pLI": 0.1, "mis_z": 1}},
                   "g1": None}}
    out = be.parse_constraint(js, ["A", "B"])
    assert out["A"]["LOEUF"] == 0.7 and out["B"]["LOEUF"] is None


def test_cached_gnomad_never_refetches(tmp_path, monkeypatch):
    cache = be.Cache(tmp_path)
    cache.put("gnomad_variants", "EGFR", [{"consequence": "missense_variant", "joint": {"ac": 1, "an": 2}}])
    cache.put("gnomad_constraint", "EGFR", {"symbol": "EGFR", "LOEUF": 0.3})

    def boom(*a, **k):
        raise AssertionError("network call")

    monkeypatch.setattr(be.requests, "post", boom)
    gn = be.PacedGnomad(cache)
    assert len(gn.variants("EGFR")) == 1
    assert gn.constraint(["EGFR"])["EGFR"]["LOEUF"] == 0.3


def test_build_pairs_offline():
    bench = pd.DataFrame({"asset": ["a", "b"], "failed_nct": ["N1", None], "retry_nct": ["N2", "N3"],
                          "therapeutic_area": ["oncology", "non-oncology"], "indication": ["NSCLC", "x"],
                          "outcome": ["success", "fail"], "biomarker_group": ["somatic_driver_mutation", "clinical"],
                          "biomarker_class": ["", ""], "same_driver_cluster": ["EGFR-mut NSCLC", None],
                          "motivating_signal": ["", ""]})
    maps = [{"mapping": "mapped", "targets": ["EGFR"], "n_targets": 1, "chembl": "C1"},
            {"mapping": "mapped_no_targets", "targets": [], "n_targets": 0, "chembl": "C2"}]
    targets = pd.DataFrame([{"pair_id": 0, "asset": "a", "target": "EGFR", "LOEUF": 0.3, "n_common_func": 1,
                             "study": "s", "frac_any_mut": 0.2, "top_change": "L858R", "top_change_freq": 0.05,
                             "target_lane": "somatic"}])
    p = be.build_pairs(bench, maps, targets)
    assert list(p.lane_verdict) == ["somatic", "not_evaluable"]
    assert p.regime_match.iloc[0] == "match" and p.somatic_top_change.iloc[0] == "L858R"
