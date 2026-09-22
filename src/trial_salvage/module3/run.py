"""Module 3 — genomic stratification and AlphaGenome.

OWNER: unassigned. Module 1 is complete; this module consumes ``outputs/module1/module1_output.json``.

Contract
--------
Input : module1_output.json  (see schemas/module1_output.schema.json), specifically ``handoff.module3``:
        gene, disease_efo, histology, clinical_proxy_subgroups (the subgroups the genomic model must out-perform)
Output: outputs/module3/module3_output.json conforming to schemas/module3_output.schema.json (to be written by owner),
        plus any figures. Suggested content:
        - somatic mutation prevalence of the gene by ancestry / histology / smoking (cBioPortal NSCLC cohorts)
    - germline / regulatory-variant effects from AlphaGenome for candidate stratifiers
    - a stratification rule (who to enrol) with estimated responder fraction f per population
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--outdir", default="outputs/module3")
    a = ap.parse_args(argv)
    m1 = json.loads(Path(a.module1).read_text())
    handoff = m1["handoff"]["module3"]
    print(json.dumps(handoff, indent=1))
    raise NotImplementedError("Module 3 not implemented yet — see module docstring for the contract.")


if __name__ == "__main__":
    raise SystemExit(main())
