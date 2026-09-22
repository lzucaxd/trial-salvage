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
