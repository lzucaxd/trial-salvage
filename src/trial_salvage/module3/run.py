"""Module 3 — genomic stratification and AlphaGenome.

OWNER: RaminKahidi (branch module3-genomic-stratification). Germline + somatic lanes implemented; AlphaGenome not yet.

Two lanes, reported side by side, because the answer to "is there variation to stratify on?" depends on which:
  germline : target -> Reactome pathway genes -> gnomAD constraint + common functional variants -> score
  somatic  : named tumour variants -> cBioPortal study frequency vs gnomAD germline frequency

Usage
-----
python -m trial_salvage.module3.run --gene EGFR --pathway R-HSA-177929 \
    --cbio-study luad_mskcc_2023_met_organotropism --entrez 1956 \
    --somatic L858R:7-55191822-T-G T790M:7-55181378-C-T G719S:7-55174014-G-A
(``--module1`` supplies ``--gene`` from ``handoff.module3.gene`` when present.)

Original stub contract (kept):

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
import time
from pathlib import Path

import pandas as pd

from trial_salvage import biodata, gnomad
from trial_salvage.module3.germline import stratification_scores, summarize_variants


def germline_lane(genes: list[str], pause: float = 7.0) -> pd.DataFrame:
    cons = {r["symbol"]: r for r in gnomad.gene_constraint(genes)}
    rows = []
    for s in genes:
        c = cons.get(s, {"symbol": s})
        if c.get("LOEUF") is None:
            rows.append({**c, "n_common_func": None})
            continue
        rows.append({**c, **summarize_variants(s, gnomad.gene_variants(s))})
        time.sleep(pause)
    df = pd.DataFrame(stratification_scores(rows))
    return df.sort_values("score", ascending=False, na_position="last")


def somatic_lane(study: str, entrez: int, specs: list[str]) -> list[dict]:
    """specs are 'ProteinChange:chrom-pos-ref-alt'; compares tumour frequency with germline frequency."""
    pairs = [s.split(":", 1) for s in specs]
    som = biodata.somatic_frequency(study, entrez, [p for p, _ in pairs])
    out = []
    for prot, vid in pairs:
        g = gnomad.variant(vid)
        j = (g or {}).get("joint") or {}
        out.append({"variant": prot, "gnomad_id": vid, "somatic_freq": som["variants"][prot]["freq"],
                    "somatic_n": som["variants"][prot]["n"], "study_n": som["n_samples"],
                    "germline_ac": j.get("ac", 0), "germline_an": j.get("an"),
                    "germline_detected": g is not None})
        time.sleep(7)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--outdir", default="outputs/module3")
    ap.add_argument("--gene", help="drug target symbol (else handoff.module3.gene)")
    ap.add_argument("--pathway", help="Reactome stId to expand the target into; default: target only")
    ap.add_argument("--cbio-study", help="cBioPortal study id for the somatic lane")
    ap.add_argument("--entrez", type=int, help="Entrez id of the target for cBioPortal")
    ap.add_argument("--somatic", nargs="*", default=[], help="ProteinChange:chrom-pos-ref-alt")
    a = ap.parse_args(argv)

    gene = a.gene
    if not gene and Path(a.module1).exists():
        gene = json.loads(Path(a.module1).read_text())["handoff"]["module3"]["gene"]
    if not gene:
        ap.error("need --gene or a module1_output.json with handoff.module3.gene")

    genes = biodata.pathway_genes(a.pathway) if a.pathway else [gene]
    out_dir = Path(a.outdir)
    out_dir.mkdir(parents=True, exist_ok=True)

    germ = germline_lane(genes)
    germ.to_csv(out_dir / "germline_pathway_variation.csv", index=False)
    somatic = somatic_lane(a.cbio_study, a.entrez, a.somatic) if a.cbio_study and a.somatic else []

    scored = germ.dropna(subset=["LOEUF"])
    result = {
        "gene": gene, "pathway": a.pathway, "n_pathway_genes": len(genes),
        "germline": {"n_scored": len(scored),
                     "total_common_functional_variants": int(scored.n_common_func.sum()),
                     "genes_without_common_functional": int((scored.n_common_func == 0).sum()),
                     "target": scored[scored.symbol == gene].to_dict("records")},
        "somatic": somatic,
        "lane_verdict": _verdict(scored, gene, somatic),
    }
    (out_dir / "module3_output.json").write_text(json.dumps(result, indent=1, default=str))
    print(json.dumps(result["lane_verdict"], indent=1))
    return 0


def _verdict(scored: pd.DataFrame, gene: str, somatic: list[dict]) -> dict:
    """Which regime carries stratifiable variation. Descriptive, not a rescue prediction."""
    tgt = scored[scored.symbol == gene]
    tgt_func = int(tgt.n_common_func.iloc[0]) if len(tgt) else None
    enriched = [s["variant"] for s in somatic
                if s["somatic_freq"] and s["somatic_freq"] >= 0.01 and
                (not s["germline_detected"] or (s["germline_ac"] / s["germline_an"]) < 1e-4)]
    if enriched:
        lane = "somatic"
    elif tgt_func and tgt_func >= 3:
        lane = "germline_common"
    else:
        lane = "none_detected"
    return {"lane": lane, "target_common_functional_variants": tgt_func, "somatic_only_variants": enriched}


if __name__ == "__main__":
    raise SystemExit(main())
