"""Module 2 — protein variants and ESM.

OWNER: unassigned. Module 1 is complete; this module consumes ``outputs/module1/module1_output.json``.

Contract
--------
Input : module1_output.json  (see schemas/module1_output.schema.json), specifically ``handoff.module2``:
        uniprot, gene, sensitising_variants, primary_resistance_variants, acquired_resistance_variants
Output: outputs/module2/module2_output.json conforming to schemas/module2_output.schema.json (to be written by owner),
        plus any figures. Suggested content:
        - per-variant ESM log-likelihood ratio / embedding distance vs wild type
    - optional Boltz-2 co-folding of drug + variant kinase domain, predicted affinity
    - does the model rank sensitising > wild-type > resistance variants for drug binding?
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--outdir", default="outputs/module2")
    a = ap.parse_args(argv)
    m1 = json.loads(Path(a.module1).read_text())
    handoff = m1["handoff"]["module2"]
    print(json.dumps(handoff, indent=1))
    raise NotImplementedError("Module 2 not implemented yet — see module docstring for the contract.")


if __name__ == "__main__":
    raise SystemExit(main())
