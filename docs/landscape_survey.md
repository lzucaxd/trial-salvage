# Failed-trial salvage landscape — what public data is obtainable

Survey pass, 2026-09-22. Sources: ClinicalTrials.gov v2 API (full census), ChEMBL 
(molecule / mechanism), Open Targets Platform (target genetics). No internal data 
used. All counts below are reproducible from the accompanying CSV/parquet files.

## 1. Census

| Cohort | n |
|---|---|
| Interventional Phase 2, 2/3 or 3 trials of a drug or biological, started ≥ 2007 | **96,827** |
| Completed | 46,434 (53% have results posted; 63% for industry-sponsored) |
| Discontinued (terminated / withdrawn / suspended) | **14,627** |
| Still active or recruiting | 23,381 |
| Status unknown (registry never updated) | 12,385 |

The 2007 floor is the FDAAA effective date, after which results reporting became 
mandatory for applicable US trials — the window where posted results are realistic.

## 2. Why trials were discontinued

Stop reasons were classified from the registry's free-text `WhyStopped` field 
(regex rules, then an LLM pass on the 2,841 residual strings; 591 remain unclear).

| Reason | Trials | Industry share | Results posted or publication linked |
|---|---|---|---|
| Enrollment / accrual | 4,215 | 24% | 45% |
| Business / strategic | 3,279 | 61% | 40% |
| **Efficacy / futility** | **1,536** | 59% | **62%** |
| Administrative / site / regulatory | 1,439 | 28% | 30% |
| **Safety** | **1,411** | 75% | **63%** |
| Not stated | 1,342 | 61% | 33% |
| Unclear text | 591 | 50% | 36% |
| COVID-19 disruption | 452 | 35% | 43% |
| Drug supply / manufacturing | 362 | 16% | 41% |

Interpretation:
- Only ~20% of discontinuations are *scientific* failures (efficacy or safety); 
  these ~2,950 trials enrolled ~612,000 participants and are 60% industry-sponsored.
- Scientific failures are the **best-documented** subgroup — roughly 62% have 
  outcome data on the registry or a linked publication, versus 30–45% elsewhere.
- "Business / strategic" (3,279 trials, 61% industry) is a known euphemism bucket. 
  A material fraction are undeclared efficacy misses; the asset-level inventory 
  retains these trials so they can be re-examined per candidate.
- **Completed-but-negative trials are not in this table.** A Phase 3 that ran to 
  completion and missed its primary endpoint is `COMPLETED` in the registry. 
  Detecting those requires parsing posted results (p-values / effect estimates) — 
  a follow-on step; the census parquet has `has_results` flags for the 24,645 
  completed trials where this is possible.

## 3. Data-availability tiers (what you can actually get)

| Tier | Meaning | Discontinued trials |
|---|---|---|
| T1 | Aggregate results posted on ClinicalTrials.gov (baseline, arm-level outcomes, AEs) | 6,231 |
| T2 | No posting, but a results publication is linked (PMID) | 214 |
| T3 | Only an IPD-sharing statement of "YES" | 574 |
| T4 | Registration record only | 7,608 |

Participant-level data (IPD) is never directly downloadable. 1,654 discontinued 
trials state IPD sharing = YES; access runs through sponsor platforms (Vivli, 
CSDR, YODA, sponsor portals) with a research proposal and typically 3–6 months 
lead time. This is the only route to a genuine post-hoc stratification analysis.

## 4. Asset-level inventory

Rolling trials up to molecules (industry-sponsored, efficacy- or safety-stopped):

| Funnel stage | Assets |
|---|---|
| Distinct intervention names in industry efficacy/safety failures | 2,084 |
| Resolved to a ChEMBL molecule | 1,105 |
| — of which approved drugs (max phase 4) appearing in a failed trial (often as combination backbone, or a new-indication attempt) | 490 |
| — of which **unapproved** (max phase 1–3) | **615** |
| Unapproved, still in an active trial somewhere | 127 |
| **Unapproved, no active trials anywhere (shelved)** | **488** |
| Shelved + mapped target + ≥1 trial with posted results | **238** |
| … and the target carries human genetic-association evidence (Open Targets) | 184 |

The 238-asset shortlist (`salvage_shortlist_unapproved_no_active.csv`) is the 
working set for salvage triage: 136 small molecules (SMILES available for 
structure-modification work), 102 biologics/other; 114 reached Phase 3. 
Failure mode split: 119 efficacy, 108 safety, 11 both.

Examples near the top by evidence richness: enzastaurin (PRKCB, 23 trials), 
bardoxolone methyl (KEAP1/NFE2L2, 15 trials, efficacy + safety), tivantinib (MET), 
TAK-875 / fasiglifam (FFAR1, hepatotoxicity), idasanutlin (MDM2), soticlestat 
(CYP46A1), brensocatib (CTSC), GDC-0853 / fenebrutinib (BTK).

Coverage caveats:
- 979 of 2,084 names did not resolve in ChEMBL. Inspection shows these are 
  mostly compound arm descriptions ("study drug + carboplatin"), sponsor codes not 
  yet in ChEMBL, and vaccines/cell products. Manual curation of the highest-trial-
  count residuals would recover more.
- `max_phase` is from ChEMBL and lags real-world approvals by months; 
  `n_active > 0` is from the registry and is current.
- Open Targets "genetic evidence" here means: at least one of the target's top-8 
  associated diseases has a non-zero genetic_association datatype score. It 
  flags targets with *any* human genetics, not genetics for the failed indication 
  specifically — per-candidate work is needed to check indication alignment.

## 5. Implications for the salvage questions

| Question | What the public layer supports | What needs more |
|---|---|---|
| Abandon vs. salvage? | Failure mode (efficacy vs. safety), phase reached, whether anyone else is still developing it, whether the same target has other failures (mechanism-wide vs. molecule-specific) | Reading the actual results posting / CSR for effect size and subgroup signals |
| New inclusion criteria / population stratification? | Target genetics from Open Targets; pharmacogenomic records (rare: 4 of 579 assets) | IPD via Vivli/YODA; population allele frequencies (gnomAD) for the target and metabolizing enzymes |
| Modify the molecule? | SMILES for 365 unapproved assets; mechanism and target for 386 | Structure-based work (ESM/Boltz co-folding, SAR from ChEMBL bioactivities) |
| New endpoint? | Registered primary/secondary outcome list per trial; posted secondary outcomes | Statistical re-analysis on IPD |
| New / narrower indication? | Target-disease association scores across all diseases; sibling trials of the same asset in other indications | Indication-specific genetics and unmet-need assessment |

## 6. Recommended next step

Pick 3–5 candidates from the shortlist and run the per-asset deep dive: pull the 
posted results modules (arm-level outcomes and AEs), sibling trials in other 
indications, ChEMBL bioactivity/SAR, Open Targets genetics for the failed 
indication specifically, and file IPD requests where sharing is offered. The 
funnel columns in the inventory (`evidence_score`, `genetic_flag`, `n_fail_trials`, 
`fail_reasons`) are designed for that selection.

## Files

- `failed_asset_inventory.csv` — 2,084 assets with ChEMBL, mechanism, Open Targets and trial-count columns
- `salvage_shortlist_unapproved_no_active.csv` — the 238-asset working set
- `discontinued_trials_classified.csv` — 14,627 discontinued trials with stop-reason class and data tier
- `ctgov_phase23_drug_2007plus_classified.parquet` — full 96,827-trial census
- `chembl_asset_enrichment.parquet`, `chembl_mechanisms.parquet`, `opentargets_enrichment.parquet` — raw enrichment pulls
- `summary_numbers.json` — every number quoted above
