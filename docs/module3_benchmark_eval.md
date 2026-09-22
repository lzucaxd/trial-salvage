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

## Results (joined after the rule commit) — `data/benchmark/module3_benchmark_eval_v0.csv`
Overlap with our 179 efficacy failures: 6/40 pairs by NCT — failed_nct 4 (aducanumab, farletuzumab, motesanib,
tivantinib [listed as partner ERLOTINIB]), retry_nct 4 (aducanumab, ganetespib, motesanib, solanezumab); 7/38 assets
by name. 37/38 assets pass the Open Targets name guard; not evaluable: 6/38 decided pairs (MAGE-A3 ×2 no hit;
nerinetide, rigosertib, pirfenidone no targets; ataluren 78). Excluded: aducanumab (contested), bimagrumab
(pending), both `none_detected`. Germline: 24 genes from scores_v0, 28 from gnomAD v4 (`*_targets_v0.csv`).

| fail / success | somatic | germline_common | none_detected |
|---|---|---|---|
| (a) all evaluable, n = 32 | 0 / 5 | 2 / 1 | 15 / 9 |
| (c) EGFR cluster removed, n = 28 | 0 / 1 (necitumumab) | 2 / 1 | 15 / 9 |

Somatic vs rest, Fisher: p = 0.015 (a) → 0.39 (c). Every somatic call is EGFR L858R (2.4 % of 1,144 pan-lung).
(b) n = 32: 4/5 somatic-selected retries called `somatic` (EGFR ×4; miss: ipatasertib, stratifier PTEN, AKT1 E17K
0.68 %) vs 1/27 other retries (necitumumab, histology-selected), p = 0.0007. Common-variant retries 0/2 detected
(APOE, DGM1 SNP — not the targets APP, PRKCB); `germline_common` fired 3×, all on clinical retries (omecamtiv,
tarenflurbil, nintedanib). Descriptive, tiny n: outside EGFR the verdict has no outcome signal — (a) falsified by
(c); (b) holds on one gene. Stratifiers are mostly not the target (PTEN, APOE, BRCA1/2, DMD): add disease-gene lanes.
