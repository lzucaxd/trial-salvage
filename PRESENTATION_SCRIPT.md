# Presentation script (verbatim)

Everything in a `>` block is said word for word. **Bold** is a stage direction, not spoken.
Deck: `trial_salvage_deck.html`, full screen, scroll position is the slide.

904 spoken words: about **5:40 at a steady pace, 5:10 if you move**. Three lines are marked
*(cut if long)* and take it to 5:28. Read it out loud once with a timer before you present, because
the only reliable number is your own pace.

Negative results are in `trial_salvage_limitations.html`. Don't open it unless a judge asks.

| | Speaker | Section | Words | At 160 wpm |
|---|---|---|---|---|
| 1 | **Luca** | The problem and the money | 158 | 0:59 |
| 2 | **Daniel** | Why it happens | 121 | 0:45 |
| 3 | **Ramin** | The framework and the models | 208 | 1:18 |
| 4 | **Tianhao** | The match, the trial, the close | 417 | 2:36 |

---

## 1. Luca — 158 words

**Header on screen. Start before the room settles.**

> A clinical trial reports one number for everybody in it.

> So a drug that works in a quarter of patients and does nothing in the rest averages out to
> nothing. The trial fails. The drug gets shelved.

> It didn't fail. It was measured on the wrong people.

**Scroll to section 01.**

> And it's the most expensive mistake in medicine. A cancer survival trial runs about
> **79 million dollars**, **41,413 dollars** a patient. Every patient
> who couldn't respond is that much money spent making your own result worse. Only
> **43 percent** of these trials succeed.

> *(cut if long)* So there's a shelf of drugs that probably work, and nobody knows who for.

**Scroll to the four header numbers. Leave them up.**

> We built something that reads a failed trial and works out the way forward. On our main case,
> **6 out of 6** decisions right, and a trial designed within
> **6 patients** of the one that got the drug
> approved. The field took **12 years**.

> Daniel, why does this happen at all?

---

## 2. Daniel — 121 words

**Section 02. The network is already moving. Don't explain the buttons.**

> This is a real protein interaction network. Growth signal comes in here, runs down the chain, and
> at the bottom it tells the cell to divide.

**Click "EGFR-driven tumour". Let one pulse travel.**

> In this tumour the signal starts at EGFR.

**Click "+ gefitinib". Wait for the caption.**

> Gefitinib blocks EGFR. It's sitting right on the route, so the signal stops. This patient is the
> whole reason the drug exists.

**Click "KRAS-driven tumour". Leave gefitinib on.**

> Same drug, same dose, different tumour. This one starts further down the chain.

**Say nothing while the pulse runs past the blocked node.**

> It's blocking something this tumour isn't using. Nothing happens, and the patient still gets
> every side effect.

> So in one patient the drug is excellent, in the other it's useless and harmful. Put them in the
> same trial, take the average, and the drug looks dead.

> Ramin, how do we read that?

---

## 3. Ramin — 208 words

**Section 03. Point at the top band.**

> Everything across the top is a real data source or a model. **11** of them running,
> feeding the five steps along the bottom.

> Clinical side: the drug's whole trial history from the registry, plus the abstracts.
> **390 trials**, **17 effect estimates**, each one checked to make sure it really
> appears in the paper we cite.

> Protein side: **ESM-1v**, an ensemble of five language models at 650 million parameters each. We
> scored **147,972 amino acid substitutions** across 6 genes.

> And we benchmark it rather than trust it. On EGFR: ESM-1v **0.802**,
> PolyPhen-2 **0.793**, SIFT **0.712**, same variants. Ground
> truth is ClinVar, **2,694 pathogenic**, **9,709
> benign**.

**Point at the two dashed boxes.**

> Those two are dashed deliberately. ESM2 is loaded in the same code but produced nothing we're
> showing you, and AlphaGenome isn't done. Better to label it than let you assume.

**Follow the dot along the bottom row.**

> Collect the evidence. Diagnose the failure. Score who can respond. Rank the ways out. Design the
> trial.

> On gefitinib, **5 of 5** diagnostic rules fire. Verdict: population dilution. It
> worked in a subgroup and the full population washed it out.

> And the output is a ranked list, never a probability that the rescue works. That number would get
> read as a promise, and this evidence can't support one.

> Tianhao, is any of it right?

---

## 4. Tianhao — 417 words

**Section 04, the match table.**

> Gefitinib was approved in 2003, failed to show a survival benefit, and got
> pulled off the market.

> We asked the pipeline one question. Which ways out does this data support? Then we looked at what
> the field actually did.

**Walk the table by column.**

> Five routes it said were worth trying. Enrol only marker-positive patients. Use a clinical
> stand-in when the test isn't available. Narrow the disease definition. Change the endpoint. Treat
> earlier. The field used all five.

> One route it said the evidence didn't support. Change the molecule. Nobody tried it.

> **6 out of 6.**

**Timeline.**

> And here's the ordinary way. Unselected approval 2003. Restricted
> 2005. Marker-positive only 2009. Withdrawn 2012. Re-approved with a companion test
> 2015. **12 years**, and the evidence
> was there by 2009.

**Section 05. Let the curves draw before you talk.**

> Now the part I didn't expect. Re-run that failed trial and the chance of success is zero. Not
> low. Zero, at 800 patients and every size we tested.

> Because marker-negative patients do *worse* on the drug. Hazard ratio **2.85** against
> **0.48**. Every extra patient pushes the average further the wrong way. No sample size fixes
> it.

> So selection isn't efficiency. It's impossible versus **100 patients** at
> **89 percent** power. The trial that won the approval enrolled
> **106**, and our simulation had never heard of it.

**Section 06. Fast.**

> It also says when not to bother. Onartuzumab had the same evidence shape and the sponsor ran
> **499 patients** on it. If that effect were real, the trial should have
> returned **0.28 to 0.47**. It returned **1.27**,
> worse on the drug. Outside the whole range, and checkable before anyone enrolled.

**Section 07. Drag one slider while you talk.**

> Last thing, and it's the part I'd want to be questioned on. We hand-built a benchmark: **40 real
> cases** where a drug failed a trial and somebody retried it. Each case carries both registry IDs,
> the paper we read the outcome from, and a label for what motivated the retry.

> **38** have settled outcomes. Where the retry was driven by a planned or mechanistic
> signal, **13 of
> 22** worked. Where it was driven by a subgroup someone
> spotted afterwards, **3 of 16**.
> Odds ratio **6**, p of **0.0202**.

> *(cut if long)* And we read those labels out of the full papers by hand, knowing the outcomes. So
> it's a direction, not a calibrated rate.

**Stop touching the laptop. Look at them.**

> A failed phase 3 isn't a dead drug. It's an experiment that answered a question nobody meant to
> ask.

> We can read that answer. And on the one case where history already told us the right move, we got
> it right 6 out of 6.

> Thank you.

---

## Judge questions, verbatim

**"Isn't this hindsight? You already knew gefitinib worked."**

> Two things. It only sees evidence published before each decision point, so it isn't reading the
> answer. And it isn't scored on guessing the outcome, it's scored on which route the evidence
> supported. On onartuzumab, where the retry failed, the same rules say the subgroup estimate was
> refutable in advance. Same pipeline, opposite call.

**"Did you actually run ESM, or just cite it?"**

> We ran ESM-1v, five-model ensemble, masked marginals,
> 147,972 substitutions across 6 genes. The score tables are
> committed so it reproduces offline. ESM2 is loaded in the same harness but nothing we showed you
> uses it, which is why it's dashed.

**"Where's AlphaGenome?"**

> Not done. The weights are licence-gated and that lane is still a stub. gnomAD and cBioPortal
> carry the genomic side today. We marked it unfinished rather than implying it ran.

**"Where does the marker prevalence come from?"**

> We sweep it, which is why that chart is a curve and not a point. Tying it to a defined screened
> population is the next piece of work, and it's in our limitations document.

**"Does the protein model actually help?"**

> On two of the six genes we tested. On two others it loses to predictors from the 1990s, and we
> report that per gene instead of averaging it away.

**"How did you build that benchmark? Who decided what counts as a planned signal?"**

> We did, by hand, and here's exactly how. We went looking for cases where a drug failed a trial
> and somebody retried it, and we found **40**. Every row carries the registry ID of the failed
> trial, the registry ID of the retry, the lever they changed, the PMID of the paper we read the
> outcome from, and a confidence flag on our own curation. **38** have a settled
> outcome, and two we marked contested or pending and excluded.

> The label you're asking about has two values. Planned or mechanistic means the retry was
> motivated either by a subgroup analysis that was specified in advance, or by a mechanism
> established independently of the failed trial. Post-hoc subgroup means somebody went looking
> after the trial missed. Across all 40 that split
> **23 to 17**, and among the
> **38** with settled outcomes,
> **22 to 16** — which are the
> denominators I just quoted.

> Now the two weaknesses. First, we assigned those labels with the outcomes sitting in the same
> spreadsheet, so we cannot claim we were blind. Second, that distinction lives in protocols and
> full texts, not abstracts, and we know that because we pre-registered a rule to recover it
> automatically and it failed. So the honest reading is: this is a direction, on a small sample,
> from labels a human assigned with hindsight. It is not a calibrated rate.

> What does make it more than an artefact of one biology is that it survives removing the whole
> EGFR lung cancer cluster. Four cases out, and the contrast strengthens rather than collapses:
> **10 of 19**
> against **2 of 15**, odds ratio
> **7.222**. We ran that same test on another one of our results and it did collapse,
> so we report both.

**"What's the model behind the dollar figures?"**

> It's deliberately simple, and it's on the screen so you can push it around. Four inputs: cost per
> trial, how many retries you're considering, what fraction of them rest on an after-the-fact
> subgroup, and the two success rates.

> Spend per success is just cost divided by the probability of success. If you retry everything,
> your success rate is the mix of the two, weighted by that fraction. If you only retry the
> well-supported ones you run fewer trials, but every one you run carries the higher rate, so the
> spend per success drops to cost divided by that rate alone.

> The fourth number is the one that matters for a portfolio. It's what you spend on retries we'd
> have advised against, that then fail. Trials times the post-hoc share, times one minus their
> success rate, times cost.

> What it is not: a forecast. It assumes one pivotal trial per attempt, ignores the cost of
> developing the assay and doing the failure analysis, and inherits every weakness of those
> 38 cases. The direction is the result. The dollars are illustration.

**"What didn't work?"**

> We pre-registered a rule to detect whether a subgroup finding was planned or found afterwards,
> committed it before extracting any data, and tested it blind on abstracts. It failed. Abstracts
> almost never say. So that 38-case result uses labels we read from full texts by
> hand, and we say so on the slide.

**"How much of this is automated?"**

> The whole chain runs offline from committed data with one command,
> 115 tests pass, and every number on that screen is injected from the pipeline
> output. Nothing you saw was typed in by a human.

---

## Notes

- Don't read a number off the screen. It's already there. Say what it means.
- Both animations run without clicks. Daniel's section needs them.
- Cut the two *(cut if long)* lines first.
- Laptop dies: **6 of 6** ·
  **100 against 106** ·
  **12 years** · **0.48 against 2.85**.
