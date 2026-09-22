"""Rank rescue strategies from module 1's evidence, with a next experiment each.

The ranking is deterministic and every entry cites the module 1 field it rests
on. Two rules govern what comes out:

* **Tiers, not scores.** A strategy lands in a visible tier. No numeric
  "probability of rescue" is produced — the evidence here cannot support one, and
  a number would be read as a forecast.
* **Evidence strength decides the tier, not plausibility.** A strategy is tier 1
  only if module 1 recorded a clinical observation in this asset supporting it;
  a mechanistic or model-only rationale is tier 3 and says what experiment would
  move it.

Where a strategy changes who is enrolled, the simulation result is attached so
the design consequence is visible next to the rationale.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field

__all__ = ["TIERS", "Strategy", "rank_strategies"]

TIERS = (
    "tier_1_clinical_evidence_in_this_asset",
    "tier_2_clinical_evidence_indirect",
    "tier_3_mechanistic_or_model_only",
    "tier_4_not_supported_by_available_evidence",
)

# Which module 1 diagnosis rules, if fired, put a strategy on clinical footing.
_SUPPORTING_RULES = {
    "biomarker_enrichment_new_inclusion_criteria": (
        "qualitative_interaction_in_rescue_trial",
        "biomarker_heterogeneity_in_failed_trial",
    ),
    "clinical_surrogate_enrichment": ("prespecified_subgroup_benefit",),
    "new_endpoint": ("os_confounded_by_crossover",),
    "narrower_indication": ("qualitative_interaction_in_rescue_trial",),
    "new_line_of_therapy": ("primary_endpoint_missed",),
    "molecule_modification": (),
}

_NEXT_EXPERIMENT = {
    "biomarker_enrichment_new_inclusion_criteria": (
        "Run the assay prospectively on archived tumour tissue from the failed trial and re-estimate the "
        "subgroup hazard ratios in the pre-registered positive and negative strata before committing to a "
        "new trial."
    ),
    "clinical_surrogate_enrichment": (
        "Quantify how well the clinical proxy predicts assay positivity in a cohort with both recorded; the "
        "proxy is only worth using where assay access is the binding constraint."
    ),
    "new_endpoint": (
        "Pre-specify the progression-based endpoint with blinded independent central review, and pre-specify "
        "how crossover will be handled in the survival analysis."
    ),
    "narrower_indication": (
        "Confirm the restricted population has sufficient incidence to enrol the required sample size at the "
        "planned number of sites."
    ),
    "new_line_of_therapy": (
        "Check whether the earlier-line population has a different comparator standard of care, which changes "
        "the control-arm event rate the design assumes."
    ),
    "molecule_modification": (
        "Hand the target and variant list to module 2; a molecule change needs structural or binding evidence "
        "that this module does not have."
    ),
}

_UNDERMINED_BY = {
    "biomarker_enrichment_new_inclusion_criteria": (
        "Assay-negative patients benefiting at a similar rate, or the positive-stratum effect shrinking when "
        "measured prospectively rather than post hoc."
    ),
    "clinical_surrogate_enrichment": (
        "The proxy turning out to be weakly associated with assay positivity, which would re-dilute the "
        "enrolled population."
    ),
    "new_endpoint": (
        "The new endpoint not being accepted as registrationally adequate, or disagreeing in direction with "
        "overall survival."
    ),
    "narrower_indication": "Insufficient eligible incidence to enrol the trial.",
    "new_line_of_therapy": "A more effective comparator in the earlier line erasing the margin.",
    "molecule_modification": "Module 2 finding the resistance mechanism is not binding-site mediated.",
}


@dataclass
class Strategy:
    strategy: str
    tier: str
    rank: int = 0
    used_historically: bool | None = None
    module1_evidence: str = ""
    supporting_rules: list[str] = field(default_factory=list)
    design_consequence: dict | None = None
    next_experiment: str = ""
    would_be_undermined_by: str = ""
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _fired_rules(module1: dict) -> set[str]:
    ev = module1.get("failure_diagnosis", {}).get("evidence", []) or []
    return {e.get("rule") for e in ev if e.get("fired")}


def rank_strategies(
    module1: dict,
    enrichment_design: dict | None = None,
    unselected_reference: dict | None = None,
    surrogate_design: dict | None = None,
) -> list[Strategy]:
    """Rank module 1's candidate strategies, attaching simulated design consequences.

    ``enrichment_design`` / ``unselected_reference`` / ``surrogate_design`` are
    the corresponding entries from :mod:`simulate` output, or ``None`` when the
    simulation was not run.
    """
    fired = _fired_rules(module1)
    out: list[Strategy] = []

    for entry in module1.get("salvage_strategies", []) or []:
        name = entry.get("strategy", "(unnamed)")
        rules = [r for r in _SUPPORTING_RULES.get(name, ()) if r in fired]
        used = entry.get("used")

        if rules and used:
            tier = TIERS[0]
        elif rules or used:
            tier = TIERS[1]
        elif name == "molecule_modification":
            tier = TIERS[3]
        else:
            tier = TIERS[2]

        s = Strategy(
            strategy=name,
            tier=tier,
            used_historically=used,
            module1_evidence=entry.get("evidence", ""),
            supporting_rules=rules,
            next_experiment=_NEXT_EXPERIMENT.get(name, ""),
            would_be_undermined_by=_UNDERMINED_BY.get(name, ""),
        )

        if name == "biomarker_enrichment_new_inclusion_criteria" and enrichment_design:
            s.design_consequence = enrichment_design
        elif name == "clinical_surrogate_enrichment" and surrogate_design:
            s.design_consequence = surrogate_design
        elif name == "narrower_indication" and enrichment_design:
            s.design_consequence = enrichment_design
            s.notes.append(
                "Shares the enriched design's arithmetic: restricting the indication and requiring the "
                "biomarker enrol the same population here."
            )

        if not rules and used:
            s.notes.append(
                "Module 1 records this lever as used historically, but no diagnosis rule in this asset "
                "supports it directly."
            )
        out.append(s)

    if unselected_reference:
        for s in out:
            if s.strategy == "biomarker_enrichment_new_inclusion_criteria":
                s.notes.append(
                    "Compare against re-running unselected: "
                    f"power {unselected_reference.get('simulated_power')} at n="
                    f"{unselected_reference.get('total_randomized')} and responder fraction "
                    f"{unselected_reference.get('responder_fraction')}."
                )

    order = {t: i for i, t in enumerate(TIERS)}
    out.sort(key=lambda s: (order[s.tier], -len(s.supporting_rules), s.strategy))
    for i, s in enumerate(out, start=1):
        s.rank = i
    return out
