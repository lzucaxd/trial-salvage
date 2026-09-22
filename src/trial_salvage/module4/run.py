"""Module 4 pipeline: module1 handoff -> simulate designs -> calibrate -> rank -> figure -> JSON.

Usage:
    python -m trial_salvage.module4.run --module1 outputs/module1/module1_output.json \
        --outdir outputs/module4 [--n-simulations 2000] [--quick]

Contract
--------
Input : ``outputs/module1/module1_output.json``, specifically ``handoff.module4``:
        endpoint, hr_pos, hr_neg, itt_reference_hr, failed_trial_itt_hr,
        responder_fraction_sweep, failed_trial_n, rescue_trial_n
Output: ``outputs/module4/module4_output.json``, validated against
        ``schemas/module4_output.schema.json``, plus ``fig_<asset>_module4.png``
        and ``module4_report.md``.

The hazard ratios are taken as given and are never converted into response
probabilities. Everything in ``assumptions`` is human-supplied, and the output
contains no probability that a rescue will succeed.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
from pathlib import Path

from jsonschema import validate

from .figures import power_and_screening
from .simulate import (
    Assumptions,
    calibrate,
    min_fraction_for_power,
    power_grid,
    required_n_enriched,
)
from .strategies import rank_strategies

SCHEMA_VERSION = "1.0.0"
DEFAULT_SIZES = (200, 400, 800)
TARGET_POWER = 0.8
# Fraction assumed for the clinical-proxy design until module 3 supplies a measured value.
PROXY_FRACTION = 0.6


def _repo_schema(name: str) -> Path | None:
    """Locate schemas/<name> by walking up from this file."""
    for parent in Path(__file__).resolve().parents:
        cand = parent / "schemas" / name
        if cand.exists():
            return cand
    return None


def _report(out: dict) -> str:
    lines = [
        f"# Module 4 — rescue ranking and trial simulation: {out['asset']}",
        "",
        (
            f"Endpoint: **{out['endpoint']}**. Subgroup hazard ratios from module 1: "
            f"positive **{out['inputs']['hr_pos']}**, negative **{out['inputs']['hr_neg']}**."
        ),
        "",
        "## What a redesigned trial would require",
        "",
    ]
    mf = out["requirements"]["min_fraction_for_target_power"]
    tp = out["requirements"]["target_power"]
    if mf["fraction"] is None:
        lines.append(f"- Re-running **unselected** at n={mf['n_total']:,} cannot reach {tp:.0%} power at any "
                     f"responder fraction. {mf['note']}")
    else:
        lines.append(f"- Re-running **unselected** at n={mf['n_total']:,} needs a responder fraction of at least "
                     f"**{mf['fraction']:.0%}** to reach {tp:.0%} power.")
    ed = out["requirements"]["enriched_design"]
    if ed.get("n_randomized"):
        lines.append(f"- An **enriched** trial reaches {tp:.0%} power with **{ed['n_randomized']:,} randomised**, "
                     f"but screens about **{ed['expected_screened']:,}** at a prevalence of "
                     f"{ed['responder_fraction']:.0%}.")
    lines += ["", "## Calibration", ""]
    cal = out["calibration"]
    lines.append(f"- Failed trial (n={cal['failed_trial']['n']:,}, observed ITT HR "
                 f"{cal['failed_trial']['observed_itt_hr']}): simulated power "
                 f"{cal['failed_trial']['simulated_power']:.2f}")
    lines.append(f"- Rescue trial (n={cal['rescue_trial']['n']:,}, observed ITT HR "
                 f"{cal['rescue_trial']['observed_itt_hr']}): simulated power "
                 f"{cal['rescue_trial']['simulated_power']:.2f}")
    lines.append(f"- Ordering reproduced: **{cal['ordering_reproduced']}**. {cal['caveat']}")
    lines += ["", "## Ranked strategies", "", "| # | strategy | tier | module 1 evidence |", "|---|---|---|---|"]
    for s in out["strategies"]:
        lines.append(f"| {s['rank']} | {s['strategy']} | {s['tier'].replace('_', ' ')} | {s['module1_evidence']} |")
    lines += ["", "## Assumptions", ""] + [f"- {n}" for n in out["assumptions"]["notes"]]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--module1", default="outputs/module1/module1_output.json")
    ap.add_argument("--outdir", default="outputs/module4")
    ap.add_argument("--n-simulations", type=int, default=2000)
    ap.add_argument("--control-median-months", type=float, default=None,
                    help="Override the assumed control-arm median for the endpoint.")
    ap.add_argument("--responder-fraction", type=float, default=None,
                    help="Measured responder fraction from module 3; defaults to the midpoint of the sweep.")
    ap.add_argument("--quick", action="store_true", help="Fewer simulations and sizes, for CI and smoke tests.")
    a = ap.parse_args(argv)

    m1 = json.loads(Path(a.module1).read_text())
    h = m1["handoff"]["module4"]

    kw = {"n_simulations": 200 if a.quick else a.n_simulations}
    if a.control_median_months is not None:
        kw["control_median_months"] = a.control_median_months
        kw["control_median_source"] = "supplied on the command line"
    assumptions = Assumptions(**kw)

    sizes = (200,) if a.quick else DEFAULT_SIZES
    fractions = list(h.get("responder_fraction_sweep") or [0.2, 0.4, 0.6, 0.8])
    f_ref = a.responder_fraction if a.responder_fraction is not None else fractions[len(fractions) // 2]

    grid = power_grid(fractions, list(sizes), h["hr_pos"], h["hr_neg"], assumptions,
                      include_surrogate_fraction=PROXY_FRACTION)
    cal = calibrate(h.get("failed_trial_n") or 0, h.get("failed_trial_itt_hr") or 1.0,
                    h.get("rescue_trial_n") or 0, h.get("itt_reference_hr") or 1.0, assumptions)
    min_frac = min_fraction_for_power(max(sizes), h["hr_pos"], h["hr_neg"], assumptions, TARGET_POWER)
    enriched_req = required_n_enriched(h["hr_pos"], f_ref, assumptions, TARGET_POWER)

    design_rows = [r.to_dict() for r in grid]
    unsel_ref = next((r for r in design_rows
                      if r["design"] == "unselected" and r["responder_fraction"] == f_ref), None)
    prox_ref = next((r for r in design_rows if r["design"] == "clinical_surrogate"), None)
    strategies = [s.to_dict() for s in rank_strategies(m1, enrichment_design=enriched_req,
                                                       unselected_reference=unsel_ref,
                                                       surrogate_design=prox_ref)]

    def _field(obj, *keys):
        """module 1 nests asset/target/disease as objects; accept a bare string too."""
        if isinstance(obj, dict):
            for k in keys:
                if obj.get(k):
                    return obj[k]
            return None
        return obj

    asset = _field(m1.get("asset"), "name")
    target = _field(m1.get("target"), "symbol", "gene")
    gene = target or "the biomarker"

    outdir = Path(a.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    fig_path = outdir / f"fig_{(asset or 'asset').lower().replace(' ', '_')}_module4.png"
    power_and_screening(design_rows, assumptions, h["hr_pos"], h["hr_neg"], enriched_req, str(fig_path),
                        asset_name=asset or "the asset", gene=gene, target_power=TARGET_POWER,
                        crossing_fraction=min_frac.get("fraction"))

    out = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "asset": asset or "unknown",
        "target": target or "unknown",
        "disease": _field(m1.get("disease"), "name"),
        "endpoint": h.get("endpoint") or "unknown",
        "inputs": h,
        "assumptions": {**{k: v for k, v in assumptions.__dict__.items()}, "notes": assumptions.notes()},
        "designs": design_rows,
        "calibration": cal,
        "requirements": {
            "target_power": TARGET_POWER,
            "min_fraction_for_target_power": min_frac,
            "enriched_design": enriched_req,
        },
        "strategies": strategies,
        "figures": [fig_path.name],
        "notes": [
            ("Power is conditional on the assumptions listed above; it is not a probability that a rescue "
                "will succeed."),
            ("The mixture population is simulated participant by participant rather than through module 1's "
                "log-linear mixture approximation, because hazard ratios are not collapsible across strata."),
            (f"The clinical-proxy design assumes a positive fraction of {PROXY_FRACTION:.0%}, which module 3 "
                "has not yet measured."),
        ],
    }

    schema_path = _repo_schema("module4_output.schema.json")
    if schema_path:
        validate(instance=out, schema=json.loads(schema_path.read_text()))

    (outdir / "module4_output.json").write_text(json.dumps(out, indent=1))
    (outdir / "module4_report.md").write_text(_report(out))
    print(json.dumps({
        "endpoint": out["endpoint"],
        "min_fraction_unselected": min_frac.get("fraction"),
        "enriched_n": enriched_req.get("n_randomized"),
        "enriched_screened": enriched_req.get("expected_screened"),
        "calibration_ordering_reproduced": cal["ordering_reproduced"],
        "strategies": len(strategies),
        "outdir": str(outdir),
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
