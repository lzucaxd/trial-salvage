"""Score merging, ClinVar validation and the applicability gate.

The gate is the point of this module. Across six selection genes an ESM masked-marginal score was
a usable residue-level triage signal on two of them and no better than a 20-year-old classical
predictor on the rest, so every case emits a machine-readable verdict that a consumer is expected
to read BEFORE the scores. Nothing here converts a score into a probability that a rescue works.
"""
from __future__ import annotations

import pandas as pd

from .stats import auroc

AA20 = list("ACDEFGHIKLMNPQRSTVWY")
PATHOGENIC = {"Pathogenic", "Likely pathogenic"}
BENIGN = {"Benign", "Likely benign"}
DRUG_RESPONSE = "Drug response"
AUROC_FLOOR = 0.60

VERDICTS = ("rank_residues_only", "do_not_rank", "not_validated")


def classify_clinvar(significances) -> str:
    """Collapse ClinVar significance terms to one class, most clinically decisive first.

    ``drug_response`` is a real ClinVar term and is kept as its own class rather than folded into
    the others. Note that the EGFR records carrying it name no drug anywhere in the retrieved
    annotation and sit at ClinVar's weakest review tier, so it must not be read as evidence about
    a specific agent. It takes no part in the pathogenic-vs-benign validation.
    """
    s = set(significances or [])
    if s & PATHOGENIC:
        return "pathogenic"
    if s & BENIGN:
        return "benign"
    if DRUG_RESPONSE in s:
        return "drug_response"
    if "Variant of uncertain significance" in s:
        return "vus"
    return "unannotated"


def score_frame(positions, logprob_by_model: dict, sequence: str) -> pd.DataFrame:
    """Long frame of masked-marginal scores: log p(mut) - log p(wt) per model, plus the ensemble.

    ``logprob_by_model`` maps a model key to an (n_positions, 20) array of log-softmax values in
    AA20 column order; every model must share the ``positions`` grid.
    """
    import numpy as np

    positions = list(positions)
    wt_index = np.array([AA20.index(sequence[p - 1]) for p in positions])
    rows = np.arange(len(positions))
    centred = {k: v - v[rows, wt_index][:, None] for k, v in logprob_by_model.items()}
    members = sorted(k for k in centred if "esm1v" in k)
    if not members:
        raise ValueError("no ESM-1v member matrices supplied")
    ensemble = np.mean([centred[k] for k in members], axis=0)
    spread = np.std([centred[k] for k in members], axis=0, ddof=1) if len(members) > 1 else None
    out = []
    for i, pos in enumerate(positions):
        wt = sequence[pos - 1]
        for j, aa in enumerate(AA20):
            if aa == wt:
                continue
            rec = {"position_uniprot": int(pos), "wt_aa": wt, "mut_aa": aa,
                       "esm1v_ensemble": float(ensemble[i, j])}
            if spread is not None:
                rec["esm1v_member_sd"] = float(spread[i, j])
            for k, v in centred.items():
                if "esm1v" not in k:
                    rec[k] = float(v[i, j])
            out.append(rec)
    df = pd.DataFrame(out)
    df["position_mean"] = df.groupby("position_uniprot").esm1v_ensemble.transform("mean")
    df["residual"] = df.esm1v_ensemble - df.position_mean
    return df


def annotate(df: pd.DataFrame, missense: dict, gene: str) -> pd.DataFrame:
    import numpy as np

    ann = pd.DataFrame([{
        "position_uniprot": r["position"], "wt_aa": r["wt_aa"], "mut_aa": r["mut_aa"],
        "clinvar_class": classify_clinvar(r["clinical_significance"]),
        "clinical_significance": sorted(x for x in r["clinical_significance"] if x),
        "review_status": sorted(r["review_status"]),
        "max_population_frequency": r["max_population_frequency"],
        "n_pubmed": len(r["pubmed"]),
        "polyphen": float(np.mean(r["polyphen"])) if r["polyphen"] else float("nan"),
        "sift": float(np.mean(r["sift"])) if r["sift"] else float("nan"),
    } for r in missense.values()])
    merged = df.merge(ann, on=["position_uniprot", "wt_aa", "mut_aa"], how="left")
    merged["clinvar_class"] = merged.clinvar_class.fillna("unannotated")
    merged.insert(0, "variant_id",
                  gene + ":p." + merged.wt_aa + merged.position_uniprot.astype(str) + merged.mut_aa)
    return merged


def validate(df: pd.DataFrame, position_constraint: pd.DataFrame | None = None) -> dict:
    """ESM vs retrieved ClinVar labels, with the like-for-like classical-predictor comparison.

    PolyPhen and SIFT do not cover every variant ESM scores, so the comparison that decides the
    verdict is computed on the matched subset all three cover.
    """
    pos, neg = df.clinvar_class.eq("pathogenic"), df.clinvar_class.eq("benign")
    overall = auroc(df.esm1v_ensemble, pos, neg)
    matched = df[df.polyphen.notna() & df.sift.notna()]
    mpos, mneg = matched.clinvar_class.eq("pathogenic"), matched.clinvar_class.eq("benign")
    esm_m = auroc(matched.esm1v_ensemble, mpos, mneg)
    # PolyPhen is oriented high = damaging; SIFT low = deleterious, matching the ESM orientation.
    poly_m = auroc(-matched.polyphen, mpos, mneg)
    sift_m = auroc(matched.sift, mpos, mneg)
    # Constraint spread is a property of the WHOLE protein, so it must come from the full
    # position table when one is supplied. Computing it from the annotated subset alone biases it
    # toward wherever ClinVar happens to have submissions (SOD1: 3.22 vs 3.70 full-protein).
    if position_constraint is not None:
        spread = float(position_constraint.mean_score.std())
        spread_basis = f"all {len(position_constraint)} scanned positions"
    else:
        spread = float(df.groupby("position_uniprot").esm1v_ensemble.mean().std())
        spread_basis = "annotated positions only (full position table not supplied)"
    return {
        "task": "ClinVar pathogenic/likely-pathogenic vs benign/likely-benign, retrieved independently",
        "n_substitutions_scored": len(df), "n_pathogenic": int(pos.sum()), "n_benign": int(neg.sum()),
        "n_vus": int(df.clinvar_class.eq("vus").sum()),
        "esm1v": overall,
        "matched_subset": {"esm1v": esm_m, "polyphen": poly_m, "sift": sift_m,
                            "note": "the like-for-like comparison; quote this row, not the overall AUROC"},
        "positional_decomposition": {
            "position_mean": auroc(df.position_mean, pos, neg), "residual": auroc(df.residual, pos, neg),
            "note": "the per-position mean is residue constraint; the residual is substitution identity"},
        "reliability_diagnostic": {
            "position_constraint_spread_sd": spread, "median_score": float(df.esm1v_ensemble.median()),
            "fraction_below_minus5": float((df.esm1v_ensemble < -5).mean()),
            "basis": spread_basis,
            "note": "observed rank correlation with AUROC was 1.00 across four evaluable genes "
                 "(exact permutation p = 0.083, n = 4): suggestive only, NOT used as a decision rule, "
                 "and contradicted by SOD1 which has high spread and chance-level performance"},
        "evidence_type": "derived_statistic", "source": "this module"}


def verdict(validation: dict) -> dict:
    """Decide from measured performance, never from the author's confidence in the model."""
    esm = validation["matched_subset"]["esm1v"]["auroc"]
    overall = validation["esm1v"]["auroc"]
    poly = validation["matched_subset"]["polyphen"]["auroc"]
    sift = validation["matched_subset"]["sift"]["auroc"]
    spread = validation["reliability_diagnostic"]["position_constraint_spread_sd"]
    classical = [c for c in (poly, sift) if c is not None]
    best = max(classical) if classical else None
    if overall is None:
        return {"verdict": "not_validated", "reason": (
            f"only {validation['n_benign']} benign-classified substitutions exist for this gene, so "
            f"pathogenic-vs-benign discrimination could not be measured (constraint spread "
            f"{spread:.2f} log units). Treat any ranking from this protein as unvalidated.")}
    if best is not None and esm is not None and best > esm:
        which = "SIFT" if sift == best else "PolyPhen"
        return {"verdict": "do_not_rank", "reason": (
            f"ESM-1v AUROC {esm:.3f} on the matched subset is beaten by {which} ({best:.3f}) on exactly "
            f"the same variants. ESM adds nothing here; use the classical predictor or experimental data.")}
    if overall <= AUROC_FLOOR:
        return {"verdict": "do_not_rank", "reason": (
            f"ESM-1v AUROC {overall:.3f} is at or below {AUROC_FLOOR} against retrieved ClinVar labels.")}
    compare = (f" and beats the best classical predictor ({best:.3f}) on the matched subset"
               if best is not None else "; no PolyPhen/SIFT coverage exists for this gene to compare against")
    return {"verdict": "rank_residues_only", "reason": (
        f"ESM-1v AUROC {overall:.3f}{compare}. Usable as a residue-level triage signal only: the "
        f"substitution-specific residual carried no reliable signal in any case tested, so rank "
        f"residues for follow-up, not substitutions at a residue.")}
