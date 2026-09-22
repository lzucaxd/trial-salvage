"""Minimal ClinicalTrials.gov v2 API client (https://clinicaltrials.gov/data-api/api)."""
from __future__ import annotations

import time

import requests

BASE = "https://clinicaltrials.gov/api/v2/studies"
ACTIVE = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "ENROLLING_BY_INVITATION", "NOT_YET_RECRUITING"}


def get_study(nct: str, timeout: int = 60) -> dict:
    r = requests.get(f"{BASE}/{nct}", timeout=timeout)
    r.raise_for_status()
    return r.json()


def search_studies(query_intr: str | None = None, filter_advanced: str | None = None,
                   fields: list[str] | None = None, page_size: int = 1000, pause: float = 0.15) -> list[dict]:
    """Page through all results of a search. Returns raw study dicts."""
    out, token = [], None
    while True:
        prm = {"pageSize": page_size}
        if query_intr:
            prm["query.intr"] = query_intr
        if filter_advanced:
            prm["filter.advanced"] = filter_advanced
        if fields:
            prm["fields"] = ",".join(fields)
        if token:
            prm["pageToken"] = token
        r = requests.get(BASE, params=prm, timeout=180)
        r.raise_for_status()
        js = r.json()
        out.extend(js.get("studies", []))
        token = js.get("nextPageToken")
        if not token:
            return out
        time.sleep(pause)


def flatten_study(s: dict) -> dict:
    """One flat row per study: design, status, eligibility text, results flag, references."""
    p = s.get("protocolSection", {})
    ident, st = p.get("identificationModule", {}), p.get("statusModule", {})
    des, arms = p.get("designModule", {}), p.get("armsInterventionsModule", {})
    spon = p.get("sponsorCollaboratorsModule", {}).get("leadSponsor", {})
    refs = p.get("referencesModule", {}).get("references", []) or []
    locs = p.get("contactsLocationsModule", {}).get("locations", []) or []
    return {
        "nct": ident.get("nctId"),
        "title": ident.get("briefTitle"),
        "official_title": ident.get("officialTitle"),
        "status": st.get("overallStatus"),
        "why_stopped": st.get("whyStopped"),
        "start": (st.get("startDateStruct") or {}).get("date"),
        "completion": (st.get("completionDateStruct") or {}).get("date"),
        "results_first_posted": (st.get("resultsFirstPostDateStruct") or {}).get("date"),
        "phase": "|".join(des.get("phases", []) or []),
        "allocation": (des.get("designInfo") or {}).get("allocation"),
        "masking": ((des.get("designInfo") or {}).get("maskingInfo") or {}).get("masking"),
        "enrollment": (des.get("enrollmentInfo") or {}).get("count"),
        "enrollment_type": (des.get("enrollmentInfo") or {}).get("type"),
        "conditions": "|".join(p.get("conditionsModule", {}).get("conditions", []) or []),
        "interventions": "|".join(i.get("name", "") for i in arms.get("interventions", []) or []),
        "sponsor": spon.get("name"),
        "sponsor_class": spon.get("class"),
        "primary_outcomes": "|".join(o.get("measure", "") for o in p.get("outcomesModule", {}).get("primaryOutcomes", []) or []),
        "eligibility": (p.get("eligibilityModule", {}) or {}).get("eligibilityCriteria") or "",
        "countries": "|".join(sorted({loc.get("country", "") for loc in locs if loc.get("country")})),
        "n_pmids": sum(1 for r in refs if r.get("pmid")),
        "pmids": "|".join(r["pmid"] for r in refs if r.get("pmid")),
        "has_results": bool(s.get("hasResults")),
    }


def posted_outcomes(s: dict) -> list[dict]:
    """Flatten the results section outcome measures (if posted) into rows."""
    rs = s.get("resultsSection") or {}
    rows = []
    for o in (rs.get("outcomeMeasuresModule") or {}).get("outcomeMeasures", []) or []:
        groups = {g["id"]: g.get("title") for g in o.get("groups", []) or []}
        for cls in o.get("classes", []) or []:
            for cat in cls.get("categories", []) or []:
                for m in cat.get("measurements", []) or []:
                    rows.append({"type": o.get("type"), "title": o.get("title"), "unit": o.get("unitOfMeasure"),
                                 "class": cls.get("title"), "arm": groups.get(m.get("groupId")),
                                 "value": m.get("value"), "lower": m.get("lowerLimit"), "upper": m.get("upperLimit")})
        for a in o.get("analyses", []) or []:
            rows.append({"type": o.get("type"), "title": o.get("title"), "unit": "analysis",
                         "class": a.get("statisticalMethod"), "arm": a.get("paramType"),
                         "value": a.get("paramValue"), "lower": a.get("ciLowerLimit"), "upper": a.get("ciUpperLimit"),
                         "p": a.get("pValue")})
    return rows
