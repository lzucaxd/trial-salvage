"""Minimal gnomAD GraphQL client (https://gnomad.broadinstitute.org/api).

Limits learned the hard way (Sep 2026):
- No API key or account exists. Flat limit of ~10 requests per IP per 60 s; excess returns HTTP 429 (HTML body).
- Query cost cap is 25, so at most ~20 aliased ``gene(...)`` lookups fit in one request.
- ``gene.variants`` returns no PolyPhen / SIFT for missense variants -- use Ensembl VEP for damaging predictions.
- ``joint`` has ``ac``/``an`` but no ``af`` field; compute AF yourself and fold to MAF.
For bulk work use the gnomAD Hail tables on the public GCS / AWS / Azure buckets instead of this API.
"""
from __future__ import annotations

import json
import time

import requests

API = "https://gnomad.broadinstitute.org/api"
DATASET = "gnomad_r4"
MAX_ALIASES = 20

CONSTRAINT_FIELDS = "gene_id symbol gnomad_constraint { pLI oe_lof oe_lof_upper oe_mis mis_z obs_lof exp_lof }"
VARIANTS_QUERY = ("query($sym: String!) { gene(gene_symbol: $sym, reference_genome: GRCh38) { symbol "
                  "variants(dataset: " + DATASET + ") { variant_id consequence joint { ac an } } } }")
VARIANT_QUERY = ("query($v: String!) { variant(variantId: $v, dataset: " + DATASET + ") { "
                 "variant_id rsids joint { ac an } } }")


def _post(payload: dict, timeout: int = 180, retries: int = 4, backoff: float = 35.0) -> dict:
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


def gene_constraint(symbols: list[str], pause: float = 7.0) -> list[dict]:
    """LOEUF / pLI / missense z per gene. Missing genes come back with None values, never dropped."""
    out = []
    for i in range(0, len(symbols), MAX_ALIASES):
        chunk = symbols[i:i + MAX_ALIASES]
        js = _post({"query": constraint_query(chunk)})
        data = js.get("data") or {}
        for j, s in enumerate(chunk):
            g = data.get(f"g{j}") or {}
            c = g.get("gnomad_constraint") or {}
            out.append({"symbol": s, "gene_id": g.get("gene_id"), "LOEUF": c.get("oe_lof_upper"),
                        "oe_lof": c.get("oe_lof"), "pLI": c.get("pLI"), "mis_z": c.get("mis_z"),
                        "obs_lof": c.get("obs_lof"), "exp_lof": c.get("exp_lof")})
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
