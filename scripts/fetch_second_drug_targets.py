"""Fetch gnomAD germline data for second-drug targets of combination trials (Module 3, germline lane).

Targets to add = every ';'-separated symbol in ``targets`` of the trial-drug pairs table MINUS the symbols
already scored in failed_trial_target_scores_v0.csv. For each: expanded gnomAD r4 constraint (one aliased
GraphQL query per <= 20 genes) and the variant list via ``trial_salvage.gnomad.gene_variants``, summarised with
``trial_salvage.module3.germline.summarize_variants``. No score is computed here (the v1 score is applied later).

Rate limit is shared across agents on one IP: >= 20 s between any two gnomAD requests; on HTTP 429 sleep 65 s,
retry at most 4 times. Every response is cached under data/raw/gnomad_cache/ so a re-run never re-fetches.
Genes gnomAD does not know are kept as rows with nulls and a ``status`` value -- never dropped.
status: ok | no_lof_constraint (gene known, LOEUF null) | not_in_gnomad | variants_error: <msg>.

Usage:  PYTHONPATH=src python scripts/fetch_second_drug_targets.py
"""
from __future__ import annotations

import argparse
import functools
import json
import time
from pathlib import Path

import pandas as pd
import requests

from trial_salvage import gnomad
from trial_salvage.module3.germline import summarize_variants

PAIRS = Path("data/candidates/ctgov_efficacy_failures_trial_drug_pairs_v0.csv")
SCORED = Path("data/candidates/failed_trial_target_scores_v0.csv")
OUT = Path("data/candidates/second_drug_targets_raw_v0.csv")
CACHE = Path("data/raw/gnomad_cache")
PACE_S = 20.0
BACKOFF_S = 65.0
RETRIES = 4
CHUNK = 20

CONSTRAINT_FIELDS = ("gene_id symbol gnomad_constraint { oe_lof_upper oe_lof pLI mis_z obs_lof exp_lof "
                     "obs_mis exp_mis obs_syn exp_syn }")
CONSTRAINT_KEYS = ["oe_lof", "pLI", "mis_z", "obs_lof", "exp_lof", "obs_mis", "exp_mis", "obs_syn", "exp_syn"]
COLUMNS = ["symbol", "gene_id", "status", "LOEUF", *CONSTRAINT_KEYS, "n_variants", "n_common", "n_common_func",
           "n_common_lof", "cum_maf_func", "trials", "n_trials"]

_last_request = [0.0]
_last_errors: list = [None]


def split_targets(cell) -> list[str]:
    if cell is None or (isinstance(cell, float) and pd.isna(cell)):
        return []
    return [t.strip() for t in str(cell).split(";") if t.strip()]


def targets_to_add(pairs: pd.DataFrame, scored: pd.DataFrame) -> list[str]:
    allt = {t for cell in pairs["targets"] for t in split_targets(cell)}
    return sorted(allt - set(scored["symbol"].dropna()))


def trials_by_target(pairs: pd.DataFrame) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    for _, r in pairs.iterrows():
        for t in split_targets(r["targets"]):
            label = f"{r['drug']} ({r['nct']})"
            if label not in out.setdefault(t, []):
                out[t].append(label)
    return out


def constraint_query(symbols: list[str]) -> str:
    if len(symbols) > CHUNK:
        raise ValueError(f"at most {CHUNK} genes per query (gnomAD cost cap 25)")
    parts = [f"g{i}: gene(gene_symbol: {json.dumps(s)}, reference_genome: GRCh38) {{ {CONSTRAINT_FIELDS} }}"
             for i, s in enumerate(symbols)]
    return "query { " + " ".join(parts) + " }"


def _pace() -> None:
    wait = PACE_S - (time.monotonic() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.monotonic()


def _post_paced(payload: dict, timeout: int = 180) -> dict:
    """POST with >= PACE_S spacing; 429 or network error -> sleep BACKOFF_S, at most RETRIES attempts."""
    for attempt in range(RETRIES):
        _pace()
        try:
            r = requests.post(gnomad.API, json=payload, timeout=timeout)
        except requests.RequestException as e:
            print(f"  network error ({e.__class__.__name__}), attempt {attempt + 1}", flush=True)
        else:
            if r.status_code != 429:
                return r.json()
            print(f"  HTTP 429, attempt {attempt + 1}; sleeping {BACKOFF_S:.0f} s", flush=True)
        time.sleep(BACKOFF_S)
        _last_request[0] = time.monotonic()
    raise RuntimeError("gnomAD: still failing after retries")


def _install_paced_post() -> None:
    """Route gnomad.gene_variants through the paced/backoff POST and record GraphQL errors (module untouched)."""
    def post(payload: dict, timeout: int = 180, **_) -> dict:
        js = _post_paced(payload, timeout=timeout)
        _last_errors[0] = js.get("errors")
        return js
    gnomad._post = functools.update_wrapper(post, gnomad._post)


def fetch_constraint(symbols: list[str]) -> dict[str, dict]:
    out = {}
    for i in range(0, len(symbols), CHUNK):
        chunk = symbols[i:i + CHUNK]
        path = CACHE / f"constraint_{'_'.join(chunk)}.json" if len(chunk) <= 5 else \
            CACHE / f"constraint_{chunk[0]}-{chunk[-1]}_{len(chunk)}.json"
        if path.exists():
            js = json.loads(path.read_text())
        else:
            print(f"constraint query: {len(chunk)} genes", flush=True)
            js = _post_paced({"query": constraint_query(chunk)})
            if js.get("errors") and not js.get("data"):
                raise RuntimeError(f"constraint query failed: {js['errors']}")
            path.write_text(json.dumps(js))
        data = js.get("data") or {}
        for j, s in enumerate(chunk):
            out[s] = data.get(f"g{j}")
    return out


def fetch_variants(symbol: str) -> tuple[list[dict] | None, str | None]:
    path = CACHE / f"variants_{symbol}.json"
    if path.exists():
        return json.loads(path.read_text()), None
    print(f"variants: {symbol}", flush=True)
    _last_errors[0] = None
    try:
        vs = gnomad.gene_variants(symbol)
    except RuntimeError as e:
        return None, str(e)
    if _last_errors[0] and not vs:
        return None, json.dumps(_last_errors[0])[:300]
    path.write_text(json.dumps(vs))
    return vs, None


def build_row(symbol: str, gene: dict | None, variants: list[dict] | None, var_err: str | None,
              trials: list[str]) -> dict:
    row = dict.fromkeys(COLUMNS)
    row.update(symbol=symbol, trials="; ".join(trials), n_trials=len(trials))
    if not gene:
        row["status"] = "not_in_gnomad"
        return row
    row["gene_id"] = gene.get("gene_id")
    c = gene.get("gnomad_constraint")
    if c:
        row["LOEUF"] = c.get("oe_lof_upper")
        row.update({k: c.get(k) for k in CONSTRAINT_KEYS})
    if variants is None:
        row["status"] = f"variants_error: {var_err}"
        return row
    s = summarize_variants(symbol, variants)
    row.update({k: s[k] for k in ["n_variants", "n_common", "n_common_func", "n_common_lof", "cum_maf_func"]})
    # e.g. single-exon genes have no expected LoF sites, so gnomAD reports no LOEUF / pLI
    row["status"] = "ok" if row["LOEUF"] is not None else "no_lof_constraint"
    return row


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args(argv)
    pairs, scored = pd.read_csv(PAIRS), pd.read_csv(SCORED)
    symbols = targets_to_add(pairs, scored)
    trials = trials_by_target(pairs)
    print(f"{len(symbols)} targets to add: {', '.join(symbols)}", flush=True)
    CACHE.mkdir(parents=True, exist_ok=True)
    _install_paced_post()
    genes = fetch_constraint(symbols)
    rows = []
    for s in symbols:
        vs, err = fetch_variants(s) if genes.get(s) else (None, None)
        rows.append(build_row(s, genes.get(s), vs, err, trials.get(s, [])))
    df = pd.DataFrame(rows, columns=COLUMNS)
    df.to_csv(a.out, index=False)
    print(df["status"].value_counts().to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
