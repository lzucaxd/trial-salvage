# Presentation script (verbatim)

`>` blocks are said word for word. **Bold** is a stage direction, not spoken.
Deck: `docs/index.html` full screen; scroll position is the slide.

| | Speaker | Section | Words | At 165 wpm |
|---|---|---|---|---|
| 1 | **Luca** | The problem and the money | 101 | 0:37 |
| 2 | **Daniel** | Why it happens | 85 | 0:31 |
| 3 | **Ramin** | The framework and the models | 137 | 0:50 |
| 4 | **Tianhao** | Both cases, the trial, the close | 326 | 1:59 |

**649 spoken words, about 4:00.** That is deliberate: the animations and the pauses in
Daniel's section eat the rest of a 5-minute slot. Don't rush to fill it.

Negative results: `docs/limitations.html`. Don't open it unless asked.

---

## 1. Luca

**Header. Start before the room settles.**

> A clinical trial reports one number for everybody in it.

> So a drug that works in a quarter of patients and does nothing in the rest averages out to
> nothing. The trial fails. The drug gets shelved. It didn't fail. It was measured on the wrong
> people.

**Section 01.**

> And it's the most expensive mistake in medicine. A cancer survival trial costs about
> **79 million dollars**, **41,413 dollars** a patient. Only
> **43 percent** succeed.

**Back to the four header numbers.**

> We built something that reads a failed trial and works out the way forward. Two drug classes so
> far. On both, every call correct.

> Daniel, why does this happen?

---

## 2. Daniel

**Section 02. Network already moving.**

> Real protein interaction network. Growth signal comes in here, runs down the chain, tells the cell
> to divide.

**Click "EGFR-driven tumour". One pulse.**

> This tumour signals from EGFR.

**Click "+ gefitinib".**

> Gefitinib blocks EGFR, right on the route. Signal stops. This patient is why the drug exists.

**Click "KRAS-driven tumour". Leave the drug on. Let it run past.**

> Same drug, different tumour. This one starts further down.

**Silence while the pulse goes through.**

> It's blocking something this tumour isn't using. Nothing happens, and the patient still gets every
> side effect.

> Put both patients in one trial, take the average, and the drug looks dead.

> Ramin, how do we read that?

---

## 3. Ramin

**Section 03. Point at the top band.**

> Everything along the top is a real model or data source. **11** of them, feeding the
> five steps below.

> Trials and abstracts from the registry and PubMed: **390 trials**, **17 effect
> estimates**, each checked to appear in the paper we cite.

> Protein side: **ESM-1v**, five language models at 650 million parameters,
> **147,972 substitutions** across 6 genes. We benchmark it
> rather than trust it: **0.802** against PolyPhen-2's
> **0.793** and SIFT's **0.712**, same variants. Ground truth
> is ClinVar.

**Point at the dashed boxes.**

> Those two are dashed on purpose. ESM2 is loaded but produced nothing we're showing. AlphaGenome
> isn't done.

**Follow the dot.**

> Collect. Diagnose. Score who responds. Rank the ways out. Design the trial. On gefitinib,
> **5 of 5** rules fire: population dilution.

> The output is a ranked list, never a probability the rescue works. That would get read as a
> promise.

> Tianhao, is it right?

---

## 4. Tianhao

**Section 04, match table.**

> Gefitinib: approved 2003, missed on survival, pulled from the market. We asked
> which ways out the evidence supported, then checked what the field did.

> Five it said were worth trying: marker-positive only, a clinical stand-in, narrower disease,
> new endpoint, treat earlier. The field used all five. One it said wasn't supported: change the
> molecule. Nobody tried it. **6 out of 6**.

**Timeline.**

> Unselected approval 2003, restricted 2005, marker-only 2009, withdrawn 2012,
> re-approved 2015. **12 years**, and the evidence was
> there by 2009.

**Section 05, CETP. This is the new one.**

> Then we ran the whole thing end to end on a different disease area. **dalcetrapib**, a
> CETP inhibitor, failed **15,871 patients**.

> It ranked new endpoint first. The sponsor's live trial switched its endpoint to heart attack
> alone, the one component that held at **0.79**. It ranked narrower
> indication second. **Last Sunday**, Europe approved a CETP drug on exactly that.

> It ranked gene-selection third, not first. That trial was run, in
> **6,147 patients**, and missed at **0.88**. And it said don't
> touch the molecule. Nobody did.

> Four for four. One asset, and only the approval came after we scored it, so that's the one
> independent row. I'm not calling it a blind test.

**Section 06. Let the curves draw.**

> Back to gefitinib. Re-run that failed trial and the chance of success is zero. At
> 800 patients, at every size we tested.

> Because marker-negative patients do *worse* on the drug: **2.85** against **0.48**. Every
> extra patient pushes the average further the wrong way.

> So selection isn't efficiency. It's impossible versus **100 patients** at
> **89 percent** power. The trial that won the approval enrolled
> **106**. Our simulation had never heard of it.

**Section 07. Fast.**

> It also says when not to bother. Onartuzumab, same evidence shape,
> **499 patients** spent. Should have returned
> **0.28 to 0.47**; returned **1.27**, worse on the
> drug. Checkable before anyone enrolled.

**Stop touching the laptop.**

> A failed phase 3 isn't a dead drug. It's an experiment that answered a question nobody meant to
> ask.

> Two drug classes, two disease areas, ten out of ten calls. Thank you.

---

## Judge questions, verbatim

**"Isn't this hindsight?"**

> It only sees evidence published before each decision point, and it's scored on which route the
> evidence supported, not on guessing outcomes. On onartuzumab, where the retry failed, the same
> rules say the subgroup was refutable in advance. On CETP it demoted gene-selection, and
> gene-selection is the one that missed.

**"The CETP case — how independent is it really?"**

> Partly, and I'll be precise. Four rows. Three were knowable when we scored: the endpoint switch is
> in the registry, the failed gene-selected trial published in 2022, and the chemistry is public.
> One was not: the European approval came on **21 September 2026**, after scoring. So it's one
> independent row and three consistency checks. And in a 44-asset cohort that same
> narrower-indication lever showed no discriminative power at all, P of 1.0. That's why I said it
> isn't a blind test.

**"Did you actually run ESM?"**

> ESM-1v, five-model ensemble, masked marginals, **147,972 substitutions** over
> 6 genes. Score tables are committed, so it reproduces offline. ESM2 is loaded in
> the same harness but nothing we showed uses it, which is why it's dashed.

**"Where's AlphaGenome?"**

> Not done. Weights are licence-gated and that lane is a stub. gnomAD and cBioPortal carry the
> genomic side today.

**"How did you build the retry benchmark?"**

> By hand: **40** cases where a drug failed and someone retried it, each with both registry IDs, the
> paper we read the outcome from, and a confidence flag. **38** have settled outcomes.
> Planned or mechanistic signal, **13 of
> 22** worked; after-the-fact subgroup,
> **3 of 16**.

> Two weaknesses. We assigned those labels with the outcomes in the same spreadsheet, so not blind.
> And the distinction lives in protocols, not abstracts, which we know because we pre-registered a
> rule to recover it automatically and it failed. It survives dropping the whole EGFR cluster
> though: **10 of
> 19** against
> **2 of 15**.

**"What's the model behind the dollar figures?"**

> Spend per success is cost divided by probability of success. Retry everything and your rate is the
> mix of the two, weighted by how many rest on a weak signal. Retry only the well-supported and you
> run fewer trials but each carries the higher rate. The fourth number is what you burn on retries
> we'd have advised against that then fail. It's a decision model, not a forecast.

**"Where does marker prevalence come from?"**

> We sweep it, which is why that chart is a curve. Tying it to a defined screened population is next
> and it's in the limitations doc.

**"What didn't work?"**

> Our pre-registered rule for telling planned from after-the-fact subgroups, tested blind on
> abstracts. It failed, because abstracts don't say. Also, the protein model only clears its own
> applicability gate on two of six genes.

---

## Notes

- Don't read numbers off the screen. Say what they mean.
- Both animations run without clicks. Daniel's needs them.
- "Last Sunday" means **21 September 2026**. Update that phrase if you present later.
- Laptop dies: **6 of 6** · **4 of 4 on CETP** ·
  **100 vs 106** · **0.48 vs 2.85**.
