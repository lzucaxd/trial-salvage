import importlib.util
from pathlib import Path

import pandas as pd
import pytest

_spec = importlib.util.spec_from_file_location(
    "fetch_second_drug_targets", Path(__file__).parent.parent / "scripts" / "fetch_second_drug_targets.py")
fsd = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(fsd)


def test_targets_to_add_is_set_difference():
    pairs = pd.DataFrame({"nct": ["N1", "N2"], "drug": ["A", "B"], "targets": ["X;Y", " Z ; X"]})
    scored = pd.DataFrame({"symbol": ["X"]})
    assert fsd.targets_to_add(pairs, scored) == ["Y", "Z"]
    assert fsd.trials_by_target(pairs)["X"] == ["A (N1)", "B (N2)"]


def test_constraint_query_caps_aliases():
    q = fsd.constraint_query(["A", "B"])
    assert "g1: gene(gene_symbol: \"B\"" in q and "obs_syn" in q
    with pytest.raises(ValueError):
        fsd.constraint_query([str(i) for i in range(21)])


def test_build_row_keeps_unknown_genes():
    r = fsd.build_row("NOPE", None, None, None, ["D (N1)"])
    assert r["status"] == "not_in_gnomad" and r["LOEUF"] is None and r["n_trials"] == 1
    assert list(r) == fsd.COLUMNS


def test_build_row_flags_missing_loeuf():
    gene = {"gene_id": "ENSG1", "gnomad_constraint": {"oe_lof_upper": None, "mis_z": 1.2, "obs_mis": 5}}
    r = fsd.build_row("S", gene, [{"consequence": "missense_variant", "joint": {"ac": 200, "an": 1000}}], None, [])
    assert r["status"] == "no_lof_constraint" and r["n_common_func"] == 1 and r["mis_z"] == 1.2
