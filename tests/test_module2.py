"""Offline tests for module 2. No network, no GPU, no torch."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from trial_salvage.module2 import evaluate, run
from trial_salvage.module2.stats import auroc, spearman
from trial_salvage.module2.tiling import ESM1V_WINDOW, make_tiles

DATA = Path("data/module2")
GENES = ["egfr", "sod1", "apoe", "brca1", "brca2", "parp1"]


# ---------------------------------------------------------------- tiling

@pytest.mark.parametrize("length,expected_tiles", [(154, 1), (317, 1), (1014, 1), (1210, 2),
                                                   (1863, 3), (3418, 5)])
def test_tile_count_matches_protein_length(length, expected_tiles):
    tiles, assignment = make_tiles(length)
    assert len(tiles) == expected_tiles
    assert len(assignment) == length


@pytest.mark.parametrize("length", [154, 1022, 1023, 1210, 1863, 3418, 5000])
def test_tiling_covers_every_position_without_gaps(length):
    tiles, assignment = make_tiles(length)
    covered = set()
    for start, end in tiles:
        assert end - start + 1 <= ESM1V_WINDOW
        covered |= set(range(start, end + 1))
    assert covered == set(range(1, length + 1))
    for pos, ti in assignment.items():
        start, end = tiles[ti]
        assert start <= pos <= end


def test_position_is_assigned_to_its_most_interior_tile():
    length = 3418
    tiles, assignment = make_tiles(length)
    for pos, ti in assignment.items():
        chosen = min(pos - tiles[ti][0], tiles[ti][1] - pos)
        for start, end in tiles:
            if start <= pos <= end:
                assert chosen >= min(pos - start, end - pos)


# ---------------------------------------------------------------- statistics

def test_auroc_orientation_lower_score_is_positive():
    # positives score lower than negatives => AUROC above 0.5
    score = pd.Series([-9.0, -8.0, -7.0, -6.5, -6.0, 0.0, 0.5, 1.0, 1.5, 2.0])
    positive = pd.Series([True] * 5 + [False] * 5)
    out = auroc(score, positive, ~positive)
    assert out["auroc"] == pytest.approx(1.0)
    assert auroc(score, ~positive, positive)["auroc"] == pytest.approx(0.0)


def test_auroc_ties_give_one_half():
    score = pd.Series([1.0] * 10)
    positive = pd.Series([True] * 5 + [False] * 5)
    assert auroc(score, positive, ~positive)["auroc"] == pytest.approx(0.5)


def test_auroc_returns_none_when_a_class_is_too_small():
    score = pd.Series(range(10), dtype=float)
    positive = pd.Series([True] + [False] * 9)
    out = auroc(score, positive, ~positive)
    assert out["auroc"] is None and out["n_positive"] == 1


def test_spearman_is_one_for_a_monotone_pair():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)


# ---------------------------------------------------------------- committed tables

@pytest.mark.parametrize("gene", GENES)
def test_committed_tables_are_present_and_consistent(gene):
    scores = pd.read_csv(DATA / f"{gene}_annotated_scores.csv.gz")
    positions = pd.read_csv(DATA / f"{gene}_position_constraint.csv.gz")
    assert len(scores) > 0 and len(positions) > 0
    assert {"variant_id", "esm1v_ensemble", "clinvar_class", "position_mean"} <= set(scores.columns)
    # every annotated variant sits at a scored position
    assert set(scores.position_uniprot) <= set(positions.position_uniprot)
    # wild type is never scored against itself
    assert (scores.wt_aa != scores.mut_aa).all()
    assert scores.clinvar_class.isin(["pathogenic", "benign", "drug_response", "vus"]).all()


def test_clinvar_classification_precedence():
    assert evaluate.classify_clinvar(["Pathogenic", "Benign"]) == "pathogenic"
    assert evaluate.classify_clinvar(["Drug response"]) == "drug_response"
    # a drug-response call never outranks a pathogenicity call
    assert evaluate.classify_clinvar(["Drug response", "Pathogenic"]) == "pathogenic"
    assert evaluate.classify_clinvar(["Likely benign"]) == "benign"
    assert evaluate.classify_clinvar(["Variant of uncertain significance"]) == "vus"
    assert evaluate.classify_clinvar([]) == "unannotated"
    assert evaluate.classify_clinvar(None) == "unannotated"


# ---------------------------------------------------------------- the applicability gate

def test_verdict_is_do_not_rank_when_a_classical_predictor_wins():
    """BRCA1: SIFT beat ESM on the matched subset, so the gate must refuse to rank."""
    scores = pd.read_csv(DATA / "brca1_annotated_scores.csv.gz")
    validation = evaluate.validate(scores)
    matched = validation["matched_subset"]
    assert matched["sift"]["auroc"] > matched["esm1v"]["auroc"]
    assert evaluate.verdict(validation)["verdict"] == "do_not_rank"


def test_verdict_is_do_not_rank_for_brca2_below_chance():
    scores = pd.read_csv(DATA / "brca2_annotated_scores.csv.gz")
    validation = evaluate.validate(scores)
    assert validation["esm1v"]["auroc"] < 0.5
    assert evaluate.verdict(validation)["verdict"] == "do_not_rank"


def test_verdict_is_not_validated_when_benign_class_is_too_small():
    """SOD1 has 2 benign-classified substitutions, so discrimination is not measurable."""
    scores = pd.read_csv(DATA / "sod1_annotated_scores.csv.gz")
    validation = evaluate.validate(scores)
    assert validation["esm1v"]["auroc"] is None
    assert evaluate.verdict(validation)["verdict"] == "not_validated"


def test_verdict_is_rank_residues_only_for_egfr():
    scores = pd.read_csv(DATA / "egfr_annotated_scores.csv.gz")
    validation = evaluate.validate(scores)
    assert validation["esm1v"]["auroc"] > 0.60
    assert evaluate.verdict(validation)["verdict"] == "rank_residues_only"


def test_constraint_spread_uses_the_full_protein_not_the_annotated_subset():
    """SOD1 gives 3.22 from annotated positions alone and 3.70 across the whole protein."""
    scores = pd.read_csv(DATA / "sod1_annotated_scores.csv.gz")
    positions = pd.read_csv(DATA / "sod1_position_constraint.csv.gz")
    subset_only = evaluate.validate(scores)["reliability_diagnostic"]
    full = evaluate.validate(scores, position_constraint=positions)["reliability_diagnostic"]
    assert full["position_constraint_spread_sd"] != subset_only["position_constraint_spread_sd"]
    assert full["position_constraint_spread_sd"] == pytest.approx(3.70, abs=0.05)
    assert "scanned positions" in full["basis"]


def test_verdict_string_does_not_conflate_overall_and_matched_auroc():
    """EGFR overall is 0.808 on 108/519; the matched subset is 0.802 on 93/505. A verdict that
    quotes one and compares it to the other reads as like-for-like when it is not."""
    scores = pd.read_csv(DATA / "egfr_annotated_scores.csv.gz")
    validation = evaluate.validate(scores)
    overall = validation["esm1v"]["auroc"]
    matched = validation["matched_subset"]["esm1v"]["auroc"]
    assert round(overall, 3) != round(matched, 3), "test is vacuous if the two agree"
    reason = evaluate.verdict(validation)["reason"]
    assert f"{overall:.3f} overall" in reason
    assert f"{matched:.3f} vs" in reason


def test_every_verdict_is_a_declared_enum_value():
    for gene in GENES:
        scores = pd.read_csv(DATA / f"{gene}_annotated_scores.csv.gz")
        assert evaluate.verdict(evaluate.validate(scores))["verdict"] in evaluate.VERDICTS


def test_substitution_residual_is_at_or_below_chance_everywhere():
    """The module's central caveat, asserted rather than only documented."""
    for gene in ("egfr", "brca1", "brca2"):
        scores = pd.read_csv(DATA / f"{gene}_annotated_scores.csv.gz")
        residual = evaluate.validate(scores)["positional_decomposition"]["residual"]["auroc"]
        assert residual is not None and residual <= 0.5, f"{gene} residual AUROC {residual}"


# ---------------------------------------------------------------- output document

def test_build_output_validates_against_the_schema():
    schema = json.loads(Path("schemas/module2_output.schema.json").read_text())
    jsonschema = pytest.importorskip("jsonschema")
    case = {"case_id": "CASE-BRCA2-OLA-OV-005", "selection_gene": "BRCA2", "selection_uniprot": "P51587",
                "drug_id": "olaparib", "drug_chembl_id": "CHEMBL521686", "drug_modality": "small molecule",
                "target_id": "PARP1", "target_uniprot": "P09874",
                "selection_target_relationship": "synthetic_lethality", "indication": "Ovarian cancer"}
    scores, positions = run.load_offline("BRCA2")
    out = run.build_output(case, scores, positions)
    jsonschema.validate(out, schema)
    assert out["target_id"] == "PARP1" and out["selection_gene_id"] == "BRCA2"
    assert out["applicability"]["verdict"] == "do_not_rank"
    assert out["limitations"]


def test_output_keeps_drug_target_and_selection_gene_separate():
    """The generalization that made olaparib expressible must not collapse the two ids."""
    case = {"case_id": "x", "selection_gene": "BRCA1", "selection_uniprot": "P38398", "drug_id": "olaparib",
                "drug_chembl_id": "CHEMBL521686", "drug_modality": "small molecule", "target_id": "PARP1",
                "target_uniprot": "P09874", "selection_target_relationship": "synthetic_lethality",
                "indication": None}
    scores, positions = run.load_offline("BRCA1")
    out = run.build_output(case, scores, positions)
    assert out["selection_gene_id"] != out["target_id"]
    assert out["handoff"]["join_keys"].count("selection_gene_id") == 1


def test_missing_gene_gives_an_actionable_error():
    with pytest.raises(SystemExit, match="score_module2_case"):
        run.load_offline("NOTAGENE")
