# trial-salvage

**Can a failed drug candidate be rescued — and how?**
A four-module pipeline that takes a failed trial and asks whether the drug should be abandoned or
re-tried with new inclusion criteria (population stratification), a new endpoint, a narrower
indication, or a modified molecule.

```
Trial ID + drug + disease + target        (config/assets/<asset>.yaml)
    ├── 1. Clinical evidence and failure analysis       ✅ implemented   src/trial_salvage/module1
    ├── 2. Protein variants and ESM                     ✅ implemented   src/trial_salvage/module2
    ├── 3. Genomic stratification and AlphaGenome       ⬜ stub          src/trial_salvage/module3
    └── 4. Rescue-hypothesis ranking + trial simulation ✅ implemented   src/trial_salvage/module4
            → ranked rescue strategies, evidence, next experiments
```

Demo asset: **gefitinib** — ISEL (NCT00242801) failed on overall survival in unselected NSCLC;
IPASS (NCT00322452) showed a qualitative interaction with EGFR mutation status; the drug was
re-approved in 2015 for EGFR exon 19 del / L858R disease.

## Quick start

```bash
pip install -e ".[dev]"
make module1            # live fetch from ClinicalTrials.gov v2 + PubMed (~30 s)
make module1-offline    # replay from the committed data/raw/gefitinib/ snapshot (no network)
make module2-all        # ESM verdicts for all 5 asset configs (offline, no GPU, ~5 s)
make module4            # simulate + rank from module 1's handoff (~10 s, no network)
make all                # module1 -> module2 -> module4
make test               # unit tests (no network)
```

Outputs land in `outputs/module1/`:

| File | What |
|---|---|
| `module1_output.json` | schema-validated structured result — **the contract for modules 2–4** (`schemas/module1_output.schema.json`) |
| `module1_report.md` | human-readable failure analysis |
| `fig_<asset>_module1.png` | forest plot of effect estimates + biomarker-selection adoption timeline |
| `effect_estimates_checked.csv` | curated HRs with a per-row provenance flag (is the number in the cited abstract?) |
| `trial_family.csv` | every interventional trial of the asset with biomarker-selection flags parsed from eligibility text |
| `posted_outcomes.csv` | what ClinicalTrials.gov actually posts for the two anchor trials |

## Module 1 — what it does

1. **Fetch** both anchor trials (full records incl. results section), the asset's entire trial family
   (`query.intr`), and the landmark abstracts (PubMed E-utilities).
2. **Curate + check.** Effect estimates live in `data/curated/<asset>_effects.csv` with PMID/NCT provenance.
   Every HR is checked for literal presence in its cited abstract; rows that fail are flagged `REVIEW`, never dropped silently.
3. **Parse eligibility** for biomarker selection (`module1/eligibility.py`) across the family → adoption timeline.
4. **Diagnose** with explicit rules (`module1/failure_analysis.py`): primary endpoint missed? prespecified subgroup
   benefit? biomarker heterogeneity in the failed trial? qualitative interaction in the rescue trial? OS confounded
   by crossover? Each rule reports what fired and why.
5. **Mixture check**: log-linear mixture of subgroup HRs vs responder fraction — the first-order answer to
   "could the unselected trial ever have won?"
6. **Hand off** structured inputs to modules 2–4.

### Gefitinib result (from `outputs/module1/module1_output.json`)

- Failure mode: **`population_dilution_qualitative_interaction`** (confidence high)
- ISEL OS HR 0.89 (0.77–1.02), p=0.087 — missed; never-smokers HR 0.67, Asian origin HR 0.66 (prespecified, both p≈0.01)
- IPASS PFS: EGFR-mutant HR 0.48 (0.36–0.64) vs EGFR-wild-type HR 2.85 (2.05–3.98) — qualitative interaction
- Mixture check (PFS): ITT HR reaches 1.00 at responder fraction **0.59** and 0.80 at **0.71**;
  an unselected Western population (~10–15% mutant) cannot win, an East-Asian never-smoker adenocarcinoma population (~60%) barely can — matching what happened
- Registry gap: ISEL posts no results at all; IPASS posts medians (5.7 vs 5.8 months PFS) but no HR — the biomarker effect exists only in the literature
- Trial family: 390 interventional trials, 232 in NSCLC; EGFR mutation required in
  0/41 trials started 2000–04 vs
  27/39 started 2017–20
- 17/17 curated hazard ratios verified against their PubMed abstracts

## Module 2 — what it does

Scores **every single-residue substitution** in a selection gene with an ESM-1v five-model
ensemble (masked marginals, Meier et al. 2021), validates the scores against independently
retrieved ClinVar labels, and emits an **applicability verdict decided by measured performance**.

The headline is a negative result worth acting on: across six selection genes the score is a
usable residue-level triage signal on two and no better than PolyPhen/SIFT on the rest. EGFR — the
gene the module was first built against — is the exception, not the rule.

| Selection gene | Drug | ESM (matched) | Best classical | Verdict |
|---|---|---|---|---|
| EGFR  | gefitinib    | **0.802** | 0.793 | `rank_residues_only` |
| APOE  | bapineuzumab | 0.736 (no PolyPhen/SIFT coverage) | — | `rank_residues_only` |
| BRCA1 | olaparib     | 0.607 | **SIFT 0.651** | `do_not_rank` |
| BRCA2 | olaparib     | 0.446 | **PolyPhen 0.616** | `do_not_rank` |
| SOD1  | tofersen     | not measurable (2 benign exist) | — | `not_validated` |
| PARP1 | olaparib     | not measurable (0 pathogenic) | — | `not_validated` |

**Read `applicability.verdict` before the scores.** BRCA2 is below chance; APOE ε4 — the strongest
common risk allele in Alzheimer disease — scores as *more plausible than wild type* because it is
the ancestral mammalian residue; SOD1 sits at chance because ALS there is a misfolding
gain-of-function that leaves evolutionary constraint intact. ESM scores evolutionary plausibility
and cannot infer the direction of a functional effect.

Three generalizations over the original EGFR-only version:

1. **Selection gene ≠ drug target.** `target_id` still means the drug target, so module 4's
   handoff is unchanged; `selection_gene_id` says where the variants live. This is what makes
   olaparib expressible — variants in BRCA1/BRCA2, drug target PARP1 (`synthetic_lethality`).
   Also supported: `same_protein_drug_target`, `same_gene_antisense`, `stratification_marker_only`.
2. **Any protein length.** Proteins below the ESM-1v 1022-token limit are scored whole with no
   truncation; longer ones use overlapping tiles with each position scored where it sits most
   interior (BRCA2 needs 5). The tiling artifact was measured, not assumed: median 0.18 log units.
3. **Per-gene numbering verification.** Literature nomenclature is offset from UniProt by **+1**
   for SOD1 (A4V = position 5) and **+18** for APOE (ε4 C112R = position 130), and identity for
   BRCA1/BRCA2/EGFR. Every case asserts the expected residue and raises on a mismatch.

Outputs land in `outputs/module2/<asset>/`:

| file | contents |
|---|---|
| `module2_output.json` | schema-validated result (`schemas/module2_output.schema.json`) with the applicability verdict, AUROCs incl. matched-subset baselines, positional decomposition, and the residue constraint map |

`make module2-all` runs offline from the committed tables in `data/module2/` — no network, no GPU.
Re-scoring needs a GPU: `scripts/score_module2_case.py` (the committed tables came from Modal A10G
sandboxes, one per model shard). Full write-up including the figure:
[`docs/module2_esm_variant_scoring.md`](docs/module2_esm_variant_scoring.md).

## Module 4 — what it does

Consumes `handoff.module4` from module 1 (`endpoint`, `hr_pos`, `hr_neg`,
`itt_reference_hr`, `failed_trial_itt_hr`, `responder_fraction_sweep`, trial sizes)
and answers **what a redesigned trial would require**.

1. **Simulate.** Exponential time-to-event trials, one-sided log-rank test.
   Three designs: `unselected` (mixture population), `enriched` (biomarker-positive
   only, screening burden `n / f`), `clinical_surrogate` (imperfect proxy).
   The mixture is simulated participant by participant rather than through module 1's
   log-linear `mixture_hr` approximation — hazard ratios are not collapsible across
   strata, so simulating avoids assuming the pooled ratio is a weighted mean of the
   stratum ratios.
2. **Calibrate.** Re-simulate the failed trial and the rescue trial at their observed
   ITT hazard ratios and actual sizes; the miss/win ordering must come out right.
3. **Rank.** Strategies are placed in visible tiers set by the module 1 diagnosis
   rules that fired, never by plausibility. Each entry carries the module 1 evidence
   it rests on, a next experiment, and the observation that would undermine it.

Outputs land in `outputs/module4/`:

| File | What |
|---|---|
| `module4_output.json` | schema-validated result (`schemas/module4_output.schema.json`) |
| `module4_report.md` | human-readable requirements, calibration and ranking |
| `fig_<asset>_module4.png` | power vs responder fraction + screening burden |

Result for gefitinib (PFS, hr_pos 0.48, hr_neg 2.85):

| Question | Answer |
|---|---|
| Re-run unselected at n=800? | needs **65%** of the population EGFR-positive to reach 80% power |
| Enriched trial? | **100 randomised**, about **200 screened** at 50% prevalence |
| Failed trial (n=1,692, HR 0.89) | simulated power **0.62** |
| Rescue trial (n=1,329, HR 0.74) | simulated power **1.00** |

Below a responder fraction of about 65% an unselected re-run is not
merely underpowered — with `hr_neg` above 1 the biomarker-negative majority is harmed,
so the pooled effect points the wrong way and no sample size rescues it.

**What is assumption and what is data.** The hazard ratios and trial sizes come from
module 1 and are observed. The control-arm event rate is human-supplied
(5.8 months — IPASS NCT00322452 posted control-arm (carboplatin/paclitaxel) median PFS, 5.8 months),
as are exponential survival, no dropout and a perfect assay. All are listed in
`assumptions.notes` in the output. Hazard ratios are never converted into response
probabilities, and no probability that a rescue will succeed is produced.

## Worked cases with known outcomes

The pipeline is demonstrated on two assets that both **failed an unselected trial,
both showed a biomarker-positive subgroup near HR 0.4-0.5 with the negative subgroup
above 1, and both were retried in a biomarker-enriched population.** One was
approved; the other was stopped for futility with the drug arm numerically worse.

| | gefitinib | onartuzumab |
|---|---|---|
| target | EGFR | MET |
| failed trial | ISEL, n=1,692 | phase 2 OAM4558g, n=137 |
| pre-retry subgroup signal | ISEL never-smokers OS 0.67 (0.49-0.92) | MET IHC+ OS **0.37** (no CI), PFS 0.53 (0.28-0.99) |
| retry | IPASS, n=1,329 | METLung, n=499, MET IHC+ only |
| retry result | EGFR mut+ PFS **0.48** (0.36-0.64) | ITT OS **1.27** (0.98-1.65) |
| outcome | approved 2015 | futility, never approved |
| motivating signal | prespecified / mechanistic | post-hoc subgroup |
| biomarker class | somatic driver mutation | protein expression (MET IHC) |
| assay cutoff chosen on outcome | no (discrete genotype) | **yes** |

**The effect size did not distinguish them.** Onartuzumab's pre-retry subgroup
hazard ratio was *better* than gefitinib's. What differed was provenance, which is
what module 4 tiers on.

`retrospective_check` quantifies the failure. If MET IHC+ OS HR 0.37 were
the truth, METLung at n=499 would have returned a ratio in
**[0.285, 0.467]**. It returned **1.27** —
outside the entire simulated distribution. Verdict: `did_not_replicate`.

For gefitinib the same check returns `not_an_independent_test`, and that is the
correct answer rather than a convenient one: IPASS *measured* the EGFR effect in a
prespecified analysis with both strata present, so agreement carries no predictive
information. The asymmetry is the lesson — trust an effect measured with both strata
in the trial you are reading, distrust one carried over from a small subgroup with a
cutoff tuned on its own outcome.

```bash
make cases     # module1-offline -> module4 -> both cases -> comparison figure (no network)
```

## Is the ranking principle actually predictive?

Module 4 tiers strategies by evidence provenance and explicitly not by reported
effect size. `module4/benchmark.py` tests that claim against all
40 curated failed-trial/retry pairs:

| | prespecified / mechanistic | post-hoc subgroup | Fisher p |
|---|---|---|---|
| all decided pairs (n=38) | 13/22 = **59%** | 3/16 = **19%** | 0.020 |
| EGFR cluster removed (n=34) | 10/19 = **53%** | 2/15 = **13%** | 0.030 |

Module 3's genomic-regime verdict lost its outcome signal once the four EGFR-mutant
NSCLC pairs were removed (p 0.015 -> 0.39). This contrast **strengthens**
(OR 6.259 -> 7.222), so it is evidence about rescue attempts in general
rather than about one biology.

The biomarker-class breakdown points the same way: somatic driver mutations went
4/4, while protein-expression markers (onartuzumab, tivantinib, vintafolide) went
0/3.

Counts are small, the rates have wide intervals, and the provenance labels were
assigned with outcomes visible in the same CSV. All three caveats travel with the
output in `caveats`.

## Adding a new asset

1. Copy `config/assets/gefitinib.yaml`, fill in trial IDs, target, biomarker gene, PMIDs.
2. Create `data/curated/<asset>_effects.csv` (HR, CI, p, n, PMID, NCT, analysis_type) and `<asset>_regulatory_timeline.csv`.
3. `make module1 ASSET=config/assets/<asset>.yaml`. Provenance flags tell you which numbers still need checking.

The diagnosis rules assume a failed trial + a later enriched trial exist. For an asset with only the failed trial,
the rules still run; `qualitative_interaction_in_rescue_trial` will not fire and the mode degrades to
`population_dilution_suspected` or `efficacy_failure_no_heterogeneity_signal`.

## Repository layout

```
config/assets/          one YAML per asset
data/curated/           hand-curated effect estimates + regulatory timelines (with provenance)
data/raw/               API pulls (gitignored; regenerated by `make module1`)
src/trial_salvage/
  ctgov.py, pubmed.py   shared API clients
  module1/              eligibility.py · effects.py · failure_analysis.py · figures.py · report.py · run.py
  module2/              cases.py · scoring.py · evaluate.py · analogs.py · tiling.py · stats.py · run.py
  module3/              stub with the input/output contract in the docstring
schemas/                JSON schema for module outputs
tests/                  unit tests (offline)
docs/                   narrative write-ups
.github/workflows/      lint + tests on 3.11/3.13; live module-1 smoke run
```

## Data sources
ClinicalTrials.gov v2 API · PubMed E-utilities · curated from Thatcher 2005 (PMID 16257339), Hirsch 2006 (17075123),
Mok 2009 (19692680), Fukuoka 2011 (21670455), Kazandjian 2016 FDA approval summary (26980062).
Upstream landscape survey (which assets are worth this treatment) is described in `docs/landscape_survey.md`.

## License
MIT
