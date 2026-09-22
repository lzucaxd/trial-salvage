# Module 3 vs the rescue benchmark (v0)

Branch `module3-benchmark-eval`. Code `src/trial_salvage/module3/benchmark_eval.py`; data `data/benchmark/`.

## Pre-registered lane-verdict rule (committed before outcomes were joined)
Inputs per asset: Open Targets targets (`search_drug` → `drug_record`, `name_matches` guard, `drug_targets`).
Per target, first match wins:
1. **somatic** — oncology pair and the target's single most recurrent protein change is in ≥ 1 % of samples of the
   indication-matched cBioPortal study (NSCLC `nsclc_tcga_broad_2016`, ovarian `ov_tcga_pan_can_atlas_2018`,
   prostate `prad_su2c_2019`, HCC `lihc_tcga_pan_can_atlas_2018`, DLBCL `dlbcl_duke_2017`, melanoma
   `skcm_tcga_pan_can_atlas_2018`; otherwise pan-cancer `msk_impact_2017`). Whole-exome studies, so every target
   is profiled.
2. **germline_common** — ≥ 3 common (MAF > 1 %) functional variants in gnomAD v4 and LOEUF ≥ 0.6.
3. **none_detected**.

Per asset: the first lane (somatic > germline_common > none) reached by *any* target. `not_evaluable` (excluded
from outcome tables, listed): no Open Targets hit or name-guard failure, no targets, or > 10 targets (complexes,
e.g. ataluren → 80 ribosomal proteins). Outcome tables use `success` / `fail` only; `contested` / `pending` listed.

Pre-stated expectations and what would falsify the approach:
- **Regime (b):** retries that selected on a somatic alteration should get `somatic`; retries that selected on
  clinical / circulating / expression markers should *not*. Falsified if `somatic` is called as often for
  non-genomic retries as for somatic ones, or if a somatic-selected retry gets `none_detected`.
- **Outcome (a):** `somatic` should be enriched for success vs other lanes. Falsified (as a decision aid) if the
  enrichment vanishes when the EGFR-mutant NSCLC cluster (4 pairs) is removed (c) — then the signal is one biology.
- Germline *monogenic* retries (rare disease-gene variants, e.g. BRCA1/2) are outside both lanes by design;
  reported as `monogenic_not_modelled`, not as hits or misses.
- `germline_common` is not expected to predict success (benchmark: common-variant retries 0/2).

Caveat on blinding: outcomes sit in the same CSV and headline rates were known from the benchmark README, so this
guards only against tuning thresholds or study choices after the join, not against prior knowledge.
