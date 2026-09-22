"""Module 4 — rescue hypothesis ranking and trial simulation.

OWNER: unassigned. Module 1 is complete; this module consumes ``outputs/module1/module1_output.json``.

Contract
--------
Input : module1_output.json  (see schemas/module1_output.schema.json), specifically ``handoff.module4``:
        endpoint, hr_pos, hr_neg, itt_reference_hr, failed_trial_itt_hr, responder_fraction_sweep, failed_trial_n, rescue_trial_n
Output: outputs/module4/module4_output.json conforming to schemas/module4_output.schema.json (to be written by owner),
        plus any figures. Suggested content:
        - simulate an ITT trial with responder fraction f (from module 3) and subgroup HRs; power vs f and n
    - reproduce the failed trial's miss and the rescue trial's win as calibration
    - rank rescue strategies (enrichment, endpoint, line, indication, molecule) with evidence and next experiments
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--outdir", default="outputs/module4")
    a = ap.parse_args(argv)
    m1 = json.loads(Path(a.module1).read_text())
    handoff = m1["handoff"]["module4"]
    print(json.dumps(handoff, indent=1))
    raise NotImplementedError("Module 4 not implemented yet — see module docstring for the contract.")


if __name__ == "__main__":
    raise SystemExit(main())
