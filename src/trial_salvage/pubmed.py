"""PubMed E-utilities client with pacing (NCBI allows 3 req/s without an API key)."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET

import requests

EU = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def esearch(term: str, retmax: int = 5, retries: int = 3) -> list[str]:
    for _ in range(retries):
        j = requests.get(f"{EU}/esearch.fcgi", params={"db": "pubmed", "term": term, "retmax": retmax,
                                                      "retmode": "json"}, timeout=60).json()
        if "esearchresult" in j:
            return j["esearchresult"]["idlist"]
        time.sleep(1.0)  # rate-limit response has no esearchresult
    return []


def efetch_abstracts(pmids: list[str]) -> dict[str, dict]:
    """Return {pmid: {title, year, journal, abstract}} for a list of PMIDs."""
    if not pmids:
        return {}
    r = requests.get(f"{EU}/efetch.fcgi", params={"db": "pubmed", "id": ",".join(pmids),
                                                "rettype": "abstract", "retmode": "xml"}, timeout=90)
    r.raise_for_status()
    root = ET.fromstring(r.text)
    out = {}
    for art in root.findall(".//PubmedArticle"):
        pmid = art.findtext(".//PMID")
        out[pmid] = {
            "title": art.findtext(".//ArticleTitle"),
            "year": art.findtext(".//PubDate/Year") or art.findtext(".//PubDate/MedlineDate"),
            "journal": art.findtext(".//Journal/ISOAbbreviation"),
            "abstract": " ".join((t.text or "") for t in art.findall(".//AbstractText")),
        }
    return out


HR_PATTERN = re.compile(r"(?:\bHR\b|hazard ratio)[^.;]{0,120}?(\d\.\d+)[^.;]{0,90}", re.IGNORECASE)


def hr_candidates(abstract: str) -> list[str]:
    """Sentences fragments in an abstract that quote a hazard ratio — for human curation, not automatic use."""
    return [m.group(0).strip() for m in HR_PATTERN.finditer(abstract or "")]
