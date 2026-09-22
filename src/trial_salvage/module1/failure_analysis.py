"""Rule-based failure diagnosis from curated effects + trial records.

The output is deliberately explicit about *which* evidence fired which rule, so a
reviewer can disagree with a rule rather than with a black box.
"""
from __future__ import annotations

import pandas as pd

from .effects import fraction_for_target_hr, mixture_hr


def diagnose(effects: pd.DataFrame, cfg: dict) -> dict:
    failed_lbl = cfg["trials"]["failed"]["label"]
    rescue_lbl = cfg["trials"]["rescue"]["label"]
    gene = cfg["biomarker"]["gene"]
    ev: list[dict] = []

    fe = effects[effects.trial == failed_lbl]
    prim = fe[fe.analysis_type.str.contains("primary", case=False)]
    primary_missed = bool(len(prim)) and not bool(prim.significant.any())
    ev.append({"rule": "primary_endpoint_missed", "fired": primary_missed,
               "detail": "; ".join(f"{r.population}: HR {r.hr:.2f} ({r.ci_lo:.2f}-{r.ci_hi:.2f}), p={r.p}"
                                   for r in prim.itertuples())})

    sub = fe[fe.analysis_type.str.contains("prespecified subgroup", case=False)]
    sig_sub = sub[sub.significant & (sub.hr < 1)]
    ev.append({"rule": "prespecified_subgroup_benefit", "fired": len(sig_sub) > 0,
               "detail": "; ".join(f"{r.population}: HR {r.hr:.2f} ({r.ci_lo:.2f}-{r.ci_hi:.2f}), n={r.n}"
                                   for r in sig_sub.itertuples())})

    bio = fe[fe.analysis_type.str.contains("biomarker", case=False)]
    bio_split = bool(len(bio)) and bool((bio.hr < 1).any() and (bio.hr > 1).any())
    ev.append({"rule": "biomarker_heterogeneity_in_failed_trial", "fired": bio_split,
               "detail": "; ".join(f"{r.population}: HR {r.hr:.2f}" for r in bio.itertuples())})

    re_ = effects[(effects.trial == rescue_lbl) & effects.population.str.contains(f"{gene} mutation", case=False)
                  & effects.analysis_type.str.contains("biomarker subgroup", case=False)]
    pos = re_[re_.population.str.contains("positive", case=False)]
    neg = re_[re_.population.str.contains("negative", case=False)]
    qual = bool(len(pos) and len(neg)) and bool(pos.significant.all() and neg.significant.all()
                                                and (pos.hr < 1).all() and (neg.hr > 1).all())
    ev.append({"rule": "qualitative_interaction_in_rescue_trial", "fired": qual,
               "detail": (f"{gene}+ HR {pos.hr.iloc[0]:.2f}, {gene}- HR {neg.hr.iloc[0]:.2f}" if len(pos) and len(neg) else "")})

    os_conf = effects[(effects.trial == rescue_lbl) & (effects.endpoint == "OS") & effects.note.fillna("").str.contains("crossover")]
    ev.append({"rule": "os_confounded_by_crossover", "fired": len(os_conf) > 0,
               "detail": "; ".join(str(x) for x in os_conf.note.dropna().unique())})

    if primary_missed and (len(sig_sub) or bio_split) and qual:
        mode, conf = "population_dilution_qualitative_interaction", "high"
    elif primary_missed and (len(sig_sub) or bio_split):
        mode, conf = "population_dilution_suspected", "moderate"
    elif primary_missed:
        mode, conf = "efficacy_failure_no_heterogeneity_signal", "moderate"
    else:
        mode, conf = "not_a_primary_endpoint_failure", "low"

    mixture = None
    if len(pos) and len(neg):
        hp, hn = float(pos.hr.iloc[0]), float(neg.hr.iloc[0])
        mixture = {"hr_pos": hp, "hr_neg": hn, "endpoint": str(pos.endpoint.iloc[0]),
                   "mixture_hr_by_fraction": {f"{f:.1f}": round(mixture_hr(f, hp, hn), 3) for f in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]},
                   "fraction_for_hr_0.80": fraction_for_target_hr(0.80, hp, hn),
                   "fraction_for_hr_1.00": fraction_for_target_hr(1.00, hp, hn),
                   "caveat": "log-linear mixture approximation; see effects.mixture_hr docstring"}

    return {"failure_mode": mode, "confidence": conf, "evidence": ev, "mixture_model": mixture}


def salvage_strategy_map(cfg: dict, diag: dict) -> list[dict]:
    """Which of the generic salvage levers this case actually used."""
    f, r = cfg["trials"]["failed"], cfg["trials"]["rescue"]
    gene = cfg["biomarker"]["gene"]
    fired = {e["rule"] for e in diag["evidence"] if e["fired"]}
    return [
        {"strategy": "biomarker_enrichment_new_inclusion_criteria", "used": "qualitative_interaction_in_rescue_trial" in fired,
         "evidence": f"{gene} mutation subgroup split in {r['label']}"},
        {"strategy": "clinical_surrogate_enrichment", "used": True,
         "evidence": f"{r['label']} enrolled on histology/smoking/geography before a validated assay"},
        {"strategy": "new_endpoint", "used": f["primary_endpoint"] != r["primary_endpoint"],
         "evidence": f"{f['primary_endpoint']} -> {r['primary_endpoint']}"
                     + ("; OS confounded by crossover" if "os_confounded_by_crossover" in fired else "")},
        {"strategy": "new_line_of_therapy", "used": f.get("line_of_therapy") != r.get("line_of_therapy"),
         "evidence": f"{f.get('line_of_therapy')} -> {r.get('line_of_therapy')}"},
        {"strategy": "narrower_indication", "used": True, "evidence": f"{cfg['disease']['name']} -> {gene}-mutant {cfg['disease'].get('histology_of_interest','')}"},
        {"strategy": "molecule_modification", "used": False, "evidence": "not for this asset; class evolved (module 2 question)"},
    ]
