"""Minimal gnomAD GraphQL client (https://gnomad.broadinstitute.org/api).

Limits learned the hard way (Sep 2026):
- No API key or account exists. Flat limit of ~10 requests per IP per 60 s; excess returns HTTP 429 (HTML body).
- Query cost cap is 25, so at most ~20 aliased ``gene(...)`` lookups fit in one request.
- ``gene.variants`` returns no PolyPhen / SIFT for missense variants -- use Ensembl VEP for damaging predictions.
- ``joint`` has ``ac``/``an`` but no ``af`` field; compute AF yourself and fold to MAF.
For bulk work use the gnomAD Hail tables on the public GCS / AWS / Azure buckets instead of this API.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

API = "https://gnomad.broadinstitute.org/api"
DATASET = "gnomad_r4"
MAX_ALIASES = 20

CONSTRAINT_FIELDS = ("gene_id symbol gnomad_constraint { pLI oe_lof oe_lof_upper oe_mis mis_z obs_lof exp_lof "
                     "obs_mis exp_mis obs_syn exp_syn }")
# gnomad_constraint field -> output key (LOEUF is oe_lof_upper). Order is the column order of gene_constraint().
CONSTRAINT_KEYS = {"oe_lof_upper": "LOEUF", "oe_lof": "oe_lof", "pLI": "pLI", "mis_z": "mis_z",
                   "obs_lof": "obs_lof", "exp_lof": "exp_lof", "obs_mis": "obs_mis", "exp_mis": "exp_mis",
                   "obs_syn": "obs_syn", "exp_syn": "exp_syn"}
VARIANTS_QUERY = ("query($sym: String!) { gene(gene_symbol: $sym, reference_genome: GRCh38) { symbol "
                  "variants(dataset: " + DATASET + ") { variant_id consequence joint { ac an } } } }")
VARIANT_QUERY = ("query($v: String!) { variant(variantId: $v, dataset: " + DATASET + ") { "
                 "variant_id rsids joint { ac an } } }")


def _post(payload: dict, timeout: int = 180, retries: int = 4, backoff: float = 65.0) -> dict:
    for _ in range(retries):
        r = requests.post(API, json=payload, timeout=timeout)
        if r.status_code == 429:
            time.sleep(backoff)
            continue
        return r.json()
    raise RuntimeError("gnomAD rate limit: still 429 after retries")


def constraint_query(symbols: list[str]) -> str:
    """One aliased query for up to MAX_ALIASES genes."""
    if len(symbols) > MAX_ALIASES:
        raise ValueError(f"at most {MAX_ALIASES} genes per query (gnomAD cost cap 25)")
    parts = [f"g{i}: gene(gene_symbol: {json.dumps(s)}, reference_genome: GRCh38) {{ {CONSTRAINT_FIELDS} }}"
             for i, s in enumerate(symbols)]
    return "query { " + " ".join(parts) + " }"


def _cached_post(payload: dict, cache_dir: str | Path | None) -> tuple[dict, bool]:
    """POST with an optional on-disk cache keyed by the payload hash. Returns (json, came_from_cache)."""
    if cache_dir is None:
        return _post(payload), False
    path = Path(cache_dir) / (hashlib.sha1(json.dumps(payload, sort_keys=True).encode()).hexdigest() + ".json")
    if path.exists():
        return json.loads(path.read_text()), True
    js = _post(payload)
    if js.get("data"):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(js))
    return js, False


def gene_constraint(symbols: list[str], pause: float = 7.0, cache_dir: str | Path | None = None) -> list[dict]:
    """LOEUF / oe_lof / pLI / mis_z and observed/expected lof, missense and synonymous counts per gene.

    Missing genes come back with None values, never dropped. With ``cache_dir`` every response is written to disk
    and re-used, so a retry never re-fetches (``pause`` is only spent after a real network request).
    """
    out = []
    for i in range(0, len(symbols), MAX_ALIASES):
        chunk = symbols[i:i + MAX_ALIASES]
        js, cached = _cached_post({"query": constraint_query(chunk)}, cache_dir)
        data = js.get("data") or {}
        for j, s in enumerate(chunk):
            g = data.get(f"g{j}") or {}
            c = g.get("gnomad_constraint") or {}
            out.append({"symbol": s, "gene_id": g.get("gene_id"),
                        **{key: c.get(field) for field, key in CONSTRAINT_KEYS.items()}})
        if not cached:
            time.sleep(pause)
    return out


def gene_variants(symbol: str) -> list[dict]:
    js = _post({"query": VARIANTS_QUERY, "variables": {"sym": symbol}}, timeout=240)
    g = (js.get("data") or {}).get("gene")
    return g["variants"] if g else []


def variant(variant_id: str) -> dict | None:
    """Single variant by chrom-pos-ref-alt; None when gnomAD has never observed it."""
    js = _post({"query": VARIANT_QUERY, "variables": {"v": variant_id}})
    return (js.get("data") or {}).get("variant")
