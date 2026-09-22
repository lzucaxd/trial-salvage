import pytest

from trial_salvage.biodata import name_matches
from trial_salvage.gnomad import MAX_ALIASES, constraint_query
from trial_salvage.module3.germline import maf, stratification_scores, summarize_variants


def v(csq, ac, an=1000):
    return {"consequence": csq, "joint": {"ac": ac, "an": an}}


def test_maf_folds_major_alt_allele():
    # PCSK9 had a variant at AF 0.954: the *reference* is the minor allele.
    assert maf(954, 1000) == pytest.approx(0.046)
    assert maf(5, 1000) == pytest.approx(0.005)
    assert maf(0, 0) is None


def test_summarize_counts_only_common_functional():
    vs = [v("missense_variant", 200), v("stop_gained", 50), v("synonymous_variant", 300),
          v("missense_variant", 5), v("intron_variant", 400), {"consequence": "missense_variant", "joint": None}]
    s = summarize_variants("X", vs)
    assert s["n_variants"] == 5
    assert s["n_common"] == 4
    assert s["n_common_func"] == 2
    assert s["n_common_lof"] == 1
    assert s["cum_maf_func"] == pytest.approx(0.25)


def test_score_needs_both_tolerance_and_burden():
    rows = [{"symbol": "tolerant_varied", "LOEUF": 1.6, "n_common_func": 10},
            {"symbol": "constrained_varied", "LOEUF": 0.2, "n_common_func": 10},
            {"symbol": "tolerant_empty", "LOEUF": 1.6, "n_common_func": 0},
            {"symbol": "missing", "LOEUF": None, "n_common_func": None}]
    sc = {r["symbol"]: r["score"] for r in stratification_scores(rows)}
    assert sc["tolerant_varied"] > sc["constrained_varied"] > sc["tolerant_empty"] == 0
    assert sc["missing"] is None


def test_constraint_query_respects_cost_cap():
    q = constraint_query(["CYP2D6", "EGFR"])
    assert q.count("gene(") == 2 and "g1:" in q
    with pytest.raises(ValueError):
        constraint_query(["G"] * (MAX_ALIASES + 1))


def test_name_guard_rejects_fuzzy_false_hits():
    midazolam = {"name": "MIDAZOLAM", "synonyms": [{"label": "Versed"}], "tradeNames": []}
    obefazimod = {"name": "OBEFAZIMOD", "synonyms": [{"label": "ABX464"}, {"label": "ABX-464"}], "tradeNames": []}
    assert not name_matches("0.9% sodium chloride", midazolam)
    assert name_matches("abx464", obefazimod)
    assert name_matches("Obefazimod", obefazimod)
    assert not name_matches("anything", None)
