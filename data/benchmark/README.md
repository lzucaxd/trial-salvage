# Rescue benchmark v0

A retrospective test set for the salvage question: **after a negative trial, did a re-targeted retry succeed?**
Used to check whether module 1's signals (available at the time of the first failure) discriminate rescues
that worked from rescues that failed. If they do not, module 1 is a document generator, not a decision aid.

## Curation rules
- A *pair* = one failed trial (primary endpoint missed, or stopped for efficacy/safety) + one retry of the same
  asset (or a same-target successor, flagged) using at least one salvage lever: biomarker enrichment,
  clinical enrichment, endpoint change, narrower indication / safety exclusion, new indication, dose/regimen,
  molecule modification.
- `outcome`: **success** = retry met its primary endpoint AND led to a regulatory approval (or EMA-only approval,
  flagged); **fail** = retry missed its primary endpoint or was refused/withdrawn; **contested** = approved then
  withdrawn without confirmation; **pending** = retry ongoing.
- `motivating_signal`: whether the selection used in the retry came from a prespecified analysis or a
  mechanistic rationale (`prespecified_or_mechanistic`) or from an unplanned subgroup finding (`post_hoc_subgroup`).
- Every NCT is checked against ClinicalTrials.gov v2 (40/40 retry trials, 38/40 failed trials — the two misses
  predate mandatory registration: TRIBUTE and the 2007 mepolizumab trial). Every retry has a PubMed record
  (`retry_pmid`); the `outcome_basis` text is the claim that record should support.
- `curation_confidence` low/moderate rows need a second reader before use in any evaluation.

## Headline numbers (v0, 38 decided pairs)

| Lever family | fail | success | rate |
|---|---|---|---|
| biomarker_enrichment | 11.0 | 9.0 | 0.45 |
| clinical_enrichment | 9.0 | 1.0 | 0.10 |
| dose_regimen | 1.0 | 0.0 | 0.00 |
| endpoint_change | 0.0 | 2.0 | 1.00 |
| molecule_modification | 0.0 | 1.0 | 1.00 |
| narrower_indication | 1.0 | 3.0 | 0.75 |

| Motivating signal | fail | success | rate |
|---|---|---|---|
| post_hoc_subgroup | 13.0 | 3.0 | 0.19 |
| prespecified_or_mechanistic | 9.0 | 13.0 | 0.59 |

Caveats that matter more than the rates:
- **Selection bias.** Successes are famous and easy to list; failed retries are under-reported, so the true
  success rate is lower than 42%.
- **One biology counts four times.** gefitinib, erlotinib, afatinib, dacomitinib are all EGFR-mutant NSCLC.
  Excluding that cluster: 12/34 success overall; post-hoc-motivated retries
  2/15; prespecified/mechanistic
  10/19.
- v0 is seeded from domain knowledge and verified against registry + PubMed; it is not a systematic search.
  A registry-driven candidate scan (asset with efficacy-stopped trial → later trial in same indication with
  selection criteria) is the next step to reduce the selection bias.

## Intended use
Run module 1 on each *failed* trial using only pre-retry information, record which rules fire, and test whether
`prespecified_subgroup_benefit` / `biomarker_heterogeneity_in_failed_trial` (vs a post-hoc-only signal) separate
the success and fail columns. That requires curating a `<asset>_effects.csv` per pair — about 40 short curation
jobs, which is the real cost of the benchmark.
