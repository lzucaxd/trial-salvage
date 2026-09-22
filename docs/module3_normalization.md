# Module 3 — normalising the germline burden term (v1)

**Problem.** v0 `score = tolerance x log1p(n_common_func)/log1p(max)` rewards gene size: MUC5AC (87 common functional
variants) and MUC16 (135) ranked 1-2 of 182 failed-trial targets. **Data.** gnomAD v4 constraint re-fetched with obs/exp
missense + synonymous counts for all 182 targets and the 24-gene panel (`data/candidates/target_gnomad_constraint_v1.csv`,
`data/module3/pharmacogene_constraint_v1.csv`; LOEUF identical to v0, 5 targets lack constraint). Variant counts reused
from v0, not re-fetched. Every variant keeps `tolerance = clip(LOEUF,0,2)/2`; k = n_common_func.

| burden term (x tolerance) | (a) PGx in top 7 /8 | (a) median PGx rank /24 | (b) MUC5AC /182 | (b) MUC16 | rho(burden, exp_syn), k>0 |
|---|---|---|---|---|---|
| v0 log1p(k)/log1p(max) | 5 | 6.5 | 1 | 2 | -0.09 |
| LOEUF alone (ablation, no burden) | 5 | **4.5** | 39 | 69 | -0.35 |
| k / exp_mis | 5 | 6.0 | 1 | 14 | -0.46 |
| k / exp_syn | **6** | 5.5 | 1 | 14 | -0.48 |
| log1p(100 k / exp_mis) | 5 | 6.0 | 1 | 15 | -0.46 |
| log1p(100 k / exp_syn) | 5 | 5.5 | 1 | 16 | -0.47 |
| log1p(k) / log1p(exp_mis) | 5 | 6.5 | 1 | 6 | -0.19 |
| **v1 = k / exp_syn + oe_syn > 1.35 gate** | **6** | **5.5** | **173** | **12** | -0.48 |

Also rejected: Poisson 90 % lower bound of k/exp (PGx 3-5/7, MUC16 5-9); shrunk rates (MUC16 7-10). Controls rank >= 12/24.

**Findings.** (1) Per-expected normalisation fixes MUC16 (2 -> 14): its burden was length. (2) No normalisation moves
MUC5AC. Its exp_syn (1237) is ordinary; what is extreme is *observed* synonymous excess, oe_syn = 1.60 (2nd of 182).
Synonymous sites are near-neutral, so this suggests calling artefacts in repeats. A gate at oe_syn > 1.35 flags 4
targets (MUC5AC, DRD4 [exon-3 VNTR], HSP90AA1, TSLP) and 0 panel genes. (3) On the panel no candidate beats LOEUF alone
on median rank; k/exp_syn beats v0 by one gene (NUDT15, TPMT in; DPYD out), within noise for 8 PGx genes.

**Choice: v1 = tolerance x (k/exp_syn)/max + synonymous-excess gate** (`germline.stratification_scores_v1`). The only
candidate at least as good as v0 on both checks (a: 6/7, median 5.5 vs 5/7, 6.5; b: both mucins leave the top 10).
Linear, not log: ranks do not depend on the set or on a scale constant (log variants shift between 100 and 1000).
exp_syn, not exp_mis: neutral mutability x length, >= on both checks (by one gene). LOEUF alone wins (a) but ignores
whether any common functional variant exists: 6 of its top 15 targets (e.g. DNMT3A) have k = 0, nothing to stratify on.

**v1 top 15:** HTR3D, P2RX7, ADRA1A, CALCA, OPRM1, MTNR1B, HRH4, LTA, MTNR1A, MYL7, ADORA3, MUC16, HTR3C, AR, S1PR3.
CLI: `python -m trial_salvage.module3.score_targets --in RAW.csv --out SCORED.csv` (symbol, LOEUF, exp_mis, exp_syn,
n_common_func required; obs_syn enables the gate; other columns pass through).

**Caveats.** Over-correction: rho(burden, exp_syn) moves from -0.09 to -0.48, so small genes with 1-2 common variants
(CALCA k=2, MYL7 k=1) rank high. The 1.35 gate is post hoc with a thin margin (CYP2C9 1.29) and demotes DRD4, whose
VNTR is a studied pharmacogenetic marker. Benchmark caveat stands: common germline variants were 0/2 as a rescue lever.
