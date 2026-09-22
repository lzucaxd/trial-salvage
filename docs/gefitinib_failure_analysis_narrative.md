# Gefitinib — Module 1: Clinical evidence and failure analysis

**Asset:** gefitinib (ZD1839, Iressa; AstraZeneca) · **Target:** EGFR tyrosine kinase · 
**Indication:** advanced non-small-cell lung cancer (NSCLC) · 
**Failed trial:** ISEL, NCT00242801 · **Rescue trial:** IPASS, NCT00322452

Sources retrieved this session: ClinicalTrials.gov v2 records (both trials; all 390 
interventional gefitinib trials), PubMed abstracts PMID 16257339, 17075123, 19692680, 
21670455, 12748244, 19027483, 15118073, 15118125. Every hazard ratio below is copied 
from those abstracts and tabulated in `gefitinib_effect_estimates.csv`.

---

## 1. What failed, and how

**ISEL (Iressa Survival Evaluation in Lung cancer)** — double-blind, placebo-controlled 
Phase 3; 1,692 patients with locally advanced/metastatic NSCLC refractory to or 
intolerant of their last chemotherapy; 2:1 randomisation to gefitinib 250 mg/day + BSC 
vs placebo + BSC; started 2003-07, completed 2005-04. **Primary endpoint: overall 
survival** in (co-primary) the overall population and the adenocarcinoma subset.

| Population | n | Median OS, gef vs placebo | HR (95% CI) | p |
|---|---|---|---|---|
| Overall | 1,692 | 5.6 vs 5.1 mo | 0.89 (0.77–1.02) | 0.087 |
| Adenocarcinoma (co-primary) | 812 | 6.3 vs 5.4 mo | 0.84 (0.68–1.03) | 0.089 |

Both co-primary analyses missed. Eligibility (registry text) required only confirmed 
NSCLC of any histology, WHO PS 0–3, and "not suitable for chemotherapy" — **no 
molecular selection of any kind.**

Registry data status: ISEL predates FDAAA; **no results are posted on 
ClinicalTrials.gov** and the record links no publications. Its outcome data exist 
only in the literature (Thatcher et al., Lancet 2005; Hirsch et al., JCO 2006).

## 2. Signals inside the failed trial

The salvage hypothesis did not have to be invented after ISEL — it was visible in 
ISEL's own pre-specified subgroups and in its retrospective biomarker analysis:

| Subgroup (ISEL) | n | HR for OS | p | Status |
|---|---|---|---|---|
| Never-smokers | 375 | 0.67 (0.49–0.92) | 0.012 | prespecified |
| Asian origin | 342 | 0.66 (0.48–0.91) | 0.010 | prespecified |
| EGFR high gene copy number (FISH) | 370 tested | 0.61 vs 1.16 for low | interaction 0.045 | retrospective |
| EGFR protein positive (IHC) | 379 tested | 0.77 vs 1.57 for negative | interaction 0.049 | retrospective |
| EGFR mutation-positive | 215 tested | response rate 37.5% vs 2.6% | — | too few for survival |

The Lancet abstract itself concludes there was "pronounced heterogeneity" with 
"some evidence of benefit among never-smokers and patients of Asian origin." The 
mechanistic explanation arrived in parallel: Lynch et al. (NEJM 2004) and Paez et al. 
(Science 2004) showed that activating EGFR kinase-domain mutations (exon 19 deletions, 
L858R) confer sensitivity to gefitinib and are enriched in never-smokers, women, 
adenocarcinoma and East-Asian patients — exactly ISEL's benefiting subgroups.

**Failure diagnosis:** not a drug that does not work, but a drug tested in a 
population where the responsive fraction (EGFR-mutant, ~10–15% in Western, 
30–50% in East-Asian adenocarcinoma cohorts — module-3 numbers, to be verified 
against gnomAD/cBioPortal) was too small to move the ITT survival curve. Dilution, 
not inactivity. Note the biomarker tissue rate: only 215/1,692 (13%) had mutation 
data — the trial was not designed to answer the question it ended up raising.

## 3. The rescue trial

**IPASS (Iressa Pan-Asia Study)** — open-label Phase 3, first-line gefitinib vs 
carboplatin/paclitaxel; 1,217 randomised (1,329 enrolled); started 2006-03; East 
Asia. **Primary endpoint changed to progression-free survival** (non-inferiority, 
then superiority).

**Enrichment was clinical, not molecular.** Eligibility (registry text): stage IIIB/IV 
**adenocarcinoma**, **never-smokers or light ex-smokers** (≤10 pack-years, quit 
≥15 years), chemotherapy-naïve. EGFR mutation status was *not* an entry criterion; 
it was a pre-planned biomarker analysis on the 437 patients (36%) with evaluable 
tissue, of whom 261 (60%) were mutation-positive — roughly a four- to five-fold 
enrichment over an unselected Western population.

| Population (IPASS) | n | Endpoint | HR (95% CI) | p |
|---|---|---|---|---|
| ITT | 1,217 | PFS | 0.74 (0.65–0.85) | <0.001 |
| **EGFR mutation-positive** | 261 | PFS | **0.48 (0.36–0.64)** | <0.001 |
| **EGFR mutation-negative** | 176 | PFS | **2.85 (2.05–3.98)** | <0.001 |
| ITT | 1,217 | OS (final) | 0.90 (0.79–1.02) | 0.109 |
| Mutation-positive | — | OS | 1.00 (0.76–1.33) | 0.99 |
| Mutation-negative | — | OS | 1.18 (0.86–1.63) | 0.31 |

Two lessons that generalise beyond gefitinib:

1. **A qualitative interaction.** Mutation-negative patients were actively harmed 
   relative to chemotherapy (HR 2.85). In an unselected population these two effects 
   cancel — which is precisely the ISEL result. The ITT PFS "win" (HR 0.74) was 
   itself an artefact of the mix: the registry posting shows median PFS 5.7 vs 5.8 
   months, near-identical, with the curves crossing. **The registry aggregate hides 
   the biomarker effect entirely** — the HR by mutation status exists only in the 
   publication.
2. **OS is the wrong endpoint once crossover is allowed.** 64% of mutation-positive 
   patients on chemotherapy subsequently received an EGFR TKI; OS HR in that subgroup 
   is 1.00. The endpoint switch to PFS was not cosmetic — it was necessary to observe 
   the effect at all.

Also in the family: IDEAL-1 (Phase 2, PMID 12748244) that supported the 2003 
accelerated approval, and INTEREST (NCT00076388, n=1,440; PMID 19027483) showing 
non-inferiority to docetaxel in an unselected second-line population (OS HR 1.02), 
i.e. active but no better than chemotherapy without selection.

## 4. What the gefitinib trial family shows about the pivot

From all 390 interventional gefitinib trials on ClinicalTrials.gov (231 in NSCLC, 
59 Phase 3, 49 with posted results), eligibility text was scanned for a requirement 
of an EGFR mutation:

| Start years | NSCLC gefitinib trials | EGFR mutation required |
|---|---|---|
| 2000–2005 | 53 | **0** |
| 2005–2008 | 32 | 3 |
| 2009–2012 | 54 | 23 |
| 2013–2016 | 57 | 26 |
| 2017–2020 | 39 | 27 |
| 2015+ (all) | 73 | 45 (62%) |

After IPASS the drug's development programme re-formed around the biomarker; post-
2013 Phase 3 trials use gefitinib almost exclusively as the *comparator arm* for 
next-generation EGFR TKIs (osimertinib FLAURA NCT02296125, dacomitinib ARCHER1050 
NCT01774721, lazertinib NCT04248829, and others) in EGFR-mutant populations — the 
clearest possible sign that the rescued indication became standard of care.

Regulatory trajectory (sourced: FDA approval summary PMID 26980062; FDA NDA 206995 review): US accelerated approval 2003-05-05 on IDEAL response 
rates → label restricted 2005-06-17 after ISEL → EU approval 2009-06-24 restricted to 
EGFR-mutation-positive disease → NDA withdrawn 2012-04-25 → US approval 2015-07-13 for first-line EGFR 
exon 19 deletion / L858R NSCLC, on IPASS plus the single-arm IFUM study.

## 5. Salvage-strategy map (what this case tells module 4)

| Strategy | Was it used for gefitinib? | Evidence |
|---|---|---|
| **New inclusion criteria (biomarker enrichment)** | **Yes — the rescue** | ISEL subgroups → IPASS mutation subgroup HR 0.48 vs 2.85 |
| Clinical-surrogate enrichment before a validated assay | Yes, as a bridge | IPASS enrolled on histology + smoking + geography; assay confirmed afterwards |
| **New endpoint** | **Yes** | OS → PFS, because crossover nullifies OS |
| New line of therapy | Yes | 2nd/3rd-line refractory (ISEL) → first-line (IPASS) |
| Narrower indication | Yes | NSCLC → EGFR-mutant NSCLC adenocarcinoma |
| Molecule modification | Not for gefitinib itself; the class evolved | 2nd/3rd-gen TKIs (afatinib, osimertinib) address T790M resistance — a module-2 question |
| Geographic re-scoping | Yes, transiently | Asia-first development reflected mutation prevalence, not ethnicity per se |

## 6. Inputs handed to modules 2–4

- **Module 2 (protein variants / ESM):** target EGFR (UniProt P00533). Sensitising 
  variants: exon 19 in-frame deletions (E746–A750 most common), L858R; primary 
  resistance: exon 20 insertions; acquired: T790M, C797S. Question: can a 
  sequence/structure model recover the sensitivity ranking of these variants for 
  gefitinib without the clinical data?
- **Module 3 (genomic stratification / AlphaGenome):** EGFR mutation prevalence by 
  ancestry and histology (cBioPortal NSCLC cohorts; gnomAD for germline context); 
  the ISEL never-smoker/Asian subgroups as the clinical proxy the genomic model 
  should out-perform.
- **Module 4 (trial simulation):** ISEL-like population with responder fraction f 
  and subgroup HRs 0.48 / 2.85 (PFS) or 0.66 / ~1.1 (OS proxy from ISEL Asian vs 
  rest). Sweep f from 0.10 to 0.60 to reproduce the ISEL miss and the IPASS win, and 
  compute the enrichment threshold at which an unselected trial would have succeeded.

## Files

- `gefitinib_effect_estimates.csv` — 16 effect estimates with PMID/NCT provenance
- `gefitinib_trial_family.csv` — all 390 gefitinib trials with EGFR-selection flags
- `gefitinib_anchor_trials_raw.json` — full CT.gov records (ISEL, IPASS incl. results section)
- `gefitinib_pubmed_abstracts.json` — the eight landmark abstracts
- `fig2_gefitinib_isel_ipass.png` — forest plot + selection-adoption timeline
