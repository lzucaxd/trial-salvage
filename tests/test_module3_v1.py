import pandas as pd
import pytest

from trial_salvage import gnomad
from trial_salvage.module3 import score_targets
from trial_salvage.module3.germline import stratification_scores, stratification_scores_v1


def g(symbol, loeuf, k, exp_syn, obs_syn=None, exp_mis=None):
    return {"symbol": symbol, "LOEUF": loeuf, "n_common_func": k, "exp_syn": exp_syn,
            "obs_syn": exp_syn if obs_syn is None else obs_syn, "exp_mis": exp_mis or 2.5 * exp_syn}


def by_symbol(rows):
    return {r["symbol"]: r for r in rows}


def test_v1_removes_gene_length_advantage():
    # 'giant' has 5x the common functional variants of 'dense' but 20x the expected synonymous count
    rows = [g("giant", 1.0, 50, 4000), g("dense", 1.0, 10, 200)]
    assert by_symbol(stratification_scores(rows))["giant"]["score"] > by_symbol(stratification_scores(rows))[
        "dense"]["score"]
    v1 = by_symbol(stratification_scores_v1(rows))
    assert v1["dense"]["rank_v1"] == 1 and v1["giant"]["rank_v1"] == 2
    assert v1["dense"]["rate_syn"] == pytest.approx(0.05)
    assert v1["dense"]["burden_v1"] == pytest.approx(1.0)
    assert v1["giant"]["rate_mis"] == pytest.approx(50 / 10000)


def test_v1_keeps_tolerance_term():
    rows = [g("tolerant", 1.6, 10, 200), g("constrained", 0.2, 10, 200), g("empty", 1.6, 0, 200)]
    sc = {s: r["score_v1"] for s, r in by_symbol(stratification_scores_v1(rows)).items()}
    assert sc["tolerant"] > sc["constrained"] > sc["empty"] == 0


def test_v1_syn_excess_gate_demotes_but_keeps_score():
    rows = [g("repeat", 1.2, 80, 1000, obs_syn=1600), g("clean", 1.0, 5, 200), g("clean_low", 1.0, 1, 200)]
    v1 = by_symbol(stratification_scores_v1(rows))
    assert v1["repeat"]["qc_syn_excess"] is True and v1["clean"]["qc_syn_excess"] is False
    assert v1["repeat"]["score_v1"] > v1["clean"]["score_v1"]
    assert [v1[s]["rank_v1"] for s in ("clean", "clean_low", "repeat")] == [1, 2, 3]
    ungated = by_symbol(stratification_scores_v1(rows, syn_excess=10.0))
    assert ungated["repeat"]["rank_v1"] == 1


def test_v1_missing_values_ranked_last_and_ranks_independent_of_set():
    rows = [g("a", 1.0, 4, 100), g("b", 1.5, 2, 100), {"symbol": "nolouef", "LOEUF": None, "n_common_func": 3,
                                                     "exp_syn": 100}, g("nan", float("nan"), 2, 100),
            {"symbol": "noobs", "LOEUF": 1.0, "n_common_func": 1, "exp_syn": 100}]
    v1 = by_symbol(stratification_scores_v1(rows))
    assert v1["nolouef"]["score_v1"] is None and v1["nan"]["score_v1"] is None
    assert {v1["nolouef"]["rank_v1"], v1["nan"]["rank_v1"]} == {4, 5}
    assert v1["noobs"]["qc_syn_excess"] is None and v1["noobs"]["score_v1"] is not None
    order = [r["symbol"] for r in sorted(v1.values(), key=lambda r: r["rank_v1"])][:3]
    bigger = by_symbol(stratification_scores_v1(rows + [g("z", 1.0, 40, 100)]))
    assert [s for s in sorted(bigger, key=lambda s: bigger[s]["rank_v1"]) if s in order] == order


def test_constraint_query_requests_missense_and_synonymous_counts():
    q = gnomad.constraint_query(["CYP2D6"])
    for f in ("obs_mis", "exp_mis", "obs_syn", "exp_syn", "oe_lof_upper", "exp_lof"):
        assert f in q
    assert gnomad.CONSTRAINT_KEYS["oe_lof_upper"] == "LOEUF"


def test_gene_constraint_reads_cache_without_network(tmp_path, monkeypatch):
    fake = {"data": {"g0": {"gene_id": "ENSG1", "symbol": "X", "gnomad_constraint": {
        "oe_lof_upper": 1.1, "oe_lof": 0.9, "pLI": 0.0, "mis_z": 0.1, "obs_lof": 9, "exp_lof": 10,
        "obs_mis": 90, "exp_mis": 100, "obs_syn": 40, "exp_syn": 42}}, "g1": None}}
    calls = []
    monkeypatch.setattr(gnomad, "_post", lambda payload: calls.append(payload) or fake)
    monkeypatch.setattr(gnomad.time, "sleep", lambda s: None)
    first = gnomad.gene_constraint(["X", "MISSING"], cache_dir=tmp_path)
    monkeypatch.setattr(gnomad, "_post", lambda payload: pytest.fail("cache miss hit the network"))
    second = gnomad.gene_constraint(["X", "MISSING"], cache_dir=tmp_path)
    assert first == second and len(calls) == 1
    assert first[0]["LOEUF"] == 1.1 and first[0]["exp_syn"] == 42 and first[0]["obs_mis"] == 90
    assert first[1]["symbol"] == "MISSING" and first[1]["LOEUF"] is None


def test_cli_round_trip_passes_columns_through(tmp_path):
    raw = pd.DataFrame([{**g("A", 1.0, 2, 100), "trials": "DRUG1 (NCT1)"},
                        {**g("B", 1.2, 8, 200), "trials": "DRUG2 (NCT2)"},
                        {"symbol": "C", "LOEUF": None, "exp_mis": None, "exp_syn": None, "n_common_func": None,
                         "trials": "DRUG3 (NCT3)", "score_v1": 99}])
    src, dst = tmp_path / "raw.csv", tmp_path / "scored.csv"
    raw.to_csv(src, index=False)
    assert score_targets.main(["--in", str(src), "--out", str(dst)]) == 0
    out = pd.read_csv(dst)
    assert out.symbol.tolist() == ["B", "A", "C"] and out.rank_v1.tolist() == [1, 2, 3]
    assert out.trials.tolist() == ["DRUG2 (NCT2)", "DRUG1 (NCT1)", "DRUG3 (NCT3)"]
    assert pd.isna(out.score_v1.iloc[2])
    assert set(score_targets.ADDED) <= set(out.columns)


def test_cli_rejects_missing_required_column(tmp_path):
    src = tmp_path / "raw.csv"
    pd.DataFrame([{"symbol": "A", "LOEUF": 1.0, "n_common_func": 2}]).to_csv(src, index=False)
    with pytest.raises(SystemExit):
        score_targets.main(["--in", str(src), "--out", str(tmp_path / "o.csv")])
