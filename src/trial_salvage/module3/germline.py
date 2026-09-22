"""Germline variation summaries and the stratification-risk score (pure functions, no network).

Score = tolerance x burden
  tolerance = clip(LOEUF, 0, 2) / 2           -- does the gene tolerate loss-of-function variation at all?
  burden    = log1p(n_common_func) / log1p(max over the gene set)   -- is there common protein-altering variation?
Both terms are needed: constrained genes (low LOEUF) have little variation because it is purged; tolerant genes
with no common functional variants have nothing to stratify on.

Validation (Sep 2026, 24-gene panel): 5 of the top 7 were CPIC pharmacogenes, constrained controls at the bottom.
The separation is driven by LOEUF, not by raw variant counts -- check LOEUF alone before trusting the product.

Caveat from the rescue benchmark (data/benchmark): retries that stratified on *common* germline variants were 0/2,
while somatic drivers were 4/4 and germline monogenic 2/3. A high score here marks common-variant tractability,
which the benchmark does not yet support as a rescue lever. Report it alongside the somatic lane, not instead of it.

v1 (``stratification_scores_v1``, see docs/module3_normalization.md): the v0 burden grows with gene size, so the
largest genes on the failed-trial list (MUC16, MUC5AC) topped it. v1 keeps the tolerance term and replaces burden by
a size/mutability-normalised rate
  rate   = n_common_func / exp_syn     -- common functional variants per expected synonymous variant (gnomAD
                                          mutation model: sequence length x mutability, blind to selection)
  burden = rate / max(rate over the set)   -- the max only rescales; ranks do not depend on the set
  score  = tolerance x burden
plus a sequence-quality gate: genes whose observed synonymous count exceeds expectation (oe_syn = obs_syn / exp_syn
> SYN_EXCESS_OE) are flagged ``qc_syn_excess`` and ranked after every unflagged gene. Synonymous sites are close to
neutral, so an excess there points to calling artefacts (tandem repeats, paralogous mapping), not biology.
Normalisation alone removes MUC16 from the top 10; MUC5AC is removed only by the gate (oe_syn 1.60).

Constraint-reliability flag (``flag_low_exp_lof``): LOEUF is an upper confidence bound on obs/exp LoF, so it is
uninformative when few LoF variants are expected (SSTR5: LOEUF 14.1 on exp_lof 0.34). Genes with
exp_lof < LOW_EXP_LOF are flagged ``low_exp_lof``; they keep their score but rank after every unflagged gene.
"""
from __future__ import annotations

import math

FUNCTIONAL = frozenset({"missense_variant", "stop_gained", "frameshift_variant", "splice_acceptor_variant",
                        "splice_donor_variant", "start_lost", "stop_lost", "inframe_insertion",
                        "inframe_deletion", "transcript_ablation"})
LOSS_OF_FUNCTION = frozenset({"stop_gained", "frameshift_variant", "splice_acceptor_variant",
                              "splice_donor_variant", "start_lost", "transcript_ablation"})
COMMON_MAF = 0.01


def maf(ac: int, an: int) -> float | None:
    """Minor allele frequency. Folding matters: some 'common' variants are a minor *reference* allele."""
    if not an:
        return None
    af = ac / an
    return min(af, 1.0 - af)


def summarize_variants(symbol: str, variants: list[dict], threshold: float = COMMON_MAF) -> dict:
    n = n_common = n_func = n_lof = 0
    cum = 0.0
    for v in variants:
        j = v.get("joint") or {}
        m = maf(j.get("ac") or 0, j.get("an") or 0)
        if m is None:
            continue
        n += 1
        if m <= threshold:
            continue
        n_common += 1
        csq = v.get("consequence")
        if csq in FUNCTIONAL:
            n_func += 1
            cum += m
        if csq in LOSS_OF_FUNCTION:
            n_lof += 1
    return {"symbol": symbol, "n_variants": n, "n_common": n_common, "n_common_func": n_func,
            "n_common_lof": n_lof, "cum_maf_func": round(cum, 4)}


def stratification_scores(rows: list[dict]) -> list[dict]:
    """Add tolerance, burden and score to rows carrying LOEUF + n_common_func. Rows without LOEUF get None."""
    counts = [r["n_common_func"] for r in rows if r.get("n_common_func") is not None]
    denom = math.log1p(max(counts)) if counts and max(counts) > 0 else None
    out = []
    for r in rows:
        r = dict(r)
        loeuf, k = r.get("LOEUF"), r.get("n_common_func")
        if loeuf is None or k is None or denom is None:
            r.update(tolerance=None, burden=None, score=None)
        else:
            r["tolerance"] = min(max(loeuf, 0.0), 2.0) / 2.0
            r["burden"] = math.log1p(k) / denom
            r["score"] = round(r["tolerance"] * r["burden"], 3)
        out.append(r)
    return out


SYN_EXCESS_OE = 1.35  # highest CPIC pharmacogene on the panel is CYP2C9 at 1.29 -- keep that margin in mind


def _num(x) -> float | None:
    """float or None; NaN / empty / non-numeric become None."""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else f


def stratification_scores_v1(rows: list[dict], syn_excess: float = SYN_EXCESS_OE) -> list[dict]:
    """Length-normalised germline score. Needs LOEUF, n_common_func, exp_syn; uses exp_mis and obs_syn if present.

    Adds: rate_syn (n_common_func / exp_syn), rate_mis (n_common_func / exp_mis, informational), oe_syn,
    qc_syn_excess (True / False, None when obs_syn is missing), tolerance, burden_v1, score_v1 and rank_v1.
    Rows lacking LOEUF, n_common_func or a positive exp_syn get None scores and are ranked last.
    """
    out = []
    for r in rows:
        r = dict(r)
        loeuf, k = _num(r.get("LOEUF")), _num(r.get("n_common_func"))
        es, em, os_ = _num(r.get("exp_syn")), _num(r.get("exp_mis")), _num(r.get("obs_syn"))
        r["rate_syn"] = k / es if k is not None and es else None
        r["rate_mis"] = k / em if k is not None and em else None
        r["oe_syn"] = os_ / es if os_ is not None and es else None
        r["qc_syn_excess"] = None if r["oe_syn"] is None else r["oe_syn"] > syn_excess
        r["tolerance"] = None if loeuf is None else min(max(loeuf, 0.0), 2.0) / 2.0
        out.append(r)
    rates = [r["rate_syn"] for r in out if r["rate_syn"] is not None and r["tolerance"] is not None]
    top = max(rates) if rates and max(rates) > 0 else None
    for r in out:
        if r["rate_syn"] is None or r["tolerance"] is None:
            r["burden_v1"] = r["score_v1"] = None
        else:
            r["burden_v1"] = r["rate_syn"] / top if top else 0.0
            r["score_v1"] = round(r["tolerance"] * r["burden_v1"], 4)
    for i, r in enumerate(sorted(out, key=_rank_key), start=1):
        r["rank_v1"] = i
    return out


LOW_EXP_LOF = 10.0  # expected LoF variants below which LOEUF is too noisy to trust (gnomAD guidance)


def flag_low_exp_lof(rows: list[dict], threshold: float = LOW_EXP_LOF) -> list[dict]:
    """Add ``low_exp_lof`` = exp_lof < threshold (None when exp_lof is missing). Apply before stratification_scores_v1,
    which ranks flagged genes after all unflagged ones without changing their score."""
    out = []
    for r in rows:
        e = _num(r.get("exp_lof"))
        out.append({**r, "low_exp_lof": None if e is None else e < threshold})
    return out


def _rank_key(r: dict) -> tuple:
    """Scored + QC-pass first, then qc_syn_excess, then low_exp_lof (any), then unscored; score descending, symbol
    breaks ties. Rows without a ``low_exp_lof`` key are treated as unflagged."""
    s = r.get("score_v1")
    if s is None:
        tier = 3
    elif r.get("low_exp_lof"):
        tier = 2
    elif r.get("qc_syn_excess"):
        tier = 1
    else:
        tier = 0
    return tier, -(s or 0.0), str(r.get("symbol"))
