"""ESM masked-marginal scoring. Needs torch + transformers, so imports are deferred.

Protocol: masked marginals (Meier et al. 2021, "Language models enable zero-shot prediction of
the effects of mutations on protein function", NeurIPS).

    score(i, mut) = log p(x_i = mut | x_-i) - log p(x_i = wt | x_-i)

One position is masked at a time. Proteins longer than the model's positional limit are covered
by overlapping tiles (see tiling.py); a position is scored in the tile where it sits most
interior, and ``overlap_qc`` optionally re-scores overlap positions in a second tile to measure
the size of the tiling artifact directly rather than assuming it is negligible.

This module is not exercised by CI: the committed score tables under data/module2 let the rest of
the module run offline. Run it on a GPU via scripts/score_module2_case.py.
"""
from __future__ import annotations

import time

AA20 = list("ACDEFGHIKLMNPQRSTVWY")
ESM1V_MODELS = [f"facebook/esm1v_t33_650M_UR90S_{i}" for i in range(1, 6)]
ESM2_650M = "facebook/esm2_t33_650M_UR50D"


def _load(model_id: str, device: str):
    import torch
    from transformers import AutoModelForMaskedLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(model_id)
    model = AutoModelForMaskedLM.from_pretrained(model_id, torch_dtype=torch.float32).to(device).eval()
    cols = torch.tensor([tok.convert_tokens_to_ids(a) for a in AA20])
    if not bool((cols >= 0).all()) or len(set(cols.tolist())) != 20:
        raise ValueError(f"{model_id}: could not map all 20 amino acids to distinct tokens")
    return tok, model, cols


def _score_tile(model, tok, cols, sequence: str, tile, positions, device: str, batch: int):
    import numpy as np
    import torch

    start, end = tile
    sub = sequence[start - 1:end]
    ids = tok(sub, return_tensors="pt")["input_ids"][0]
    if ids.shape[0] != len(sub) + 2:
        raise ValueError(f"expected {len(sub) + 2} tokens, got {int(ids.shape[0])}")
    for probe in (0, len(sub) // 2, len(sub) - 1):
        if tok.convert_ids_to_tokens(int(ids[probe + 1])) != sub[probe]:
            raise ValueError("token/residue misalignment: refusing to emit scores")
    local = [p - start for p in positions]
    if not all(0 <= j < len(sub) for j in local):
        raise ValueError("position outside tile")
    out = np.zeros((len(positions), 20), dtype="float32")
    for k in range(0, len(local), batch):
        chunk = list(range(k, min(k + batch, len(local))))
        batched = ids.unsqueeze(0).repeat(len(chunk), 1).clone()
        for bi, ri in enumerate(chunk):
            batched[bi, local[ri] + 1] = tok.mask_token_id
        with torch.no_grad():
            logits = model(input_ids=batched.to(device)).logits.float()
        lsm = torch.log_softmax(logits, dim=-1)
        for bi, ri in enumerate(chunk):
            out[ri] = lsm[bi, local[ri] + 1, cols].cpu().numpy()
    return out


def score_case(case: dict, model_ids: list[str], *, batch: int = 8, overlap_qc: bool = False,
               qc_sample: int = 60, progress=print) -> tuple[dict, dict]:
    """Return ({model_key: (n_positions, 20) log-softmax array}, {model_key: metadata})."""
    import numpy as np
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    sequence = case["sequence"]
    tiles = [tuple(t) for t in case["tiles"]]
    assignment = {int(k): v for k, v in case["assignment"].items()}
    positions = sorted(int(p) for p in case["positions"])
    index = {p: i for i, p in enumerate(positions)}
    matrices, meta = {}, {}
    for model_id in model_ids:
        t0 = time.time()
        tok, model, cols = _load(model_id, device)
        key = model_id.split("/")[-1]
        mat = np.zeros((len(positions), 20), dtype="float32")
        for ti, tile in enumerate(tiles):
            mine = [p for p in positions if assignment[p] == ti]
            if not mine:
                continue
            progress(f"  [{key}] tile {ti} {tile}: {len(mine)} positions  {time.time() - t0:.0f}s")
            block = _score_tile(model, tok, cols, sequence, tile, mine, device, batch)
            for j, p in enumerate(mine):
                mat[index[p]] = block[j]
        qc = []
        if overlap_qc and len(tiles) > 1:
            for ti, (start, end) in enumerate(tiles):
                alt = [p for p in positions if start <= p <= end and assignment[p] != ti]
                if not alt:
                    continue
                alt = alt[:: max(1, len(alt) // qc_sample)][:qc_sample]
                block = _score_tile(model, tok, cols, sequence, (start, end), alt, device, batch)
                for j, p in enumerate(alt):
                    wt = AA20.index(sequence[p - 1])
                    primary = mat[index[p]] - mat[index[p]][wt]
                    other = block[j] - block[j][wt]
                    qc.append({"position": int(p), "primary_tile": int(assignment[p]), "other_tile": int(ti),
                                   "mean_abs_delta": float(np.abs(primary - other).mean()),
                                   "max_abs_delta": float(np.abs(primary - other).max())})
        matrices[key] = mat
        meta[key] = {"model_id": model_id, "wall_seconds": round(time.time() - t0, 1), "dtype": "float32",
                         "protocol": "masked_marginals", "device": device, "n_tiles": len(tiles),
                         "n_positions": len(positions), "overlap_qc": qc}
        del model
        if device == "cuda":
            torch.cuda.empty_cache()
    return matrices, meta
