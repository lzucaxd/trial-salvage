# Module 3 — genomic stratification (germline + somatic lanes)

Branch `module3-genomic-stratification`. Status: germline and somatic lanes run; AlphaGenome not started.

## Question
For a failed trial's drug target, is there population variation a retry could stratify on — and in which
regime? Germline (inherited, gnomAD) and somatic (tumour-acquired, cBioPortal) must not be mixed.

## Germline lane — validated
Score = LOEUF tolerance × common (MAF > 1 %) functional-variant burden, over the target or its Reactome pathway.
On a 24-gene panel, 5 of the top 7 are CPIC pharmacogenes (CYP2D6 first, 0.74); constrained controls rank last.
The separation is carried by LOEUF, not raw variant counts. Data: `data/module3/pharmacogene_validation_panel.csv`.

## Gefitinib — why the somatic lane is needed
EGFR → Reactome R-HSA-177929 (53 genes, 50 scored): 49 common functional variants in total, 28 genes with none,
EGFR itself 1. The ISEL → IPASS drivers are somatic:

| Variant | Somatic, LUAD (cBioPortal MSK, n = 2,653) | Germline, gnomAD v4 (1.6 M alleles) |
|---|---|---|
| L858R | 10.9 % | not detected |
| T790M | 3.4 % | 16 carriers (AF 9.9e-06) |
| G719S | 0.45 % | not detected |

Reproduce: `make module3-egfr`.

## Consistency with the rescue benchmark
`data/benchmark`: retries selected on somatic drivers 4/4, germline monogenic 2/3, germline common variants 0/2
(both post-hoc subgroups, n = 2, so confounded with the post-hoc effect). Module 3 therefore reports *which lane*
carries variation, not a rescue probability.

## Candidate failed trials (`data/candidates/`)
8,603 terminated/withdrawn Phase 2–3 trials with a stated reason → regex + LLM check of `whyStopped` → 179
efficacy failures (n ≥ 100, drug mapped to Open Targets with a name/synonym guard) = 221 trial–drug pairs,
173 drugs, 209 targets. Constraint so far covers the 182 targets of each trial's first-listed drug (177 have
gnomAD scores); 27 targets from second drugs in combination trials are not yet scored. Keyword matching alone was wrong ~5 % of the time (e.g. "no efficacy/safety concerns").

## API gotchas
gnomAD: no key, ~10 req/min/IP, query cost cap 25 (≤ 20 aliased genes), no PolyPhen/SIFT on gene variants
(use Ensembl VEP), fold AF to MAF. Open Targets: `maximumClinicalStage`; synonyms need `{ label }`.

## Results v0 — failed-trial targets scored (germline lane)
176 of the 182 first-drug targets scored (5 lack gnomAD constraint, 1 lacks variant data).
`data/candidates/failed_trial_target_scores_v0.csv`.

- **73 of 176 targets have zero common functional variants**; the median is 1. For most failed trials, common
  germline variation in the target is not a plausible explanation, which is itself a useful negative.
- **Top of the ranking is contaminated.** MUC5AC (87 common functional variants) and MUC16 (135) rank 1–2 because
  mucins are huge, repetitive (VNTR) genes, and both are antibody-targeted tumour antigens where germline variation
  is irrelevant. The burden term is not normalized for coding length — fix before trusting the top ranks.
- Plausible germline-lane hits after the mucins are receptor genes with known common coding variation: DRD4
  (haloperidol), ADRA1A (tamsulosin), OPRM1 (buprenorphine), MTNR1A/B (piromelatine), MAPT (3 anti-tau antibodies).
- Most constrained, i.e. germline stratification least plausible: GRIN2B (LOEUF 0.09), GRIA3, NFKB1, JAK1, BTK.

Next: normalize burden by coding length or expected variant count; score the 27 second-drug targets; run the
somatic lane for oncology trials; test the lane verdict against the rescue benchmark's 38 decided pairs.

## Results v1 — all 209 failed-trial targets, length-normalised score
Per-track notes: [normalisation](module3_normalization.md), [second-drug targets](module3_second_drug_targets.md),
[benchmark eval](module3_benchmark_eval.md). Data: `data/candidates/failed_trial_target_scores_v1_all.csv`
(`PYTHONPATH=src python scripts/score_all_failed_trial_targets.py`; 182 first-drug + 27 second-drug targets).

- **202 of 209 scored** (7 unscored: ADRB1, CCR2, CCR5, CXCR1, S1PR5 lack constraint; GRIN3B lacks variant data;
  SSTR3 has no LOEUF). **85 of 202 have zero common functional variants.**
- Score v1 = tolerance × (n_common_func / exp_syn) / max, genes with oe_syn > 1.35 ranked after the rest
  (4: MUC5AC, DRD4, HSP90AA1, TSLP). New QC flag `low_exp_lof` (exp_lof < 10: LOEUF unreliable; SSTR5 has LOEUF 14.1
  on exp_lof 0.34): **9 of 209 flagged** (CALCA, SSTR5, MTNR1B, MTNR1A, ADORA3, S1PR4, CXCR2, IL17A, P2RY12); they keep
  their score but rank after every unflagged gene. `module3.run` germline lane uses the same v1 score + flag.
- **Top 10:** HTR3D, P2RX7, ADRA1A, OPRM1, HRH4, LTA, MYL7, MUC16, HTR3C, AR. Best second-drug target: TYK2 (rank 51).
- Caveats (v1): the oe_syn > 1.35 gate was chosen post hoc (margin: CYP2C9 at 1.29) and demotes DRD4, whose VNTR is a
  studied pharmacogenetic marker. The pharmacogene gain over v0 is 1 gene (6 vs 5 of the top 7 of 24), within noise.
  Normalisation over-corrects toward small genes (rho(burden, exp_syn) -0.09 → -0.48; MYL7 is in the top 10 on k = 1).
- **Benchmark (lane verdict vs retry outcome):** `somatic` vs other lanes, Fisher p = 0.015 on n = 32 evaluable pairs,
  falling to p = 0.39 (n = 28) without the EGFR-mutant NSCLC cluster; all 5 somatic calls are EGFR L858R. Selection
  regime: 4/5 somatic-selected retries called `somatic` vs 1/27 others (p = 0.0007), again on one gene. Most retry
  stratifiers are not the drug target (PTEN, APOE, BRCA1/2, DMD), so a disease-gene lane is needed before the verdict
  can serve as a rescue predictor.

