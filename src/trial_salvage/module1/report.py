"""Render the module-1 markdown report from the structured output."""
from __future__ import annotations

import pandas as pd


def render(out: dict, effects: pd.DataFrame, reg: pd.DataFrame, fig_rel: str) -> str:
    a, t = out["asset"], out["trials"]
    f, r = t["failed"], t["rescue"]
    d = out["failure_diagnosis"]
    L = []
    L.append(f"# {a['name']} \u2014 Module 1: clinical evidence and failure analysis\n")
    L.append(f"**Target** {out['target']['symbol']} \u00b7 **Indication** {out['disease']['name']} \u00b7 "
             f"**Failed trial** {f['label']} ({f['nct']}) \u00b7 **Rescue trial** {r['label']} ({r['nct']})\n")
    L.append(f"Generated {out['generated_at']} by `trial_salvage.module1` from ClinicalTrials.gov v2, PubMed and curated effect estimates.\n")
    L.append(f"![figure]({fig_rel})\n")
    L.append("## 1. Failure diagnosis\n")
    L.append(f"**Mode:** `{d['failure_mode']}` (confidence: {d['confidence']})\n")
    L.append("| Rule | Fired | Evidence |\n|---|---|---|")
    for e in d["evidence"]:
        L.append(f"| {e['rule']} | {'yes' if e['fired'] else 'no'} | {e['detail']} |")
    if d.get("mixture_model"):
        m = d["mixture_model"]
        f80 = m["fraction_for_hr_0.80"]; f100 = m["fraction_for_hr_1.00"]
        L.append(f"\nMixture check ({m['endpoint']}; HR+ {m['hr_pos']}, HR\u2212 {m['hr_neg']}): responder fraction needed for ITT HR "
                 f"\u2264 0.80 \u2248 **{f80:.2f}**; for HR = 1.00 \u2248 {f100:.2f}. {m['caveat']}.\n")
    L.append("## 2. Trials\n")
    L.append("| | Failed | Rescue |\n|---|---|---|")
    for k in ["nct", "label", "status", "start", "completion", "enrollment", "phase", "masking", "primary_endpoint", "primary_outcomes", "results_posted", "n_pmids"]:
        L.append(f"| {k} | {f.get(k, '')} | {r.get(k, '')} |")
    L.append(f"\n**{f['label']} eligibility (registry text)**\n\n```\n{f['eligibility'][:1500]}\n```\n")
    L.append(f"**{r['label']} eligibility (registry text)**\n\n```\n{r['eligibility'][:1500]}\n```\n")
    L.append("## 3. Effect estimates (curated, provenance-checked)\n")
    L.append("| Trial | Population | Endpoint | HR (95% CI) | p | n | Type | PMID | HR in abstract |\n|---|---|---|---|---|---|---|---|---|")
    for e in effects.itertuples():
        ci = f" ({e.ci_lo:.2f}\u2013{e.ci_hi:.2f})" if pd.notna(e.ci_lo) else ""
        L.append(f"| {e.trial} | {e.population} | {e.endpoint} | {e.hr:.2f}{ci} | {e.p if isinstance(e.p, str) else ''} | "
                 f"{e.n if isinstance(e.n, str) else ''} | {e.analysis_type} | {e.pmid} | {'yes' if e.hr_in_abstract else 'REVIEW'} |")
    L.append("\n## 4. Registry results posting\n")
    for lbl, tr in (("failed", f), ("rescue", r)):
        L.append(f"- **{tr['label']}**: results posted = {tr['results_posted']}; posted primary-outcome rows = {tr['n_posted_primary_rows']}. "
                 + (tr.get("posting_note") or ""))
    L.append("\n## 5. Biomarker selection across the trial family\n")
    fam = out["trial_family_summary"]
    L.append(f"{fam['n_trials']} interventional trials of {a['name']}; {fam['n_in_indication']} in the indication; "
             f"{fam['n_phase3_in_indication']} Phase 3; {fam['n_with_results']} with posted results.\n")
    L.append("| Start years | Trials in indication | Biomarker required |\n|---|---|---|")
    for row in fam["selection_by_period"]:
        L.append(f"| {row['period']} | {row['trials']} | {row['required']} |")
    L.append("\n## 6. Regulatory timeline\n")
    L.append("| Date | Agency | Event | Source |\n|---|---|---|---|")
    for e in reg.itertuples():
        L.append(f"| {e.date} | {e.agency} | {e.event} | {e.source} |")
    L.append("\n## 7. Salvage strategies used in this case\n")
    L.append("| Strategy | Used | Evidence |\n|---|---|---|")
    for s in out["salvage_strategies"]:
        L.append(f"| {s['strategy']} | {'yes' if s['used'] else 'no'} | {s['evidence']} |")
    L.append("\n## 8. Hand-off to modules 2\u20134\n")
    h = out["handoff"]
    L.append(f"- **Module 2 (protein variants / ESM):** target {h['module2']['uniprot']}; sensitising {h['module2']['sensitising_variants']}; "
             f"primary resistance {h['module2']['primary_resistance_variants']}; acquired {h['module2']['acquired_resistance_variants']}.")
    L.append(f"- **Module 3 (genomic stratification):** gene {h['module3']['gene']}, disease {h['module3']['disease_efo']}; clinical proxies to beat: {h['module3']['clinical_proxy_subgroups']}.")
    L.append(f"- **Module 4 (trial simulation):** subgroup HRs {h['module4']['hr_pos']} / {h['module4']['hr_neg']} ({h['module4']['endpoint']}); "
             f"sweep responder fraction {h['module4']['responder_fraction_sweep']}; ITT reference HR {h['module4']['itt_reference_hr']}.")
    return "\n".join(L) + "\n"
