from trial_salvage.module1.eligibility import biomarker_selection

ISEL = """Inclusion: histologically confirmed non-small cell bronchogenic carcinoma; not suitable for chemotherapy;
WHO performance status 0-3."""
IPASS = """Inclusion: Stage IIIB/IV NSCLC with adenocarcinoma histology. Never smokers or light ex-smokers.
Exclusion: prior chemotherapy or targeted therapies such as EGFR and VEGF inhibitors."""
FLAURA = """Inclusion: locally advanced or metastatic NSCLC harbouring an EGFR mutation known to be associated with
EGFR-TKI sensitivity (exon 19 deletion or L858R)."""
WT = """Inclusion: EGFR wild-type NSCLC confirmed by local testing; EGFR mutation negative patients only."""


def test_unselected_trial_has_no_flags():
    f = biomarker_selection(ISEL, "EGFR")
    assert not f["mentioned"] and not f["required"]


def test_clinical_surrogate_enrichment_is_not_molecular_selection():
    f = biomarker_selection(IPASS, "EGFR")
    assert not f["required"], "IPASS mentions EGFR inhibitors in exclusion but does not require a mutation"


def test_mutation_required():
    f = biomarker_selection(FLAURA, "EGFR")
    assert f["mentioned"] and f["required"]


def test_wild_type_selection_is_not_required():
    f = biomarker_selection(WT, "EGFR")
    assert f["wt_or_negative"] and not f["required"]
