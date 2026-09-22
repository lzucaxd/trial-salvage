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
