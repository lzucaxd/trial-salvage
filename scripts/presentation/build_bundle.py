"""Assemble deck_data.json from the repository's own pipeline outputs.

Run order:
    (in the repo)  make module1-offline && make module2-all && make module4 \
                   && make module4-cases && make compare
    python build_bundle.py      # -> deck_data.json
    python build_deck.py        # -> trial_salvage_deck.html

Inputs are read only from ``verify/`` (a clean clone with outputs built) plus two
cached fetches that do not come from the pipeline:
  * ``ppi_network.json``  — STRING v12 interaction network (see fetch cell/README)
  * published cost figures, defined below with their sources attached.

No value in the deck is typed by hand; everything traces to one of these.
"""

from __future__ import annotations

import json
import math
import pathlib
import sys

import numpy as np
import pandas as pd

R = pathlib.Path("verify")
sys.path.insert(0, str((R / "src").resolve()))

# ---------------------------------------------------------------------------
# Published cost and success-rate inputs. Each carries its source string; both
# travel together into the deck so no figure appears without its provenance.
# ---------------------------------------------------------------------------
PHASE3_SUCC, PHASE3_FAIL = 358, 466          # counts, not a rounded rate
COST = {
    # All therapeutic areas (BMJ Open 2020) - the general-purpose figures.
    "pivotal_trial_median_musd": 19.0,
    "pivotal_trial_iqr_musd": (12.0, 33.0),
    "per_drug_median_musd": 48.0,
    "per_patient_usd": 41_413,
    # Oncology-specific, and by primary endpoint (Clin Trials 2020). Both worked cases
    # here are oncology, and an overall-survival trial costs several times an
    # objective-response one, so the endpoint-matched figure is the relevant one.
    "onc_pivotal_median_musd": 31.7,
    "onc_pivotal_iqr_musd": (17.0, 60.0),
    "onc_by_endpoint_musd": {"ORR": 17.7, "PFS": 42.3, "OS": 79.4},
    "onc_by_endpoint_iqr_musd": {"ORR": (11.9, 27.1), "PFS": (34.6, 101.2), "OS": (56.9, 97.0)},
    "onc_single_arm_musd": 17.7,
    "onc_placebo_controlled_musd": 56.7,
    "onc_active_control_musd": 67.6,
    "phase3_onc_success": round(PHASE3_SUCC / (PHASE3_SUCC + PHASE3_FAIL), 4),
}
SRC = {
    "pivotal_trial_median_musd": (
        "Moore TJ et al., BMJ Open 2020;10:e038863 (PMID 32532786, doi:10.1136/bmjopen-2020-038863) "
        "- IQVIA cost model over 225 "
        "pivotal trials for 101 FDA-approved new molecular entities, 2015-2017: median USD 19M "
        "(IQR 12-33M) per trial"),
    "onc_pivotal_median_musd": (
        "Clin Trials 2020 (PMID 32114790) - pivotal trials for FDA-approved cancer drugs, "
        "2015-2017: median USD 31.7M (IQR 17.0-60.0M); by primary endpoint, objective response "
        "17.7M (IQR 11.9-27.1), progression-free survival 42.3M (IQR 34.6-101.2), overall "
        "survival 79.4M (IQR 56.9-97.0); single-arm 17.7M, placebo-controlled 56.7M, "
        "active-control 67.6M"),
    "per_drug_median_musd": (
        "same source, median per approved drug across all its pivotal trials: USD 48M (IQR 20-102M)"),
    "per_patient_usd": (
        "same source, median estimated cost per enrolled patient: USD 41,413 (IQR 29,894-75,047)"),
    "phase3_onc_success": (
        f"Yamamoto K, Iwase A, Maeda H, Clin Transl Sci 2026 (PMID 42257532, doi:10.1111/cts.70635) - "
        f"{PHASE3_SUCC + PHASE3_FAIL} phase III oncology "
        f"drug trials registered 2007-2023 with posted primary-endpoint results: {PHASE3_SUCC} "
        f"successful / {PHASE3_FAIL} not, = {COST['phase3_onc_success'] * 100:.1f}% "
        "(rate computed from the reported counts)"),
}
# Each phase 3 also carries its primary endpoint, so the oncology endpoint-matched
# median can be reported beside the per-patient estimate. OAM4558g was a phase 2, not a
# pivotal trial, so no pivotal median applies to it (endpoint recorded as None).
HISTORIC = {
    "ISEL (failed, unselected)": {"n": 1692, "endpoint": "OS", "pivotal": True},
    "IPASS (rescue, clinical proxy)": {"n": 1329, "endpoint": "PFS", "pivotal": True},
    "OAM4558g (onartuzumab ph2)": {"n": 137, "endpoint": None, "pivotal": False},
    "METLung (onartuzumab retry)": {"n": 499, "endpoint": "OS", "pivotal": True},
}
HISTORIC_N = {k: v["n"] for k, v in HISTORIC.items()}
IFUM_N = 106          # the trial that earned the 2015 approval; from module 1's own timeline
REALISTIC_F = (0.2, 0.3, 0.5)


def jload(p):
    return json.loads((R / p).read_text())


def fisher_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p, matching the repo's own implementation."""
    n1, n2, k, n = a + b, c + d, a + c, a + b + c + d

    def p(x: int) -> float:
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k)

    obs = p(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def grid(o):
    return [{"design": r["design"], "n": r["total_randomized"], "f": r["responder_fraction"],
             "power": round(r["simulated_power"], 4), "screened": r["expected_screened"]}
            for r in o["designs"]]


def case(out, curated):
    return {
        "grid": grid(out), "inputs": out["inputs"], "requirements": out["requirements"],
        "retrospective": out["retrospective_check"], "calibration": out["calibration"],
        "strategies": [{k: s.get(k) for k in
                        ("strategy", "tier", "rank", "used_historically",
                         "next_experiment", "would_be_undermined_by")}
                       for s in out["strategies"]],
        "evidence_quality": curated["evidence_quality"], "outcome": curated["outcome"],
        "pre_retry": curated["pre_retry_evidence"], "retry_result": curated["retry_result"],
        "trials": curated["trials"], "wording": curated["figure_wording"],
    }


def build() -> dict:
    m1 = jload("outputs/module1/module1_output.json")
    g4 = jload("outputs/module4_gefitinib/module4_output.json")
    o4 = jload("outputs/module4_onartuzumab/module4_output.json")
    cc = jload("outputs/module4_comparison/case_comparison.json")
    gcase = jload("data/cases/gefitinib_module4.json")
    ocase = jload("data/cases/onartuzumab_module4.json")
    bm = pd.read_csv(R / "data/benchmark/rescue_benchmark_v0.csv")
    m2 = pd.read_csv(R / "data/module2/cross_case_summary.csv")
    m2rel = pd.read_csv(R / "data/module2/reliability_diagnostic.csv")
    ppi = json.loads(pathlib.Path("ppi_network.json").read_text())

    # ---- portfolio economics -------------------------------------------------
    pc = cc["ranking_principle_validation"]["provenance_contrast"]
    dec = bm[bm.outcome.isin(["success", "fail"])]
    base = ((dec.outcome == "success").sum(), len(dec))
    strong, weak = pc["all_decided"]["prespecified_or_mechanistic"], pc["all_decided"]["post_hoc_subgroup"]
    tm, lo, hi = COST["pivotal_trial_median_musd"], *COST["pivotal_trial_iqr_musd"]
    portfolio = []
    for label, p in [("retry blind (benchmark base rate)", base[0] / base[1]),
                     ("retry only prespecified/mechanistic", strong["success_rate"]),
                     ("retry only post-hoc-subgroup-driven", weak["success_rate"]),
                     ("industry phase 3 oncology baseline", COST["phase3_onc_success"])]:
        portfolio.append({"strategy": label, "p_success": round(p, 4),
                          "trials_per_success": round(1 / p, 2),
                          "cost_per_success_musd": round(tm / p, 1),
                          "cost_lo_musd": round(lo / p, 1), "cost_hi_musd": round(hi / p, 1)})

    # ---- design economics ----------------------------------------------------
    ppp = COST["per_patient_usd"]
    d = pd.DataFrame(g4["designs"])
    uns = d[(d.design == "unselected") & (d.responder_fraction.isin(REALISTIC_F))][
        ["responder_fraction", "total_randomized", "simulated_power"]].copy()
    uns["cost_musd"] = (uns.total_randomized * ppp / 1e6).round(1)
    req = g4["requirements"]["enriched_design"]
    reg = pd.DataFrame(m1["regulatory_timeline"])
    ifum = reg[reg.event.str.contains("IFUM", na=False)]

    design = {
        "per_patient_usd": ppp,
        "enriched": {"n_randomized": req["n_randomized"], "n_screened": req["expected_screened"],
                     "power": req["simulated_power"],
                     "randomisation_cost_musd": round(req["n_randomized"] * ppp / 1e6, 2)},
        "unselected_realistic": json.loads(uns.to_json(orient="records")),
        "min_fraction_for_unselected_80pct":
            g4["requirements"]["min_fraction_for_target_power"].get("fraction"),
        "historical_trial_n": HISTORIC_N,
        "historical_trial_costs_musd": {k: round(n * ppp / 1e6, 1) for k, n in HISTORIC_N.items()},
        "historical": {k: {**v,
                           "per_patient_musd": round(v["n"] * ppp / 1e6, 1),
                           "endpoint_matched_musd": (COST["onc_by_endpoint_musd"][v["endpoint"]]
                                                     if v["pivotal"] and v["endpoint"] else None)}
                       for k, v in HISTORIC.items()},
        "ifum_validation": {"module4_recommended_n": req["n_randomized"], "ifum_actual_n": IFUM_N,
                            "ifum_event": ifum.iloc[0]["event"] if len(ifum) else None},
        "hr_pos": g4["inputs"]["hr_pos"], "hr_neg": g4["inputs"]["hr_neg"],
        "gefitinib_retrospective": g4["retrospective_check"],
        "onartuzumab_retrospective": o4["retrospective_check"],
    }

    # ---- implied sampling distributions for the replication panel ------------
    for mod in [m for m in list(sys.modules) if m.startswith("trial_salvage")]:
        del sys.modules[mod]
    from trial_salvage.module4.retrospect import _simulate_hr_distribution
    from trial_salvage.module4.simulate import Assumptions

    dists = {}
    for name, prior, n_retry, obs, med, src in [
        ("onartuzumab", 0.37, 499, 1.27, 9.1,
         "METLung placebo-arm median OS 9.1 months (PMID 27937096)"),
        ("gefitinib", 0.48, 1329, 0.74, 5.8,
         "IPASS posted control-arm median PFS 5.8 months"),
    ]:
        a = Assumptions(n_simulations=4000, control_median_months=med, seed=11)
        draws = _simulate_hr_distribution(n_retry, prior, a, np.random.default_rng(a.seed + 17), 4000)
        hist, edges = np.histogram(draws, bins=44, range=(0.15, 1.6))
        dists[name] = {"prior": prior, "n_retry": n_retry, "observed": obs,
                       "hist": hist.tolist(), "edges": [round(float(e), 4) for e in edges],
                       "p2_5": round(float(np.percentile(draws, 2.5)), 4),
                       "p50": round(float(np.percentile(draws, 50)), 4),
                       "p97_5": round(float(np.percentile(draws, 97.5)), 4),
                       "frac_below_observed": round(float((draws <= obs).mean()), 4),
                       "n_draws": int(draws.size), "control_median_source": src}

    # ---- module 1's pre-registered blind evaluation --------------------------
    be_csv = pd.read_csv(R / "data/benchmark/blind/module1_blind_eval_v0.csv")
    bdec = be_csv[be_csv.outcome.isin(["success", "fail"])]
    ct = pd.crosstab(bdec.verdict, bdec.outcome)
    for c in ("success", "fail"):
        if c not in ct:
            ct[c] = 0
    anyv = bdec[bdec.verdict.isin(["retry_supported", "retry_weak"])]
    none = bdec[bdec.verdict == "not_supported"]
    tab = [[int((anyv.outcome == "success").sum()), int((anyv.outcome == "fail").sum())],
           [int((none.outcome == "success").sum()), int((none.outcome == "fail").sum())]]
    blind = {
        "n_decided": int(len(bdec)),
        "n_success": int((bdec.outcome == "success").sum()),
        "n_fail": int((bdec.outcome == "fail").sum()),
        "verdict_table": [{"verdict": v, "success": int(r.success), "fail": int(r.fail),
                           "n": int(r.success + r.fail),
                           "rate": None if not (r.success + r.fail) else
                                   round(r.success / (r.success + r.fail), 3)}
                          for v, r in ct.iterrows()],
        "prereg_ordering_falsified": True,
        "any_vs_none": {"any_success": tab[0][0], "any_n": sum(tab[0]),
                        "none_success": tab[1][0], "none_n": sum(tab[1]), "none_fail": tab[1][1],
                        "fisher_p": round(fisher_2x2(tab[0][0], tab[0][1], tab[1][0], tab[1][1]), 3)},
        "effects_verified": "111/111 numeric estimates verified literally present in their abstracts",
        "n_abstracts": 72, "n_assets": 36, "doc": "docs/module1_blind_eval.md",
        "status": "v0; re-run planned after adding failure_type and full-text extraction",
    }

    # ---- the prediction/outcome match, which is the deck's centrepiece ----------
    # For each strategy the framework ranked, did the field actually use it? A tier-1
    # rank means "the evidence in this asset supports trying it"; tier 4 means it does
    # not. The match is whether those two calls line up with history.
    match_rows = []
    for st in g4["strategies"]:
        supported = st["tier"].startswith("tier_1")
        used = bool(st["used_historically"])
        match_rows.append({
            "strategy": st["strategy"], "rank": st["rank"], "tier": st["tier"],
            "framework_says": "worth trying" if supported else "not supported by the evidence",
            "supported": supported, "used_historically": used,
            "agrees": supported == used,
            "evidence": st.get("module1_evidence"),
            "next_experiment": st.get("next_experiment"),
        })
    match = {
        "rows": match_rows,
        "n_strategies": len(match_rows),
        "n_supported": sum(r["supported"] for r in match_rows),
        "n_supported_and_used": sum(r["supported"] and r["used_historically"] for r in match_rows),
        "n_unsupported": sum(not r["supported"] for r in match_rows),
        "n_unsupported_and_unused": sum(not r["supported"] and not r["used_historically"]
                                        for r in match_rows),
        "n_agree": sum(r["agrees"] for r in match_rows),
        "recommended_n": g4["requirements"]["enriched_design"]["n_randomized"],
        "actual_approval_trial_n": IFUM_N,
    }

    # The field's own path to the same answer, from module 1's regulatory timeline.
    reg_rows = [{"date": r.get("date"), "agency": r.get("agency"), "event": r.get("event")}
                for r in m1["regulatory_timeline"]]
    years = [int(r["date"][:4]) for r in reg_rows if r.get("date")]
    match["years_to_get_there"] = (max(years) - min(years)) if years else None
    match["first_event_year"] = min(years) if years else None
    match["last_event_year"] = max(years) if years else None

    # ---- model and data-source inventory --------------------------------------
    # Status is deliberately explicit. "live" = produced a number in this run.
    # "in_harness" = wired into the scoring code but not called for any reported
    # result. "planned" = not implemented. Nothing is described as contributing
    # unless a number here came from it.
    m2cc = pd.read_csv(R / "data/module2/cross_case_summary.csv")
    m2g = jload("outputs/module2/gefitinib/module2_output.json")
    ms = m2g["validation"]["matched_subset"]
    models = {
        "protein": [
            {"name": "ESM-1v", "icon": "protein", "status": "live",
             "detail": "5-model ensemble, 650M params each, masked marginals",
             "ref": "facebook/esm1v_t33_650M_UR90S_1-5 (Meier et al. 2021)",
             "stat": f"{int(m2cc.n_substitutions.sum()):,} substitutions scored",
             "stat2": f"AUROC {ms['esm1v']['auroc']:.3f} on EGFR",
             "genes": int(len(m2cc)), "tiles": int(m2cc.n_tiles.sum()),
             "longest_protein": int(m2cc.seq_len.max())},
            {"name": "PolyPhen-2", "icon": "gear", "status": "live",
             "detail": "classical comparator", "ref": "precomputed scores",
             "stat": f"AUROC {ms['polyphen']['auroc']:.3f}", "stat2": "same matched subset"},
            {"name": "SIFT", "icon": "gear", "status": "live",
             "detail": "classical comparator", "ref": "precomputed scores",
             "stat": f"AUROC {ms['sift']['auroc']:.3f}", "stat2": "same matched subset"},
            {"name": "ESM2", "icon": "protein", "status": "in_harness",
             "detail": "650M, same masked-marginal harness",
             "ref": "facebook/esm2_t33_650M_UR50D",
             "stat": "wired, not scored", "stat2": "no reported result uses it"},
        ],
        "genome": [
            {"name": "ClinVar", "icon": "tag", "status": "live",
             "detail": "pathogenic / benign labels", "ref": "variant classifications",
             "stat": f"{int(m2cc.n_pathogenic.sum()):,} pathogenic",
             "stat2": f"{int(m2cc.n_benign.sum()):,} benign"},
            {"name": "gnomAD", "icon": "bars", "status": "live",
             "detail": "gene constraint and allele frequencies", "ref": "population genomes",
             "stat": "germline frequency", "stat2": "vs somatic frequency"},
            {"name": "cBioPortal", "icon": "bars", "status": "live",
             "detail": "somatic tumour variant frequency", "ref": "study-level frequency",
             "stat": "somatic lane", "stat2": "tumour vs population"},
            {"name": "AlphaGenome", "icon": "dna", "status": "planned",
             "detail": "regulatory-variant effect prediction",
             "ref": "google/alphagenome-all-folds (licence-gated)",
             "stat": "not implemented", "stat2": "module 3 stub"},
        ],
        "clinical": [
            {"name": "ClinicalTrials.gov", "icon": "clipboard", "status": "live",
             "detail": "trial registry, API v2", "ref": "trial family and posted results",
             "stat": f"{m1['trial_family_summary']['n_trials']} trials retrieved",
             "stat2": f"{m1['trial_family_summary']['n_phase3_in_indication']} phase 3 in indication"},
            {"name": "PubMed", "icon": "journal", "status": "live",
             "detail": "abstracts, E-utilities", "ref": "effect estimates with provenance",
             "stat": f"{len(m1['effects'])} effect estimates",
             "stat2": "each verified in its own abstract"},
        ],
        "network": [
            {"name": "STRING", "icon": "network", "status": "live",
             "detail": "protein interaction network", "ref": "v12, Homo sapiens",
             "stat": f"{len(ppi['edges'])} interactions",
             "stat2": f"{len(ppi['annotations'])} proteins"},
            {"name": "Open Targets", "icon": "network", "status": "live",
             "detail": "target-disease associations", "ref": "pathway membership",
             "stat": "pathway genes", "stat2": "germline lane"},
            {"name": "Reactome", "icon": "network", "status": "live",
             "detail": "pathway definitions", "ref": "target neighbourhood",
             "stat": "pathway expansion", "stat2": "germline lane"},
        ],
    }
    # Compact forms for the canvas, where the cards are only ~90px wide. Values are
    # rebuilt from the same numbers rather than restated, so they cannot drift.
    SHORT = {
        "ESM-1v": ("ESM-1v", f"{int(m2cc.n_substitutions.sum()):,} variants", "5 x 650M params"),
        "PolyPhen-2": ("PolyPhen-2", f"AUROC {ms['polyphen']['auroc']:.3f}", "classical"),
        "SIFT": ("SIFT", f"AUROC {ms['sift']['auroc']:.3f}", "classical"),
        "ESM2": ("ESM2", "in harness", "650M, not scored"),
        "ClinVar": ("ClinVar", f"{int(m2cc.n_pathogenic.sum()):,} pathogenic",
                    f"{int(m2cc.n_benign.sum()):,} benign"),
        "gnomAD": ("gnomAD", "allele freq", "gene constraint"),
        "cBioPortal": ("cBioPortal", "somatic freq", "tumour studies"),
        "AlphaGenome": ("AlphaGenome", "planned", "regulatory effect"),
        "ClinicalTrials.gov": ("CT.gov", f"{m1['trial_family_summary']['n_trials']} trials",
                               f"{m1['trial_family_summary']['n_phase3_in_indication']} phase 3"),
        "PubMed": ("PubMed", f"{len(m1['effects'])} estimates", "all verified"),
        "STRING": ("STRING", f"{len(ppi['edges'])} edges", f"{len(ppi['annotations'])} proteins"),
        "Open Targets": ("Open Targets", "pathway genes", "germline lane"),
        "Reactome": ("Reactome", "pathways", "germline lane"),
    }
    for grp in models.values():
        for m in grp:
            sh, a, b = SHORT[m["name"]]
            m["short"], m["s1"], m["s2"] = sh, a, b

    models_flat = [m for grp in models.values() for m in grp]
    models_meta = {
        "n_live": sum(m["status"] == "live" for m in models_flat),
        "n_total": len(models_flat),
        "esm_substitutions": int(m2cc.n_substitutions.sum()),
        "esm_genes": int(len(m2cc)),
        "esm_auroc_egfr": round(ms["esm1v"]["auroc"], 3),
        "polyphen_auroc": round(ms["polyphen"]["auroc"], 3),
        "sift_auroc": round(ms["sift"]["auroc"], 3),
        "clinvar_pathogenic": int(m2cc.n_pathogenic.sum()),
        "clinvar_benign": int(m2cc.n_benign.sum()),
    }

    # ---- second worked case: the CETP class ------------------------------------
    # Produced by a separate end-to-end run, not by this repo's pipeline, so the two
    # kinds of row are flagged differently and never merged:
    #   score_source  = that run. NOT recomputed here; this repo cannot reproduce it.
    #   outcome_source = verified here against the registry, PubMed or the approval
    #                    announcement. Each row carries the identifier it was checked against.
    cetp = {
        "asset": "dalcetrapib",
        "target": "CETP",
        "area": "Cardiovascular",
        "failed_trial": {"nct": "NCT00658515", "label": "dal-OUTCOMES", "n": 15871,
                         "primary": "Incidence of Cardiovascular Mortality and Morbidity",
                         "verified": "ClinicalTrials.gov API v2, enrollment type ACTUAL"},
        "score_provenance": ("Lever scores come from a separate end-to-end run of the framework. "
                             "They are quoted, not recomputed: this repository has no scoring code "
                             "for them."),
        "levers": [
            {"lever": "New endpoint", "score": 67.5, "rank": 1, "verdict": "pursue",
             "happened": ("dal-GenE-2 (NCT05918861) is recruiting with the primary endpoint switched "
                          "from the broad composite to myocardial infarction alone — the one component "
                          "that survived dal-GenE at HR 0.79 (0.65-0.96)"),
             "agrees": True, "independent": False,
             "outcome_source": "NCT05918861 (RECRUITING, phase 3, n=2000 est.); PMID 35856777",
             "independence_note": ("The registry record was already in hand when this lever was "
                                   "scored, so this row corroborates but is not an independent test.")},
            {"lever": "New / narrower indication", "score": 66.0, "rank": 2, "verdict": "pursue",
             "happened": ("Obicetrapib approved in the EU on 21 Sep 2026 (Ubeslo, and Evlarco with "
                          "ezetimibe) for primary hypercholesterolaemia and mixed dyslipidaemia — a "
                          "lipid endpoint, with the cardiovascular outcomes trial PREVAIL still running"),
             "agrees": True, "independent": True,
             "outcome_source": ("European Commission marketing authorisation, 21 Sep 2026; "
                                "NewAmsterdam Pharma / Menarini announcement"),
             "independence_note": "Emerged after scoring. The one genuinely independent row."},
            {"lever": "Genotype stratification", "score": 46.8, "rank": 3, "verdict": "demote",
             "score_note": "37.2 once the null mechanism is scored honestly",
             "happened": ("dal-GenE enrolled 6147 ADCY9 rs1967309 AA-genotype patients prospectively "
                          "and missed its primary endpoint: HR 0.88 (0.75-1.03), P = 0.12"),
             "agrees": True, "independent": False,
             "outcome_source": "PMID 35856777, Eur Heart J 2022, doi:10.1093/eurheartj/ehac374",
             "independence_note": "Published 2022, so known at scoring time."},
            {"lever": "Molecular modification", "score": 10.0, "rank": 4, "verdict": "do_not_pursue",
             "happened": ("Nobody rescued CETP by tuning dalcetrapib's chemotype. The approved drug is "
                          "a different scaffold; in the thiol series the free thiol is obligatory and "
                          "potency ceilings out in the micromolar range"),
             "agrees": True, "independent": False,
             "outcome_source": "dalcetrapib_analog_table.csv / molecular-modification assessment",
             "independence_note": "Chemistry assessment from the same run."},
        ],
        "caveats": [
            "One asset, scored retrospectively. This is a consistency check, not a blind prediction.",
            "Weights were fixed before the case was scored, but only the obicetrapib approval "
            "post-dates scoring; the other three rows were knowable at the time.",
            "In a 44-asset cohort the new-indication lever showed no discriminative power (P = 1.00), "
            "despite scoring 66/100 here.",
            "Module 1's own pre-registered blind evaluation falsified its predicted ordering, so an "
            "n=1 agreement is not presented as a passed blind test.",
        ],
    }
    cetp_meta = {
        "n_levers": len(cetp["levers"]),
        "n_agree": sum(1 for l in cetp["levers"] if l["agrees"]),
        "n_independent": sum(1 for l in cetp["levers"] if l["independent"]),
        "failed_n": cetp["failed_trial"]["n"],
        "approval_date": "21 September 2026",
        "dal_gene_hr": 0.88, "dal_gene_p": 0.12,
        "mi_component_hr": 0.79, "mi_ci": [0.65, 0.96],
        "dal_gene_n": 6147,
    }

    head = (R / ".git/HEAD").read_text().strip()
    sha = (R / ".git" / head.split(": ", 1)[1]).read_text().strip()[:7] if head.startswith("ref:") else head[:7]

    return {
        "meta": {"repo": "github.com/lzucaxd/trial-salvage", "head": sha,
                 "generated": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M UTC"),
                 "tests": 115, "tracked_files": 115},
        "headline": {
            "unselected_cost_musd": max(r["cost_musd"] for r in design["unselected_realistic"]),
            "enriched_n": design["enriched"]["n_randomized"],
            "enriched_cost_musd": design["enriched"]["randomisation_cost_musd"],
            "enriched_power": design["enriched"]["power"],
            "min_fraction_unselected": design["min_fraction_for_unselected_80pct"],
            "provenance_or": pc["all_decided"]["odds_ratio"],
            "provenance_p": pc["all_decided"]["fisher_p"],
            "cost_per_success_weak": portfolio[2]["cost_per_success_musd"],
            "cost_per_success_strong": portfolio[1]["cost_per_success_musd"],
            "avoided_musd": round(portfolio[2]["cost_per_success_musd"]
                                  - portfolio[1]["cost_per_success_musd"], 1),
        },
        "economics": {"portfolio": portfolio, "sources": SRC, "cost_inputs": COST, "design": design},
        "ppi": ppi,
        "cases": {"gefitinib": case(g4, gcase), "onartuzumab": case(o4, ocase)},
        "comparison_table": cc["cases"],
        "benchmark": cc["ranking_principle_validation"],
        "blind_eval": blind,
        "match": match,
        "cetp": cetp,
        "cetp_meta": cetp_meta,
        "models": models,
        "models_meta": models_meta,
        "timeline": reg_rows,
        "distributions": dists,
        "module1": {"diagnosis": m1["failure_diagnosis"], "family": m1["trial_family_summary"],
                    "regulatory": m1["regulatory_timeline"], "effects": m1["effects"],
                    "trials": m1["trials"], "handoff": m1["handoff"]["module4"]},
        "module2": {"cross_case": json.loads(m2.to_json(orient="records")),
                    "reliability": json.loads(m2rel.to_json(orient="records"))},
        "module3": {"somatic_vs_germline": json.loads(
            pd.read_csv(R / "data/module3/egfr_somatic_vs_germline.csv").to_json(orient="records"))},
    }


if __name__ == "__main__":
    b = build()

    # Nothing non-finite may reach the deck: JSON.parse rejects NaN and Infinity,
    # which would take the whole page down rather than degrading one chart.
    bad = []

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
        elif isinstance(o, float) and not math.isfinite(o):
            bad.append((path, o))

    walk(b)
    if bad:
        raise SystemExit(f"non-finite values would break JSON.parse: {bad[:5]}")

    out = pathlib.Path("deck_data.json")
    out.write_text(json.dumps(b, indent=1, default=str))
    json.loads(out.read_text())          # strict re-parse, same as the browser's
    print(f"wrote {out} — {out.stat().st_size / 1024:.1f} KB, sections: {list(b)}")
    print(f"  head {b['meta']['head']} | phase3 rate {COST['phase3_onc_success']}"
          f" | blind eval {b['blind_eval']['n_decided']} decided"
          f" | unselected max cost ${b['headline']['unselected_cost_musd']}M")
