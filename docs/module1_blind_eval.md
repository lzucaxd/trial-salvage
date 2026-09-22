# Module 1 vs the rescue benchmark — blind evaluation v0

Code `src/trial_salvage/module1/blind_eval.py` (rule committed `614b7aa`, amended `ec3d4d2` before the join);
data `data/benchmark/blind/`. Pairs: 35 decided (15 success / 20 fail); enzastaurin excluded (no retrievable
PRELUDE abstract); aducanumab (contested) evaluated but excluded from outcome tables.

## What was done
1. For each failed trial, PubMed abstracts about **that trial only**, published before the retry started (six retry-trial
   abstracts explicitly excluded: REACH-2, ESCAPE-NEXT, DERMA, MAGRIT, bapineuzumab Ph3, STRATOS). 72 abstracts, 36 assets.
2. LLM extraction of every effect estimate into the module-1 effects schema, with `analysis_type` taken from the abstract's
   own wording. 205 rows; **every numeric estimate (111/111) verified literally present in its abstract**; rows with a
   p-value but no estimate were dropped by the provenance filter (this matters — see limitations).
3. Pre-registered verdict per asset (`retry_supported` / `retry_weak` / `not_supported` / `primary_not_missed` / `not_evaluable`),
   saved to `module1_blind_verdicts_prejoin_v0.csv` **before** outcomes were joined.

## Result — the pre-registered ordering is falsified

| verdict | fail | success | rate |
|---|---|---|---|
| retry_supported | 2.0 | 1.0 | 0.33 |
| retry_weak | 1.0 | 6.0 | 0.86 |
| not_supported | 10.0 | 4.0 | 0.29 |
| primary_not_missed | 4.0 | 4.0 | 0.5 |
| not_evaluable | 3.0 | 0.0 | 0.0 |

Expected `retry_supported > retry_weak >= not_supported`. Observed: retry_supported 1/3 (gefitinib only; farletuzumab and
ganetespib carried prespecified-labelled subgroup benefits and failed), retry_weak 6/7, not_supported 4/14.
`retry_supported` vs rest: Fisher p = 1.0. Removing the EGFR cluster leaves retry_supported at 0/2.

What does carry a weak signal is the coarser split the module-1 rules collapse to: **any favourable subgroup or secondary
signal in the failed trial** (supported + weak) 7/10 success vs **none** 4/14 (Fisher p = 0.095). Direction as expected,
n far too small to lean on.

## Why the prespecified / post-hoc distinction did not work here
- **Abstracts rarely say it.** Most favourable subgroup rows came back `unspecified subgroup`, which the rule bins with
  post hoc. The `retry_weak` successes (afatinib, belimumab, sipuleucel-T, tofersen, vorapaxar, rituximab→ocrelizumab)
  are all cases where the abstract reports a favourable secondary/subgroup result without stating whether it was planned.
  The benchmark's hand-coded `motivating_signal` column (59% vs 19%) used knowledge that is in full texts and protocols,
  not abstracts.
- **Provenance filter cost recall.** Rows with a p-value but no numeric estimate (TRIBUTE's EGFR-mutation response,
  p<0.05) were dropped, so erlotinib came out `not_supported`. REACH's AFP subgroup is not in its PubMed abstract at all.
  At least 2 of the 4 `not_supported` successes are abstract-recall failures, not rule failures.
- **Nine pairs were not primary-endpoint failures** (Study 19, LUME-Lung 1, GALACTIC-HF, PRECEDENT, ARCHER 1009 as
  extracted, IPATential150, onartuzumab Ph2, mepolizumab, aducanumab). Their "failure" was regulatory or an OS miss after a
  positive primary — outside what the module-1 rules were written for. The verdict `primary_not_missed` is correct for them
  and the benchmark should carry a `failure_type` column to separate these.
- **Rescue evidence often came from outside the failed trial** (necitumumab: squamous histology from mechanism and
  other trials; pirfenidone: the sibling CAPACITY 004). A rule that reads only the failed trial cannot see it.

## What this means for the tool
Module 1's rules, fed from abstracts alone, do **not** discriminate rescues that worked from rescues that failed on this
benchmark. The honest claims that survive: (1) the pipeline reproduces gefitinib; (2) "no heterogeneity signal anywhere in
the failed trial" was 10/14 fail — the *abandon* side is the stronger one; (3) the evidence base has to move from abstracts
to full text / posted results before the prespecified-vs-post-hoc distinction can be tested at all.

## Next steps, in order
1. Add `failure_type` to the benchmark (primary miss / OS miss after positive primary / regulatory / safety) and evaluate
   only primary-miss pairs.
2. Full-text extraction (Europe PMC OA + CT.gov posted results) so `analysis_type` and p-only rows are recoverable.
3. Re-run with the same pre-registered rule; report the change.
