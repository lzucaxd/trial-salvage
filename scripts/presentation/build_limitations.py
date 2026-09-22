"""Generate the companion document: limitations and negative results.

Kept out of the presentation deliberately. This is the document to hand to anyone
who asks what does not work, and the one to read before trusting a number from the
deck. Same data bundle, so the figures agree with the deck by construction.

    python build_bundle.py && python build_limitations.py
"""

from __future__ import annotations

import json
import pathlib

DATA = json.loads(pathlib.Path("deck_data.json").read_text())
OUT = pathlib.Path("trial_salvage_limitations.html")

BE = DATA["blind_eval"]
AD = DATA["benchmark"]["provenance_contrast"]["all_decided"]
CR = DATA["benchmark"]["provenance_contrast"]["cluster_removed"]
M2 = DATA["module2"]["cross_case"]
G = DATA["cases"]["gefitinib"]
O = DATA["cases"]["onartuzumab"]

CSS = """
:root{--bg:#0f1117;--panel:#181b25;--line:#2a2f3d;--ink:#eef0f6;--dim:#a8aec2;
  --faint:#6d7488;--bad:#ff6b7a;--warn:#ffc043;--good:#5fb3ff;
  --mono:ui-monospace,SFMono-Regular,Menlo,monospace}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:16.5px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,sans-serif}
.wrap{max-width:860px;margin:0 auto;padding:60px 28px 100px}
h1{font-size:34px;letter-spacing:-.025em;margin:0 0 10px;line-height:1.1}
.sub{color:var(--faint);font-size:15px;margin:0 0 8px}
h2{font-size:22px;margin:52px 0 6px;letter-spacing:-.015em;padding-top:22px;
  border-top:1px solid var(--line)}
h3{font-size:16.5px;margin:26px 0 6px;color:var(--ink)}
p,li{color:var(--dim);max-width:70ch}
li{margin:7px 0}
code{font-family:var(--mono);font-size:13.5px;color:var(--good)}
table{width:100%;border-collapse:collapse;margin:16px 0;font-size:14.5px}
th,td{text-align:left;padding:9px 10px;border-bottom:1px solid var(--line)}
th{color:var(--faint);font-size:12px;text-transform:uppercase;letter-spacing:.06em}
td.num,th.num{text-align:right;font-family:var(--mono)}
.box{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  padding:18px 22px;margin:20px 0}
.box.bad{border-left:3px solid var(--bad)}
.box.warn{border-left:3px solid var(--warn)}
.box p{margin:0;color:var(--ink)}
.tag{display:inline-block;font-family:var(--mono);font-size:11px;padding:3px 8px;
  border-radius:999px;border:1px solid var(--line);color:var(--dim)}
.tag.bad{color:var(--bad);border-color:#6d2a33}
.tag.warn{color:var(--warn);border-color:#6d5520}
.tag.good{color:var(--good);border-color:#2a5580}
.lead{font-size:18px;color:var(--ink);max-width:62ch}
footer{margin-top:60px;padding-top:22px;border-top:1px solid var(--line);
  color:var(--faint);font-size:13.5px}
"""

m2_rows = "".join(
    f"<tr><td><code>{r['selection_gene']}</code></td><td>{r['drug']}</td>"
    f"<td class='num'>{'--' if r.get('esm_matched') in (None, '') else format(float(r['esm_matched']), '.3f')}</td>"
    f"<td class='num'>{'--' if r.get('best_classical') in (None, '') else format(float(r['best_classical']), '.3f')}</td>"
    f"<td><span class='tag {'good' if r['verdict'] == 'rank_residues_only' else 'bad' if r['verdict'] == 'do_not_rank' else 'warn'}'>"
    f"{r['verdict'].replace('_', ' ')}</span></td></tr>"
    for r in M2)

_ORDER = ["retry_supported", "retry_weak", "not_supported", "primary_not_missed", "not_evaluable"]
_BEV = {r["verdict"]: r for r in BE["verdict_table"]}
blind_rows = "".join(
    f"<tr><td><code>{v.replace('_', ' ')}</code></td><td class='num'>{_BEV[v]['n']}</td>"
    f"<td class='num'>{_BEV[v]['success']}</td><td class='num'>{_BEV[v]['fail']}</td>"
    f"<td class='num'>{'--' if _BEV[v]['rate'] is None else format(_BEV[v]['rate'] * 100, '.0f') + '%'}</td></tr>"
    for v in _ORDER if v in _BEV)

HTML = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trial Salvage: limitations and negative results</title>
<style>{CSS}</style></head><body><div class="wrap">

<h1>Limitations and negative results</h1>
<p class="sub">Companion to the presentation. <code>{DATA['meta']['repo']}</code> @
<code>{DATA['meta']['head']}</code> &middot; generated {DATA['meta']['generated']}</p>

<p class="lead">Three of the four parts of this pipeline report a limit on their own usefulness.
This document collects those limits, the results that came out negative, and the things we did not
finish. Numbers here come from the same pipeline outputs as the deck.</p>

<h2>1. The provenance rule does not survive automation</h2>
<p>The deck reports that retries built on a planned or mechanistic signal succeeded
{AD['prespecified_or_mechanistic']['success_rate'] * 100:.0f}% of the time against
{AD['post_hoc_subgroup']['success_rate'] * 100:.0f}% for retries built on an after-the-fact
subgroup ({AD['n_pairs']} cases, Fisher p = {AD['fisher_p']}, odds ratio {AD['odds_ratio']}).
That contrast strengthens when the four EGFR-mutant lung cancer cases are removed
(odds ratio {CR['odds_ratio']}, p = {CR['fisher_p']}), so it is not carried by one biology.</p>

<p><strong>But those provenance labels were hand-coded from full texts and trial protocols.</strong>
We pre-registered a rule to recover them automatically, committed it before extracting any
evidence, ran it over {BE['n_abstracts']} abstracts published before each retry opened, and only
then joined the outcomes.</p>

<table><thead><tr><th>Pre-registered verdict, abstracts only</th><th class="num">retries</th>
  <th class="num">worked</th><th class="num">failed</th><th class="num">rate</th></tr></thead>
<tbody>{blind_rows}</tbody></table>

<div class="box bad"><p>The pre-registered ordering is falsified. We predicted
<code>retry_supported &gt; retry_weak &ge; not_supported</code> and the top two tiers came out
inverted. Read from abstracts alone, the rule does not separate retries that worked from retries
that failed.</p></div>

<p>The cause is not subtle: abstracts almost never state whether a subgroup analysis was planned in
advance. Most favourable findings come back as an unspecified subgroup, which the rule bins with
"after the fact". The distinction that carries the result lives in protocols and full texts, which
we do not parse.</p>

<h3>What did survive</h3>
<ul>
  <li><strong>The abandon call.</strong> Assets with no favourable heterogeneity signal anywhere in
  the failed trial: {BE['any_vs_none']['none_fail']} of {BE['any_vs_none']['none_n']} retries
  failed. Advising against the spend is the claim this pipeline supports best.</li>
  <li><strong>A coarser signal.</strong> Any favourable subgroup or secondary finding against none:
  {BE['any_vs_none']['any_success']}/{BE['any_vs_none']['any_n']} versus
  {BE['any_vs_none']['none_success']}/{BE['any_vs_none']['none_n']}, Fisher
  p = {BE['any_vs_none']['fisher_p']}. Right direction, too small to lean on.</li>
</ul>
<p>Full analysis and cause breakdown: <code>{BE['doc']}</code>. Status: {BE['status']}.</p>

<h2>2. The protein model is unusable on most of the genes we tried</h2>
<p>We tested whether a protein language model can rank variants well enough to support patient
selection, against classical predictors, on six selection genes. It is cleared for residue-level
use on two of the six.</p>

<table><thead><tr><th>Gene</th><th>Drug</th><th class="num">model AUROC</th>
  <th class="num">best classical</th><th>verdict</th></tr></thead>
<tbody>{m2_rows}</tbody></table>

<div class="box warn"><p>Only three genes had enough labelled variants for a head-to-head
comparison. On the gene the method was first built against it wins by 0.009 AUROC
(0.802 against 0.793). On the other two it loses to predictors from the 1990s, by 0.044 and 0.170.
We report the applicability gate per gene rather than an average across them.</p></div>

<h2>3. The genomic stratification result does not generalise</h2>
<p>Module 3's verdict separated outcomes at p = 0.015 across the benchmark. Removing the four
EGFR-mutant lung cancer cases took that to p = 0.39. One biology was carrying it. We ran the same
leave-the-cluster-out test on every result in the pipeline after finding this.</p>

<h2>4. Limits on the trial simulation</h2>
<ul>
  <li><strong>Marker prevalence is swept, not measured.</strong> The designed sample size depends on
  what share of screened patients carry the marker. We show a range because no module yet hands us
  a prevalence tied to a defined screened population.</li>
  <li><strong>The assay is assumed perfect and nobody drops out.</strong> Real screening has false
  negatives and real trials lose patients, so the screening burden we report is a floor.</li>
  <li><strong>Hazard ratios are taken as given.</strong> We never convert them into response
  probabilities, and we never derive them from protein or genome model scores.</li>
  <li><strong>No probability of rescue is produced anywhere.</strong> Strategies are placed in
  visible tiers. The evidence cannot support a number, and a number would be read as a forecast.</li>
</ul>

<h2>5. The gefitinib result is not an independent test</h2>
<p>Our replication check compares a trial's observed result against what a prior estimate implies.
For gefitinib it returns <code>{G['retrospective']['verdict']}</code>, and that is the correct
answer rather than a failure: the estimate we would check against was measured inside the very
trial we would be checking, with both marker groups present. The check refuses circular cases
instead of scoring them as agreement.</p>
<p>The onartuzumab case is a real test, because its prior estimate came from an earlier trial:
verdict <code>{O['retrospective']['verdict']}</code>.</p>

<h2>6. Benchmark caveats</h2>
<ul>
  <li>{AD['n_pairs']} decided cases is small. The success rates have wide intervals.</li>
  <li>Provenance labels were assigned with the outcomes visible in the same file.</li>
  <li>Nine cases were not primary-endpoint failures at all, but regulatory decisions or a survival
  miss after a positive primary. The benchmark needs a <code>failure_type</code> column before the
  provenance test can be re-run cleanly.</li>
  <li>No prospective validation. Every case here has a known outcome.</li>
</ul>

<h2>7. Not finished</h2>
<ul>
  <li>Prevalence handoff from the genomic module to the trial design, with an agreed definition of
  the screened population.</li>
  <li><code>failure_type</code> on the benchmark, then re-run the blind evaluation.</li>
  <li>Full-text extraction, which is where the provenance information actually lives.</li>
</ul>

<div class="box"><p>We would rather show a pipeline that reports where it stops working than one
that returns a confident score for everything.</p></div>

<footer>
<p>{DATA['meta']['tests']} tests pass; lint clean; the whole chain runs offline from committed
data. Trial data from ClinicalTrials.gov API v2 and PubMed E-utilities.</p>
</footer>
</div></body></html>
"""

OUT.write_text(HTML)
print(f"wrote {OUT} — {len(HTML) / 1024:.0f} KB")
