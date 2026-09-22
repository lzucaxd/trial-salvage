# Module 3 — germline data for second-drug targets (combination trials)

**What.** Targets in `data/candidates/ctgov_efficacy_failures_trial_drug_pairs_v0.csv` (221 trial-drug pairs, 179
efficacy-failure trials; 209 distinct target symbols) that were not yet in `failed_trial_target_scores_v0.csv`
(182 symbols). **27 added:** BCL2, BIRC2, BIRC3, CASR, CD47, CHRM1, CSF3R, DHFR, ERBB2, ERBB3, ESR1, GART, HTR2C,
IMPDH1, IMPDH2, JAK3, KEAP1, MET, NPC1L1, PTH1R, SLC22A12, SSTR1, SSTR2, SSTR3, SSTR5, TYK2, TYMS
(38 trial-drug links in total; `trials` column lists `DRUG (NCT...)`).

**How.** `PYTHONPATH=src python scripts/fetch_second_drug_targets.py` -> `data/candidates/second_drug_targets_raw_v0.csv`.
gnomAD r4 constraint (LOEUF, oe_lof, pLI, mis_z, obs/exp LoF, missense, synonymous) via two aliased GraphQL queries
(20 + 7 genes); variants via `gnomad.gene_variants`, summarised with `germline.summarize_variants` (MAF > 1 %,
unchanged). Requests paced >= 20 s, 429 -> 65 s backoff (none occurred); responses cached in `data/raw/gnomad_cache/`
(gitignored), so a re-run is offline. No score computed: the integrator applies the v1 score.

**Results.**
- All 27 genes are known to gnomAD and have variant data (status `ok` for 26); none dropped.
- 1 unscoreable on LOEUF: **SSTR3** (`no_lof_constraint`) — intronless gene with no expected LoF sites, so gnomAD
  reports no LOEUF/pLI/obs_lof/exp_lof (mis_z = 1.75 and missense/synonymous counts are present).
- 1 LOEUF to treat as unreliable: **SSTR5**, LOEUF = 14.1 from exp_lof = 0.34 (obs_lof = 1). Clip/flag before scoring
  (the v0 tolerance term clips at 2, which would give it maximal tolerance on essentially no information).
- **12 of 27 have zero common functional variants** (n_common_func = 0): BCL2, BIRC3, CD47, CHRM1, DHFR, ESR1, IMPDH1,
  IMPDH2, JAK3, SLC22A12, SSTR2, TYMS — nothing common-germline to stratify on under the v0 burden term.
- Most common functional variation: TYK2 (4; cum MAF 0.46), SSTR5 (4; 0.61), CASR / ERBB2 / ERBB3 / MET (3 each).
- Caveat: MAF threshold is global (joint) frequency; population-restricted variants (e.g. SLC22A12 W258X, East Asian)
  are missed. Common-variant stratification was 0/2 in the rescue benchmark — report beside the somatic lane.
