"""Window tiling for proteins longer than a protein language model's positional limit.

ESM-1v inherits ESM-1b's 1024-token learned positional embedding, so at most 1022 residues fit
in one forward pass. Targets in this project range from 154 aa (SOD1) to 3418 aa (BRCA2), so the
window cannot be hand-declared per case as it was in the first EGFR-only version of this module.
"""
from __future__ import annotations

ESM1V_WINDOW = 1022


def make_tiles(length: int, window: int = ESM1V_WINDOW, min_overlap: int = 256):
    """Return (tiles, assignment) covering 1..length with overlapping windows.

    ``tiles`` is a list of inclusive 1-based (start, end) pairs. ``assignment`` maps every
    position to the index of the tile in which it sits most interior -- maximal distance to the
    nearest tile edge -- so no reported score is taken from a token near a context boundary.
    """
    if length <= window:
        return [(1, length)], {p: 0 for p in range(1, length + 1)}
    n = -(-(length - window) // (window - min_overlap)) + 1
    stride = (length - window) / (n - 1)
    tiles = [(round(i * stride) + 1, round(i * stride) + window) for i in range(n)]
    tiles[-1] = (length - window + 1, length)
    assignment = {}
    for p in range(1, length + 1):
        cands = [(min(p - s, e - p), i) for i, (s, e) in enumerate(tiles) if s <= p <= e]
        assignment[p] = max(cands)[1]
    covered = set()
    for s, e in tiles:
        covered |= set(range(s, e + 1))
    if covered != set(range(1, length + 1)):
        raise ValueError(f"tiling leaves gaps for length {length}")
    return tiles, assignment
