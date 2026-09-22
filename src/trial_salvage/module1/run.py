"""Module 1 pipeline: fetch -> curate/check -> diagnose -> figure -> report -> schema-validated JSON.

Usage:
    python -m trial_salvage.module1.run --config config/assets/gefitinib.yaml --outdir outputs/module1 [--offline]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

import pandas as pd
from jsonschema import validate

from .. import ctgov, pubmed
from ..config import load_asset_config
from .effects import load_effects, provenance_check
from .eligibility import biomarker_selection
from .failure_analysis import diagnose, salvage_strategy_map
from .figures import forest_and_timeline
from .report import render

FAMILY_FIELDS = ["NCTId", "BriefTitle", "OfficialTitle", "OverallStatus", "WhyStopped", "StartDate", "CompletionDate",
                 "ResultsFirstPostDate", "Phase", "DesignAllocation", "DesignMasking", "EnrollmentCount", "EnrollmentType",
                 "Condition", "InterventionName", "LeadSponsorName", "LeadSponsorClass", "PrimaryOutcomeMeasure",
                 "EligibilityCriteria", "LocationCountry", "ReferencePMID", "HasResults"]


def fetch_all(cfg: dict, raw: Path, offline: bool) -> tuple[dict, list, dict]:
    raw.mkdir(parents=True, exist_ok=True)
    f_anchor, f_family, f_abs = raw / "anchor_trials.json", raw / "trial_family.json", raw / "abstracts.json"
    if offline:
        return (json.loads(f_anchor.read_text()), json.loads(f_family.read_text()), json.loads(f_abs.read_text()))
    anchors = {k: ctgov.get_study(v["nct"]) for k, v in cfg["trials"].items()}
    family = ctgov.search_studies(query_intr=cfg["trial_family_query"], filter_advanced="AREA[StudyType]INTERVENTIONAL",
                                  fields=FAMILY_FIELDS)
    abstracts = pubmed.efetch_abstracts(list(cfg["literature"].values()))
    f_anchor.write_text(json.dumps(anchors)); f_family.write_text(json.dumps(family)); f_abs.write_text(json.dumps(abstracts, indent=1))
    return anchors, family, abstracts


def trial_block(study: dict, tcfg: dict) -> dict:
    row = ctgov.flatten_study(study)
    posted = ctgov.posted_outcomes(study)
    prim = [p for p in posted if p.get("type") == "PRIMARY"]
    has_hr = any((p.get("unit") == "analysis") and str(p.get("arm", "")).lower().startswith("hazard") for p in posted)
    note = ""
    if not row["has_results"]:
        note = "No results posted on ClinicalTrials.gov; outcome data exist only in the literature."
    elif not has_hr:
        note = "Results posted, but no hazard ratio analysis in the posting; subgroup effect sizes exist only in the literature."
    return {**row, "label": tcfg["label"], "primary_endpoint": tcfg["primary_endpoint"], "line_of_therapy": tcfg.get("line_of_therapy"),
            "results_posted": row["has_results"], "n_posted_primary_rows": len(prim), "posted_outcomes": posted, "posting_note": note}


def family_frame(family: list, cfg: dict) -> pd.DataFrame:
    rows = [ctgov.flatten_study(s) for s in family]
    df = pd.DataFrame(rows)
    gene = cfg["biomarker"]["gene"]
    flags = df.eligibility.apply(lambda t: biomarker_selection(t, gene))
    df["biomarker_mentioned"] = flags.apply(lambda d: d["mentioned"])
    df["biomarker_required"] = flags.apply(lambda d: d["required"])
    df["biomarker_wt_or_negative"] = flags.apply(lambda d: d["wt_or_negative"])
    df["start_year"] = pd.to_numeric(df.start.str.slice(0, 4), errors="coerce")
    kw = "|".join([cfg["disease"]["name"].split()[0].lower(), "lung", "nsclc"])
    df["in_indication"] = df.conditions.str.lower().str.contains(kw, regex=True, na=False)
    return df


def family_summary(df: pd.DataFrame) -> dict:
    ind = df[df.in_indication]
    bins = [1999, 2004, 2008, 2012, 2016, 2020, 2030]
    labels = ["2000-04", "2005-08", "2009-12", "2013-16", "2017-20", "2021+"]
    ind = ind.assign(period=pd.cut(ind.start_year, bins, labels=labels))
    per = ind.groupby("period", observed=True).agg(trials=("nct", "size"), required=("biomarker_required", "sum")).reset_index()
    return {"n_trials": len(df), "n_in_indication": len(ind),
            "n_phase3_in_indication": int(ind.phase.str.contains("PHASE3").sum()),
            "n_with_results": int(ind.has_results.sum()),
            "n_biomarker_required": int(ind.biomarker_required.sum()),
            "selection_by_period": [{"period": str(r.period), "trials": int(r.trials), "required": int(r.required)} for r in per.itertuples()]}


def _year(s: str | None) -> float | None:
    try:
        y, m = s.split("-")[:2]
        return int(y) + (int(m) - 0.5) / 12
    except (AttributeError, ValueError):
        return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    ap.add_argument("--outdir", default="outputs/module1")
    ap.add_argument("--offline", action="store_true", help="reuse data/raw/<asset>/ instead of hitting the APIs")
    a = ap.parse_args(argv)

    cfg = load_asset_config(a.config)
    root = Path(cfg["_root"]); out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    raw = root / "data" / "raw" / cfg["asset"]["name"]
    anchors, family, abstracts = fetch_all(cfg, raw, a.offline)

    failed = trial_block(anchors["failed"], cfg["trials"]["failed"])
    rescue = trial_block(anchors["rescue"], cfg["trials"]["rescue"])
    effects = provenance_check(load_effects(cfg["curated"]["effects"]), abstracts)
    reg = pd.read_csv(cfg["curated"]["regulatory"])
    fam = family_frame(family, cfg)
    diag = diagnose(effects, cfg)
    strategies = salvage_strategy_map(cfg, diag)

    rescue_pub_year = None
    for k, p in cfg["literature"].items():
        if k.startswith(cfg["trials"]["rescue"]["label"]) and "primary" in k:
            rescue_pub_year = abstracts.get(p, {}).get("year")
    cfg["_dates"] = {"failed_start": _year(failed["start"]), "rescue_start": _year(rescue["start"]),
                     "rescue_published": float(rescue_pub_year) + 0.5 if rescue_pub_year else None}

    pos = effects[(effects.trial == rescue["label"]) & effects.population.str.contains("mutation-positive") & (effects.endpoint == rescue["primary_endpoint"])]
    neg = effects[(effects.trial == rescue["label"]) & effects.population.str.contains("mutation-negative") & (effects.endpoint == rescue["primary_endpoint"])]
    itt = effects[(effects.trial == rescue["label"]) & effects.population.str.startswith("ITT") & (effects.endpoint == rescue["primary_endpoint"])]
    bm = cfg["biomarker"]
    result = {
        "schema_version": "1.0",
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "asset": cfg["asset"], "target": cfg["target"], "disease": cfg["disease"],
        "trials": {"failed": {k: v for k, v in failed.items() if k != "posted_outcomes"},
                   "rescue": {k: v for k, v in rescue.items() if k != "posted_outcomes"}},
        "effects": json.loads(effects.to_json(orient="records")),
        "failure_diagnosis": diag,
        "salvage_strategies": strategies,
        "trial_family_summary": family_summary(fam),
        "regulatory_timeline": reg.to_dict(orient="records"),
        "literature": {k: {"pmid": v, **{kk: vv for kk, vv in abstracts.get(v, {}).items() if kk != "abstract"}} for k, v in cfg["literature"].items()},
        "handoff": {
            "module2": {"uniprot": cfg["target"]["uniprot"], "gene": bm["gene"], "sensitising_variants": bm["sensitising_variants"],
                        "primary_resistance_variants": bm["primary_resistance_variants"], "acquired_resistance_variants": bm["acquired_resistance_variants"]},
            "module3": {"gene": bm["gene"], "disease_efo": cfg["disease"]["efo"], "histology": cfg["disease"].get("histology_of_interest"),
                        "clinical_proxy_subgroups": [e["detail"] for e in diag["evidence"] if e["rule"] == "prespecified_subgroup_benefit"]},
            "module4": {"endpoint": rescue["primary_endpoint"],
                        "hr_pos": float(pos.hr.iloc[0]) if len(pos) else None, "hr_neg": float(neg.hr.iloc[0]) if len(neg) else None,
                        "itt_reference_hr": float(itt.hr.iloc[0]) if len(itt) else None,
                        "failed_trial_itt_hr": float(effects[(effects.trial == failed["label"]) & (effects.analysis_type == "prespecified primary")].hr.iloc[0]),
                        "responder_fraction_sweep": [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8],
                        "failed_trial_n": failed["enrollment"], "rescue_trial_n": rescue["enrollment"]},
        },
    }
    schema = json.loads((root / "schemas" / "module1_output.schema.json").read_text())
    validate(result, schema)

    fig = out / f"fig_{cfg['asset']['name']}_module1.png"
    forest_and_timeline(effects, fam, cfg, str(fig))
    (out / "module1_output.json").write_text(json.dumps(result, indent=1, default=str))
    effects.to_csv(out / "effect_estimates_checked.csv", index=False)
    fam.drop(columns=["eligibility"]).to_csv(out / "trial_family.csv", index=False)
    pd.DataFrame(failed["posted_outcomes"] + rescue["posted_outcomes"]).to_csv(out / "posted_outcomes.csv", index=False)
    (out / "module1_report.md").write_text(render(result, effects, reg, fig.name))
    print(json.dumps({"failure_mode": diag["failure_mode"], "confidence": diag["confidence"],
                      "effects_checked": int(effects.hr_in_abstract.sum()), "effects_total": len(effects),
                      "family_trials": len(fam), "outdir": str(out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
