"""Test the Module 3 lane verdict against the rescue benchmark (data/benchmark/rescue_benchmark_v0.csv).

Question: for each failed-trial/retry pair, does Module 3 -- given only the drug's targets -- say that stratifiable
population variation exists, and in which regime (somatic tumour driver vs common germline variation)? Then: does
that verdict line up with (a) retry outcome and (b) the regime the retry actually selected on (biomarker_group)?

Pre-registered rule (docs/module3_benchmark_eval.md, committed before outcomes were joined):
  per target:  somatic          if oncology and top recurrent protein change >= SOMATIC_TOP_FREQ of study samples
               germline_common  elif n_common_func >= GERMLINE_MIN_FUNC and LOEUF >= GERMLINE_MIN_LOEUF
               none_detected    otherwise
  per asset :  first lane (in that order) reached by ANY of its targets; unmapped assets / no targets / complexes
               with > MAX_TARGETS targets get 'not_evaluable' and are excluded from the outcome tables.

Network: Open Targets (biodata), gnomAD (paced client below -- the gnomAD rate limit is shared, so >= 20 s between
requests and 65 s sleep on HTTP 429), mygene.info (Entrez ids) and cBioPortal. Every response is cached as JSON
under ``cache_dir`` so a rerun never re-fetches. Everything below the ``# ---- pure`` line is offline.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import time
from pathlib import Path

import pandas as pd
import requests

from trial_salvage import biodata, gnomad
from trial_salvage.module3.germline import summarize_variants

SOMATIC_TOP_FREQ = 0.01
GERMLINE_MIN_FUNC = 3
GERMLINE_MIN_LOEUF = 0.6
MAX_TARGETS = 10
LANE_ORDER = ("somatic", "germline_common", "none_detected")
DECIDED = ("success", "fail")
PAN_CANCER = "msk_impact_2017"
# Indication -> large cBioPortal study (whole-exome where available, so every target gene is profiled).
INDICATION_STUDY = {
    "NSCLC": "nsclc_tcga_broad_2016",
    "ovarian cancer": "ov_tcga_pan_can_atlas_2018",
    "prostate cancer": "prad_su2c_2019",
    "HCC": "lihc_tcga_pan_can_atlas_2018",
    "DLBCL": "dlbcl_duke_2017",
    "melanoma": "skcm_tcga_pan_can_atlas_2018",
}
# Benchmark biomarker_group -> the Module 3 lane that would detect it (None = outside Module 3's scope).
GROUP_TO_LANE = {
    "somatic_driver_mutation": "somatic", "somatic_alteration": "somatic",
    "germline_common_variant": "germline_common", "germline_monogenic": "germline_monogenic",
}
GNOMAD_PAUSE = 20.0
GNOMAD_429_SLEEP = 65.0
GNOMAD_MAX_TRIES = 4
MYGENE = "https://mygene.info/v3/query"


# ---------------------------------------------------------------- cached network clients
class Cache:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, kind: str, key: str) -> Path:
        return self.root / kind / (re.sub(r"[^A-Za-z0-9_.-]", "_", key) + ".json")

    def get(self, kind: str, key: str):
        p = self.path(kind, key)
        return json.loads(p.read_text()) if p.exists() else None

    def put(self, kind: str, key: str, obj) -> None:
        p = self.path(kind, key)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(obj))


class PacedGnomad:
    """gnomAD GraphQL with shared-IP etiquette. Reuses gnomad.py query builders; only pacing/backoff differ."""

    def __init__(self, cache: Cache, pause: float = GNOMAD_PAUSE):
        self.cache, self.pause, self._last = cache, pause, 0.0

    def _post(self, payload: dict, timeout: int = 240) -> dict:
        for _ in range(GNOMAD_MAX_TRIES):
            wait = self.pause - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            r = requests.post(gnomad.API, json=payload, timeout=timeout)
            self._last = time.time()
            if r.status_code == 429:
                time.sleep(GNOMAD_429_SLEEP)
                continue
            return r.json()
        raise RuntimeError("gnomAD rate limit: still 429 after retries")

    def constraint(self, symbols: list[str]) -> dict[str, dict]:
        out = {s: self.cache.get("gnomad_constraint", s) for s in symbols}
        todo = [s for s, v in out.items() if v is None]
        for i in range(0, len(todo), gnomad.MAX_ALIASES):
            chunk = todo[i:i + gnomad.MAX_ALIASES]
            js = self._post({"query": gnomad.constraint_query(chunk)})
            for s, row in parse_constraint(js, chunk).items():
                self.cache.put("gnomad_constraint", s, row)
                out[s] = row
        return out

    def variants(self, symbol: str) -> list[dict]:
        hit = self.cache.get("gnomad_variants", symbol)
        if hit is not None:
            return hit
        js = self._post({"query": gnomad.VARIANTS_QUERY, "variables": {"sym": symbol}})
        if js.get("errors") and not js.get("data"):
            raise RuntimeError(f"gnomAD variants {symbol}: {str(js['errors'])[:200]}")
        g = (js.get("data") or {}).get("gene")
        vs = g["variants"] if g else []
        self.cache.put("gnomad_variants", symbol, vs)
        return vs


def entrez_ids(symbols: list[str], cache: Cache) -> dict[str, int | None]:
    out = {}
    for s in symbols:
        hit = cache.get("entrez", s)
        if hit is None:
            js = requests.get(MYGENE, params={"q": f"symbol:{s}", "species": "human", "fields": "entrezgene,symbol"},
                              timeout=60).json()
            ids = [h.get("entrezgene") for h in js.get("hits", []) if h.get("symbol") == s and h.get("entrezgene")]
            hit = {"symbol": s, "entrez": int(ids[0]) if ids else None}
            cache.put("entrez", s, hit)
        out[s] = hit["entrez"]
    return out


def somatic_raw(study: str, entrez: int, cache: Cache) -> dict:
    key = f"{study}__{entrez}"
    hit = cache.get("cbio", key)
    if hit is None:
        n = cache.get("cbio_n", study)
        if n is None:
            n = biodata.study_sample_count(study)
            cache.put("cbio_n", study, n)
        muts = biodata.somatic_mutations(study, entrez)
        hit = {"study": study, "entrez": entrez, "n_samples": n,
               "mutations": [{"sampleId": m["sampleId"], "proteinChange": m.get("proteinChange")} for m in muts]}
        cache.put("cbio", key, hit)
    return hit


def map_asset(asset: str, cache: Cache) -> dict:
    q = asset_query(asset)
    hit = cache.get("opentargets", q)
    if hit is None:
        h = biodata.search_drug(q)
        rec = biodata.drug_record(h["id"]) if h else None
        hit = {"hit": h, "rec": rec}
        cache.put("opentargets", q, hit)
    return mapping_row(asset, hit["hit"], hit["rec"])


# ---- pure (offline) -----------------------------------------------------------------------------------------
def asset_query(asset: str) -> str:
    """'ocrelizumab (after rituximab)' -> 'ocrelizumab'."""
    return re.sub(r"\s*\(.*?\)", "", str(asset)).strip()


def parse_constraint(js: dict, chunk: list[str]) -> dict[str, dict]:
    data = js.get("data") or {}
    out = {}
    for j, s in enumerate(chunk):
        g = data.get(f"g{j}") or {}
        c = g.get("gnomad_constraint") or {}
        out[s] = {"symbol": s, "gene_id": g.get("gene_id"), "LOEUF": c.get("oe_lof_upper"), "pLI": c.get("pLI"),
                  "mis_z": c.get("mis_z")}
    return out


def mapping_row(asset: str, hit: dict | None, rec: dict | None) -> dict:
    q = asset_query(asset)
    row = {"asset": asset, "ot_query": q, "chembl": (hit or {}).get("id"), "ot_name": (rec or {}).get("name"),
           "drug_type": (rec or {}).get("drugType"), "targets": [], "n_targets": 0}
    if not hit or not rec:
        return {**row, "mapping": "unmapped_no_hit"}
    if not biodata.name_matches(q, rec):
        return {**row, "mapping": "unmapped_name_mismatch"}
    t = biodata.drug_targets(rec)
    row.update(targets=t, n_targets=len(t))
    if not t:
        return {**row, "mapping": "mapped_no_targets"}
    if len(t) > MAX_TARGETS:
        return {**row, "mapping": "complex_target"}
    return {**row, "mapping": "mapped"}


def overlap(bench: pd.DataFrame, cands: pd.DataFrame) -> pd.DataFrame:
    """Benchmark rows whose failed_nct / retry_nct / asset name appears among our verified efficacy failures."""
    names = {biodata._norm(d): d for d in cands.drug}
    rows = []
    for _, b in bench.iterrows():
        for col in ("failed_nct", "retry_nct"):
            m = cands[cands.nct == b[col]]
            for _, c in m.iterrows():
                rows.append({"asset": b.asset, "match": col, "benchmark_nct": b[col], "cand_nct": c.nct,
                             "cand_drug": c.drug, "cand_cond": c.cond})
        qn = biodata._norm(asset_query(b.asset))
        if qn in names:
            for _, c in cands[cands.drug == names[qn]].iterrows():
                rows.append({"asset": b.asset, "match": "asset_name", "benchmark_nct": "",
                             "cand_nct": c.nct, "cand_drug": c.drug, "cand_cond": c.cond})
    return pd.DataFrame(rows, columns=["asset", "match", "benchmark_nct", "cand_nct", "cand_drug", "cand_cond"])


def somatic_summary(raw: dict) -> dict:
    n = raw["n_samples"]
    by: dict[str, set] = {}
    for m in raw["mutations"]:
        if m.get("proteinChange"):
            by.setdefault(m["proteinChange"], set()).add(m["sampleId"])
    top = max(by.items(), key=lambda kv: (len(kv[1]), kv[0]), default=(None, set()))
    any_n = len({m["sampleId"] for m in raw["mutations"]})
    return {"study": raw["study"], "study_n": n, "frac_any_mut": any_n / n if n else None,
            "top_change": top[0], "top_change_n": len(top[1]), "top_change_freq": len(top[1]) / n if n else None}


def target_lane(oncology: bool, top_change_freq: float | None, loeuf: float | None,
                n_common_func: float | None) -> str:
    if oncology and top_change_freq is not None and top_change_freq >= SOMATIC_TOP_FREQ:
        return "somatic"
    if (n_common_func is not None and not _nan(n_common_func) and n_common_func >= GERMLINE_MIN_FUNC
            and loeuf is not None and not _nan(loeuf) and loeuf >= GERMLINE_MIN_LOEUF):
        return "germline_common"
    return "none_detected"


def asset_lane(target_lanes: list[str], mapping: str) -> str:
    if mapping != "mapped" or not target_lanes:
        return "not_evaluable"
    return next(lane for lane in LANE_ORDER if lane in target_lanes)


def regime_match(lane: str, biomarker_group: str) -> str:
    """Does the predicted regime equal the regime the retry selected on?"""
    if lane == "not_evaluable":
        return "not_evaluable"
    expected = GROUP_TO_LANE.get(biomarker_group)
    if expected == "germline_monogenic":
        return "monogenic_not_modelled"
    if expected is None:
        return "retry_not_genomic" if lane == "none_detected" else "lane_without_genomic_retry"
    return "match" if lane == expected else "miss"


def crosstab(df: pd.DataFrame, row: str, col: str) -> pd.DataFrame:
    t = pd.crosstab(df[row], df[col], margins=True, margins_name="n")
    return t


def fisher_2x2(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher exact p for [[a, b], [c, d]] (no scipy dependency)."""
    n1, n2, k, n = a + b, c + d, a + c, a + b + c + d

    def p(x: int) -> float:
        return math.comb(n1, x) * math.comb(n2, k - x) / math.comb(n, k)

    obs = p(a)
    lo, hi = max(0, k - n2), min(k, n1)
    return min(1.0, sum(p(x) for x in range(lo, hi + 1) if p(x) <= obs * (1 + 1e-9)))


def evaluation(pairs: pd.DataFrame) -> dict:
    """Tables (a) lane x outcome, (b) lane x biomarker_group, (c) (a) without the EGFR-mutant NSCLC cluster.

    Descriptive; Fisher p compares somatic vs any other evaluable lane for success.
    """
    dec = pairs[pairs.outcome.isin(DECIDED)]
    ev = dec[dec.lane_verdict != "not_evaluable"]
    no_egfr = ev[ev.same_driver_cluster.isna() | (ev.same_driver_cluster == "")]
    out = {"n_pairs": len(pairs), "n_decided": len(dec), "n_evaluable": len(ev),
           "excluded_undecided": pairs[~pairs.outcome.isin(DECIDED)][["asset", "outcome", "lane_verdict"]],
           "not_evaluable": dec[dec.lane_verdict == "not_evaluable"][["asset", "mapping", "outcome"]],
           "a": crosstab(ev, "lane_verdict", "outcome"), "b": crosstab(ev, "biomarker_group", "lane_verdict"),
           "b_match": crosstab(ev, "regime_match", "outcome"), "c": crosstab(no_egfr, "lane_verdict", "outcome"),
           "n_c": len(no_egfr)}
    for key, d in (("p_a", ev), ("p_c", no_egfr)):
        som = d.lane_verdict == "somatic"
        suc = d.outcome == "success"
        out[key] = fisher_2x2(int((som & suc).sum()), int((som & ~suc).sum()),
                              int((~som & suc).sum()), int((~som & ~suc).sum()))
    genomic = ev.biomarker_group.map(GROUP_TO_LANE) == "somatic"
    som = ev.lane_verdict == "somatic"
    out["p_b"] = fisher_2x2(int((som & genomic).sum()), int((som & ~genomic).sum()),
                            int((~som & genomic).sum()), int((~som & ~genomic).sum()))
    return out


def _nan(x) -> bool:
    return isinstance(x, float) and math.isnan(x)


# ---------------------------------------------------------------- pipeline
def build_targets(bench: pd.DataFrame, maps: list[dict], scores: pd.DataFrame, cache: Cache,
                  gn: PacedGnomad | None = None) -> pd.DataFrame:
    """One row per (asset, target): germline facts + somatic facts in the indication-matched study."""
    genes = sorted({t for m in maps if m["mapping"] == "mapped" for t in m["targets"]})
    have = scores.set_index("symbol")
    missing = [g for g in genes if g not in have.index or pd.isna(have.loc[g, "n_common_func"])]
    germ = {}
    for g in genes:
        if g not in missing:
            r = have.loc[g]
            germ[g] = {"LOEUF": r.LOEUF, "n_common_func": r.n_common_func, "germline_source": "scores_v0"}
    if missing:
        gn = gn or PacedGnomad(cache)
        cons = gn.constraint(missing)
        for g in missing:
            c = cons[g]
            k = summarize_variants(g, gn.variants(g))["n_common_func"] if c.get("LOEUF") is not None else None
            germ[g] = {"LOEUF": c.get("LOEUF"), "n_common_func": k, "germline_source": "gnomad_r4_api"}
    onc_genes = sorted({t for m, (_, b) in zip(maps, bench.iterrows())
                        if m["mapping"] == "mapped" and b.therapeutic_area == "oncology" for t in m["targets"]})
    ez = entrez_ids(onc_genes, cache) if onc_genes else {}
    rows = []
    for i, (m, (_, b)) in enumerate(zip(maps, bench.iterrows())):
        onc = b.therapeutic_area == "oncology"
        study = INDICATION_STUDY.get(b.indication, PAN_CANCER) if onc else None
        for t in m["targets"] if m["mapping"] == "mapped" else []:
            som = {}
            if onc and ez.get(t):
                som = somatic_summary(somatic_raw(study, ez[t], cache))
            g = germ[t]
            rows.append({"pair_id": i, "asset": b.asset, "target": t, "entrez": ez.get(t),
                         **g, **som, "study": study,
                         "target_lane": target_lane(onc, som.get("top_change_freq"), g["LOEUF"],
                                                    g["n_common_func"])})
    return pd.DataFrame(rows)


def build_pairs(bench: pd.DataFrame, maps: list[dict], targets: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for i, (m, (_, b)) in enumerate(zip(maps, bench.iterrows())):
        t = targets[targets.pair_id == i] if len(targets) else targets
        lane = asset_lane(list(t.target_lane), m["mapping"])
        best = t[t.target_lane == lane] if len(t) else t
        som = t.dropna(subset=["top_change_freq"]) if "top_change_freq" in t else t.iloc[0:0]
        top = som.sort_values("top_change_freq", ascending=False).head(1)
        rows.append({
            "pair_id": i, "asset": b.asset, "failed_nct": b.failed_nct, "retry_nct": b.retry_nct,
            "therapeutic_area": b.therapeutic_area, "indication": b.indication, "mapping": m["mapping"],
            "chembl": m["chembl"], "targets": ";".join(m["targets"]), "n_targets": m["n_targets"],
            "lane_verdict": lane, "lane_genes": ";".join(best.target) if lane in LANE_ORDER[:2] else "",
            "max_n_common_func": t.n_common_func.max() if len(t) else None,
            "loeuf_of_max_func": (t.sort_values("n_common_func", ascending=False).LOEUF.iloc[0]
                                  if len(t) and t.n_common_func.notna().any() else None),
            "somatic_study": top.study.iloc[0] if len(top) else None,
            "somatic_gene": top.target.iloc[0] if len(top) else None,
            "somatic_frac_any": top.frac_any_mut.iloc[0] if len(top) else None,
            "somatic_top_change": top.top_change.iloc[0] if len(top) else None,
            "somatic_top_freq": top.top_change_freq.iloc[0] if len(top) else None,
            "outcome": b.outcome, "biomarker_group": b.biomarker_group, "biomarker_class": b.biomarker_class,
            "same_driver_cluster": b.same_driver_cluster, "motivating_signal": b.motivating_signal,
            "regime_match": regime_match(lane, b.biomarker_group)})
    return pd.DataFrame(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", default="data/benchmark/rescue_benchmark_v0.csv")
    ap.add_argument("--cands", default="data/candidates/ctgov_efficacy_failures_v0.csv")
    ap.add_argument("--scores", default="data/candidates/failed_trial_target_scores_v0.csv")
    ap.add_argument("--cache", default="data/raw/module3_benchmark")
    ap.add_argument("--out", default="data/benchmark/module3_benchmark_eval_v0.csv")
    ap.add_argument("--targets-out", default="data/benchmark/module3_benchmark_targets_v0.csv")
    ap.add_argument("--overlap-out", default="data/benchmark/module3_benchmark_overlap_v0.csv")
    ap.add_argument("--features-only", action="store_true", help="stop before joining outcomes")
    a = ap.parse_args(argv)
    bench, cands, scores = pd.read_csv(a.bench), pd.read_csv(a.cands), pd.read_csv(a.scores)
    cache = Cache(a.cache)
    overlap(bench, cands).to_csv(a.overlap_out, index=False)
    maps = [map_asset(x, cache) for x in bench.asset]
    targets = build_targets(bench, maps, scores, cache)
    targets.to_csv(a.targets_out, index=False)
    if a.features_only:
        return 0
    pairs = build_pairs(bench, maps, targets)
    pairs.to_csv(a.out, index=False)
    ev = evaluation(pairs)
    for k, v in ev.items():
        print(f"== {k}\n{v.to_string() if isinstance(v, pd.DataFrame) else v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
