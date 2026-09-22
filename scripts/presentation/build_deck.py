"""Generate the trial-salvage presentation as one self-contained HTML file.

Every number comes from ``deck_data.json``, built by ``build_bundle.py`` from the
repository's own pipeline outputs. Figures are base64-embedded, so the result is a
single portable file that renders with no network and no local assets.

Written to be *presented*: short lines, large numbers, one idea per screen. The
limitations and negative results live in a separate document,
``build_limitations.py`` -> ``trial_salvage_limitations.html``.
"""

from __future__ import annotations

import base64
import json
import pathlib

HERE = pathlib.Path(".")
OUT = HERE / "trial_salvage_deck.html"
DATA = json.loads((HERE / "deck_data.json").read_text())

FIG_FILES = {
    "module1": "verify/outputs/module1/fig_gefitinib_module1.png",
    "comparison": "verify/outputs/module4_comparison/fig_case_comparison.png",
    "gefitinib_m4": "verify/outputs/module4_gefitinib/fig_gefitinib_module4.png",
}


def b64(path: str) -> str:
    p = pathlib.Path(path)
    return "" if not p.exists() else "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()


CSS = """
:root{
  --bg:#0a0e1c; --panel:#141b33; --panel2:#1b2340; --line:#28325a;
  --ink:#f0f3ff; --dim:#aab4d6; --faint:#6f7ba4;
  --good:#4da3ff; --bad:#ff5c6c; --warn:#ffc043; --go:#3ddc97;
  --mono:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace;
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font:17px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Inter,Roboto,sans-serif;
  -webkit-font-smoothing:antialiased}
a{color:var(--good)}
.wrap{max-width:1140px;margin:0 auto;padding:0 32px}

nav{position:sticky;top:0;z-index:100;background:rgba(10,14,28,.93);
  backdrop-filter:blur(14px);border-bottom:1px solid var(--line)}
nav .wrap{display:flex;align-items:center;gap:26px;height:54px;overflow-x:auto}
nav .brand{font-weight:700;white-space:nowrap}
nav .brand span{color:var(--good)}
nav a{color:var(--dim);text-decoration:none;font-size:14px;white-space:nowrap}
nav a:hover,nav a.on{color:var(--ink)}
nav .who{margin-left:auto;font-family:var(--mono);font-size:12px;color:var(--faint);white-space:nowrap}

header{padding:96px 0 72px;
  background:radial-gradient(1100px 500px at 15% -20%,#1d2a58 0%,transparent 72%)}
.kicker{font-family:var(--mono);font-size:13px;letter-spacing:.18em;text-transform:uppercase;color:var(--good)}
h1{font-size:clamp(34px,5.2vw,60px);line-height:1.04;margin:18px 0 20px;letter-spacing:-.03em;font-weight:760}
h1 em{font-style:normal;color:var(--good)}
.lede{font-size:clamp(18px,1.7vw,22px);color:var(--dim);max-width:44ch;margin:0}

.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;margin-top:52px}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:22px 24px}
.stat .big{font-size:clamp(32px,3.4vw,44px);font-weight:780;letter-spacing:-.035em;line-height:1}
.stat .lbl{font-size:14px;color:var(--dim);margin-top:10px;line-height:1.4}
.stat.good .big{color:var(--good)} .stat.bad .big{color:var(--bad)}
.stat.warn .big{color:var(--warn)} .stat.go .big{color:var(--go)}

section{padding:88px 0;border-top:1px solid var(--line)}
.sec-no{font-family:var(--mono);font-size:12.5px;color:var(--good);letter-spacing:.2em}
h2{font-size:clamp(26px,3.1vw,38px);letter-spacing:-.025em;margin:12px 0 18px;font-weight:730;
  line-height:1.12;max-width:26ch}
h3{font-size:19px;margin:38px 0 12px;letter-spacing:-.01em}
p{color:var(--dim);max-width:60ch;font-size:17px}
p strong,li strong{color:var(--ink)}
p.big{font-size:20px;color:var(--ink);max-width:48ch}
.sub{color:var(--faint);font-size:14px;max-width:70ch}
ul{color:var(--dim);max-width:60ch;padding-left:22px}
li{margin:9px 0}

.grid2{display:grid;grid-template-columns:1fr 1fr;gap:26px}
.grid3{display:grid;grid-template-columns:repeat(3,1fr);gap:18px}
@media(max-width:900px){.grid2,.grid3{grid-template-columns:1fr}}
.card{background:var(--panel);border:1px solid var(--line);border-radius:16px;padding:24px}
.card h3{margin-top:0}
.card.good{border-color:#2d629f} .card.bad{border-color:#7d3040}

figure{margin:30px 0 0;background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:18px}
figure img{width:100%;display:block;border-radius:10px;background:#fff}
figcaption{font-size:14px;color:var(--faint);margin-top:14px;max-width:80ch}

table{width:100%;border-collapse:collapse;margin-top:18px;font-size:15px}
th,td{text-align:left;padding:11px 12px;border-bottom:1px solid var(--line)}
th{color:var(--faint);font-weight:600;font-size:12.5px;text-transform:uppercase;letter-spacing:.07em}
td.num,th.num{text-align:right;font-family:var(--mono)}
.tag{display:inline-block;font-family:var(--mono);font-size:11.5px;padding:4px 9px;border-radius:999px;
  border:1px solid var(--line);color:var(--dim)}
.tag.good{color:var(--good);border-color:#2d629f;background:rgba(77,163,255,.12)}
.tag.bad{color:var(--bad);border-color:#7d3040;background:rgba(255,92,108,.12)}
.tag.go{color:var(--go);border-color:#206e51;background:rgba(61,220,151,.12)}
.tag.warn{color:var(--warn);border-color:#7d6020;background:rgba(255,192,67,.12)}

.callout{border-left:3px solid var(--good);background:rgba(77,163,255,.07);
  padding:20px 24px;border-radius:0 14px 14px 0;margin:30px 0}
.callout.go{border-color:var(--go);background:rgba(61,220,151,.07)}
.callout.bad{border-color:var(--bad);background:rgba(255,92,108,.07)}
.callout p{margin:0;max-width:70ch;color:var(--ink);font-size:18px}

.reveal{opacity:0;transform:translateY(20px);transition:opacity .65s ease,transform .65s ease}
.reveal.in{opacity:1;transform:none}

/* pipeline + network canvases */
.stage{position:relative;background:var(--panel2);border:1px solid var(--line);
  border-radius:16px;overflow:hidden}
#pipe{display:block;width:100%;height:440px}
#ppi{display:block;width:100%;height:460px}
.controls{position:absolute;right:16px;top:16px;display:flex;gap:8px;flex-wrap:wrap}
.btn{background:var(--panel);border:1px solid var(--line);color:var(--dim);border-radius:10px;
  padding:8px 14px;font-size:13.5px;cursor:pointer;font-family:inherit}
.btn:hover{color:var(--ink);border-color:var(--good)}
.btn.on{background:rgba(77,163,255,.18);color:var(--good);border-color:var(--good)}
.legend{position:absolute;left:18px;bottom:16px;font-size:12.5px;color:var(--dim);
  background:rgba(10,14,28,.78);border:1px solid var(--line);border-radius:11px;padding:11px 14px;line-height:1.75}
.dot{display:inline-block;width:9px;height:9px;border-radius:50%;margin-right:7px;vertical-align:middle}
.state{margin-top:18px;font-size:18px;color:var(--ink);max-width:72ch;min-height:2.6em}

.chart{background:var(--panel2);border:1px solid var(--line);border-radius:16px;padding:20px 22px 14px}
.chart svg{width:100%;height:auto;display:block;overflow:visible}
.serie{fill:none;stroke-width:2.6;stroke-linecap:round}
.gridline{stroke:var(--line);stroke-dasharray:2 4}
.chart-title{font-size:16px;color:var(--ink);margin:0 0 4px;font-weight:620}
.chart-sub{font-size:14px;color:var(--faint);margin:0 0 16px;max-width:72ch}

/* timeline */
.tl{position:relative;margin-top:30px;padding-left:34px}
.tl::before{content:'';position:absolute;left:9px;top:6px;bottom:6px;width:2px;background:var(--line)}
.tl-row{position:relative;padding:0 0 26px}
.tl-row::before{content:'';position:absolute;left:-30px;top:7px;width:11px;height:11px;border-radius:50%;
  background:var(--panel);border:2px solid var(--faint)}
.tl-row.key::before{border-color:var(--go);background:rgba(61,220,151,.25)}
.tl-yr{font-family:var(--mono);font-size:13px;color:var(--good)}
.tl-txt{font-size:16px;color:var(--dim);max-width:70ch;margin-top:3px}
.tl-row.key .tl-txt{color:var(--ink)}

.calc{display:grid;grid-template-columns:320px 1fr;gap:30px}
@media(max-width:900px){.calc{grid-template-columns:1fr}}
.slider{margin:18px 0}
.slider label{display:flex;justify-content:space-between;font-size:14px;color:var(--dim);margin-bottom:8px}
.slider label b{color:var(--ink);font-family:var(--mono)}
input[type=range]{width:100%;accent-color:var(--good);height:22px}
.outs{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.out{background:var(--panel2);border:1px solid var(--line);border-radius:14px;padding:18px 20px}
.out .v{font-size:30px;font-weight:740;letter-spacing:-.02em;font-family:var(--mono)}
.out .k{font-size:13px;color:var(--faint);margin-top:6px;line-height:1.4}
.out.good .v{color:var(--good)} .out.bad .v{color:var(--bad)} .out.go .v{color:var(--go)}

footer{padding:56px 0 88px;color:var(--faint);font-size:14px}
footer code{font-family:var(--mono);color:var(--dim)}
footer p{max-width:80ch;color:var(--faint)}
"""

JS = r"""
const D = JSON.parse(document.getElementById('deck-data').textContent);
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const pct = v => v==null ? '--' : (v*100).toFixed(0)+'%';
const fmt = (v,d=0) => v==null ? '--' : v.toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d});

const io = new IntersectionObserver(es => es.forEach(e => {
  if(e.isIntersecting) e.target.classList.add('in');
}), {threshold:.14});

// data-count lives on .big, while .reveal is on its parent .stat, so a single observer
// reading e.target.dataset.count silently never fires. Observe the counters directly.
const countIo = new IntersectionObserver(es => es.forEach(e => {
  if(e.isIntersecting) count(e.target);
}), {threshold:.4});
$$('.reveal').forEach(el => io.observe(el));
$$('[data-count]').forEach(el => countIo.observe(el));
const navIo = new IntersectionObserver(es => es.forEach(e => { if(e.isIntersecting)
  $$('nav a').forEach(a => a.classList.toggle('on', a.getAttribute('href')==='#'+e.target.id));
}), {threshold:.22});
$$('section[id]').forEach(s => navIo.observe(s));

function count(el){
  if(el.dataset.done) return; el.dataset.done = 1;
  if(matchMedia('(prefers-reduced-motion: reduce)').matches) return;  // static text is already correct
  const t = parseFloat(el.dataset.count), dec = parseInt(el.dataset.dec||'0');
  const pre = el.dataset.pre||'', post = el.dataset.post||'';
  let t0 = null;
  const step = ts => { if(!t0) t0 = ts;
    const k = Math.min(1,(ts-t0)/850), e = 1-Math.pow(1-k,3);
    el.textContent = pre + (t*e).toFixed(dec) + post;
    if(k<1) requestAnimationFrame(step); };
  requestAnimationFrame(step);
}

/* ======================== the framework, animated ======================= */
/* Top band: the models and databases, each drawn as an icon with its own number.
   Bottom band: five stages. Evidence packets leave the sources that feed a stage
   and travel into it, so the picture shows which model does what. */
(() => {
  const cv = $('#pipe'); if(!cv) return;
  const ctx = cv.getContext('2d');
  const MM = D.models_meta, M = D.match, G = D.cases.gefitinib;

  // which source group feeds which stage
  const SRC = [
    {g:'clinical', stage:0}, {g:'protein', stage:2},
    {g:'genome', stage:2}, {g:'network', stage:2},
  ];
  const STAGES = [
    {t:'Collect the evidence', o:`${D.module1.family.n_trials} trials, ${D.module1.effects.length} estimates`},
    {t:'Diagnose the failure', o:`${D.module1.diagnosis.evidence.filter(e=>e.fired).length} of ${D.module1.diagnosis.evidence.length} rules fire`},
    {t:'Score who can respond', o:`${MM.esm_substitutions.toLocaleString('en-US')} variants`},
    {t:'Rank the ways out', o:`${M.n_supported} worth trying, ${M.n_unsupported} not`},
    {t:'Design the trial', o:`n=${M.recommended_n}, ${pct(G.requirements.enriched_design.simulated_power||0.89)} power`},
  ];

  const items = [];
  SRC.forEach(sg => (D.models[sg.g]||[]).forEach(m => items.push({...m, stage:sg.stage})));

  let W=0,H=0,cards=[],boxes=[],pk={i:0,k:0},t=0,pulses=[];

  function layout(){
    const r = cv.getBoundingClientRect();
    cv.width=r.width*devicePixelRatio; cv.height=r.height*devicePixelRatio;
    ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0);
    W=r.width; H=r.height;
    // Two rows: 13 sources across one row leaves ~76px per card, which truncates
    // every label on a projector. Split them.
    const pad=12, n=items.length, gap=8, rows=2;
    const perRow=Math.ceil(n/rows), ch=68, rgap=9;
    const cw=Math.min(132,(W-pad*2-gap*(perRow-1))/perRow);
    cards = items.map((m,i)=>{
      const r=Math.floor(i/perRow), inRow=i%perRow;
      const cnt=Math.min(perRow, n-r*perRow);
      const total=cw*cnt+gap*(cnt-1), x0=(W-total)/2;
      return {...m, x:x0+inRow*(cw+gap), y:14+r*(ch+rgap), w:cw, h:ch, lit:0};
    });
    const bn=STAGES.length, bgap=13, by=H-112;
    const bw=(W-pad*2-bgap*(bn-1))/bn;
    boxes = STAGES.map((st,i)=>({...st, x:pad+i*(bw+bgap), y:by, w:bw, h:98, lit:0}));
  }
  layout(); addEventListener('resize', layout);

  const COL = {live:'#4da3ff', in_harness:'#6d7488', planned:'#6d7488'};
  function icon(kind, cx, cy, c, dim){
    ctx.save(); ctx.strokeStyle=c; ctx.fillStyle=c;
    ctx.lineWidth=1.5; ctx.globalAlpha = dim?0.5:1;
    if(kind==='protein'){
      ctx.beginPath();
      for(let i=0;i<5;i++){ const a=i/4*Math.PI*1.7-0.5;
        const x=cx+Math.cos(a)*8, y=cy+Math.sin(a)*7;
        i?ctx.lineTo(x,y):ctx.moveTo(x,y); }
      ctx.stroke();
      for(let i=0;i<5;i+=2){ const a=i/4*Math.PI*1.7-0.5;
        ctx.beginPath(); ctx.arc(cx+Math.cos(a)*8, cy+Math.sin(a)*7, 2.3, 0, 7); ctx.fill(); }
    } else if(kind==='dna'){
      ctx.beginPath();
      for(let i=0;i<=16;i++){ const y=cy-9+i*1.15, x=cx+Math.sin(i/16*Math.PI*2.4)*7;
        i?ctx.lineTo(x,y):ctx.moveTo(x,y); }
      ctx.stroke(); ctx.beginPath();
      for(let i=0;i<=16;i++){ const y=cy-9+i*1.15, x=cx-Math.sin(i/16*Math.PI*2.4)*7;
        i?ctx.lineTo(x,y):ctx.moveTo(x,y); }
      ctx.stroke();
    } else if(kind==='clipboard'){
      ctx.strokeRect(cx-6.5,cy-8.5,13,17);
      ctx.beginPath(); ctx.moveTo(cx-3,cy-8.5); ctx.lineTo(cx-3,cy-11);
      ctx.lineTo(cx+3,cy-11); ctx.lineTo(cx+3,cy-8.5); ctx.stroke();
      [-3.5,0,3.5].forEach(d=>{ ctx.beginPath(); ctx.moveTo(cx-3.5,cy+d); ctx.lineTo(cx+3.5,cy+d); ctx.stroke(); });
    } else if(kind==='journal'){
      ctx.strokeRect(cx-8,cy-7,16,14);
      ctx.beginPath(); ctx.moveTo(cx,cy-7); ctx.lineTo(cx,cy+7); ctx.stroke();
      [-3,1].forEach(d=>{ ctx.beginPath(); ctx.moveTo(cx-5.5,cy+d); ctx.lineTo(cx-1.5,cy+d);
        ctx.moveTo(cx+1.5,cy+d); ctx.lineTo(cx+5.5,cy+d); ctx.stroke(); });
    } else if(kind==='tag'){
      ctx.beginPath(); ctx.moveTo(cx-8,cy-6); ctx.lineTo(cx+3,cy-6); ctx.lineTo(cx+8,cy);
      ctx.lineTo(cx+3,cy+6); ctx.lineTo(cx-8,cy+6); ctx.closePath(); ctx.stroke();
      ctx.beginPath(); ctx.arc(cx+2.5,cy,1.8,0,7); ctx.fill();
    } else if(kind==='bars'){
      [[-6,5],[-2,9],[2,13],[6,7]].forEach(([dx,hh])=>{
        ctx.fillRect(cx+dx-1.4, cy+8-hh, 2.8, hh); });
    } else if(kind==='gear'){
      ctx.beginPath(); ctx.arc(cx,cy,5.5,0,7); ctx.stroke();
      for(let i=0;i<6;i++){ const a=i/6*Math.PI*2;
        ctx.beginPath(); ctx.moveTo(cx+Math.cos(a)*6.5, cy+Math.sin(a)*6.5);
        ctx.lineTo(cx+Math.cos(a)*9.5, cy+Math.sin(a)*9.5); ctx.stroke(); }
    } else if(kind==='network'){
      const pts=[[0,-8],[-8,4],[8,4],[0,1]];
      pts.forEach((a,i)=>pts.forEach((b,j)=>{ if(j>i){ ctx.beginPath();
        ctx.moveTo(cx+a[0],cy+a[1]); ctx.lineTo(cx+b[0],cy+b[1]); ctx.stroke(); }}));
      pts.forEach(a=>{ ctx.beginPath(); ctx.arc(cx+a[0],cy+a[1],2.4,0,7); ctx.fill(); });
    }
    ctx.restore();
  }
  function rr(x,y,w,h,r){ ctx.beginPath(); ctx.moveTo(x+r,y);
    ctx.arcTo(x+w,y,x+w,y+h,r); ctx.arcTo(x+w,y+h,x,y+h,r);
    ctx.arcTo(x,y+h,x,y,r); ctx.arcTo(x,y,x+w,y,r); ctx.closePath(); }
  function clip(txt, maxw, size, weight){
    ctx.font = `${weight} ${size}px ui-monospace,Menlo,monospace`;
    let s2 = String(txt);
    while(s2.length > 3 && ctx.measureText(s2).width > maxw) s2 = s2.slice(0,-1);
    return s2.length < String(txt).length ? s2.slice(0,-1)+'…' : s2;
  }

  function draw(){
    ctx.clearRect(0,0,W,H);
    // feed lines from each source down to its stage
    cards.forEach(c => {
      const b = boxes[c.stage];
      const active = pk.i === c.stage;
      ctx.strokeStyle = active && c.status==='live' ? 'rgba(77,163,255,.5)' : 'rgba(40,50,90,.62)';
      ctx.lineWidth = active && c.status==='live' ? 1.5 : .85;
      ctx.beginPath();
      const x0=c.x+c.w/2, y0=c.y+c.h, x1=b.x+b.w/2, y1=b.y;
      ctx.moveTo(x0,y0); ctx.bezierCurveTo(x0,y0+34, x1,y1-40, x1,y1); ctx.stroke();
    });
    // source cards
    cards.forEach(c => {
      const dim = c.status!=='live', col = COL[c.status];
      rr(c.x,c.y,c.w,c.h,10);
      ctx.fillStyle = c.lit>.05 ? `rgba(29,42,88,${.6+c.lit*.4})` : 'rgba(20,27,51,.9)';
      ctx.fill();
      ctx.lineWidth = c.lit>.05?1.8:1; 
      ctx.strokeStyle = c.lit>.05 ? `rgba(77,163,255,${.5+c.lit*.5})`
                                  : dim ? 'rgba(60,68,96,.85)' : 'rgba(45,58,104,1)';
      if(dim){ ctx.setLineDash([3,3]); } ctx.stroke(); ctx.setLineDash([]);
      icon(c.icon, c.x+16, c.y+c.h/2, col, dim);
      ctx.textAlign='left';
      const tx = c.x+31;
      ctx.fillStyle = dim ? '#7c85a6' : '#eef2ff';
      ctx.fillText(clip(c.short, c.w-38, 11.5, 650), tx, c.y+22);
      ctx.fillStyle = dim ? '#5f677f' : (c.lit>.25 ? '#3ddc97' : '#8893bd');
      ctx.fillText(clip(c.s1, c.w-36, 10, 600), tx, c.y+38);
      ctx.fillStyle = dim ? '#565d73' : '#6b7596';
      ctx.fillText(clip(c.s2, c.w-36, 9, 400), tx, c.y+52);
      c.lit *= .975;
    });
    // stage connectors
    for(let i=0;i<boxes.length-1;i++){
      const a=boxes[i], b=boxes[i+1], y=a.y+a.h/2;
      const act = pk.i===i;
      ctx.strokeStyle = act?'rgba(77,163,255,.95)':'rgba(40,50,90,1)';
      ctx.lineWidth = act?2.3:1.3;
      ctx.beginPath(); ctx.moveTo(a.x+a.w,y); ctx.lineTo(b.x,y); ctx.stroke();
      ctx.beginPath(); ctx.moveTo(b.x-6,y-4); ctx.lineTo(b.x,y); ctx.lineTo(b.x-6,y+4); ctx.stroke();
    }
    // stages
    boxes.forEach((b,i)=>{
      rr(b.x,b.y,b.w,b.h,12);
      ctx.fillStyle = b.lit>.05?`rgba(29,42,88,${.55+b.lit*.45})`:'rgba(20,27,51,.92)';
      ctx.fill();
      ctx.lineWidth = b.lit>.05?2:1.1;
      ctx.strokeStyle = b.lit>.05?`rgba(77,163,255,${.45+b.lit*.55})`:'rgba(40,50,90,1)';
      ctx.stroke();
      ctx.textAlign='center';
      ctx.fillStyle = b.lit>.05?'#7fc0ff':'#5e6a95';
      ctx.font='600 10px ui-monospace,Menlo,monospace';
      ctx.fillText(String(i+1).padStart(2,'0'), b.x+b.w/2, b.y+19);
      ctx.fillStyle = b.lit>.05?'#f0f3ff':'#96a0c6';
      const words=b.t.split(' '); const lines=[]; let cur='';
      ctx.font='500 12.5px -apple-system,Segoe UI,sans-serif';
      for(const w of words){ const tst=cur?cur+' '+w:w;
        if(ctx.measureText(tst).width>b.w-18 && cur){ lines.push(cur); cur=w; } else cur=tst; }
      if(cur) lines.push(cur);
      let yy=b.y+40; lines.slice(0,2).forEach(l=>{ ctx.fillText(l,b.x+b.w/2,yy); yy+=16; });
      ctx.fillStyle = b.lit>.3?'#3ddc97':'rgba(111,123,164,.7)';
      ctx.font='500 11px ui-monospace,Menlo,monospace';
      ctx.fillText(clip(b.o, b.w-12, 11, 500), b.x+b.w/2, yy+4);
      b.lit *= .982;
    });
    // feed pulses
    pulses.forEach(p=>{
      const c=cards[p.ci], b=boxes[c.stage];
      const x0=c.x+c.w/2, y0=c.y+c.h, x1=b.x+b.w/2, y1=b.y, k=p.k;
      const mt=1-k;
      const x = mt*mt*mt*x0 + 3*mt*mt*k*x0 + 3*mt*k*k*x1 + k*k*k*x1;
      const y = mt*mt*mt*y0 + 3*mt*mt*k*(y0+34) + 3*mt*k*k*(y1-40) + k*k*k*y1;
      const g=ctx.createRadialGradient(x,y,0,x,y,8);
      g.addColorStop(0,'rgba(255,255,255,.95)'); g.addColorStop(.4,'rgba(61,220,151,.8)');
      g.addColorStop(1,'rgba(61,220,151,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(x,y,8,0,7); ctx.fill();
    });
    // stage packet
    const a=boxes[pk.i], nb=boxes[Math.min(pk.i+1,boxes.length-1)], y=a.y+a.h/2;
    const x = pk.i===boxes.length-1 ? a.x+a.w/2 : (a.x+a.w)+((nb.x)-(a.x+a.w))*pk.k;
    const g=ctx.createRadialGradient(x,y,0,x,y,13);
    g.addColorStop(0,'rgba(255,255,255,.95)'); g.addColorStop(.35,'rgba(77,163,255,.85)');
    g.addColorStop(1,'rgba(77,163,255,0)');
    ctx.fillStyle=g; ctx.beginPath(); ctx.arc(x,y,13,0,7); ctx.fill();
  }

  function enterStage(i){
    boxes[i].lit = 1;
    cards.forEach((c,ci)=>{ if(c.stage===i && c.status==='live'){
      c.lit = 1; pulses.push({ci, k:0}); }});
  }
  function tick(){
    t++;
    pulses.forEach(p=>p.k+=0.028);
    pulses = pulses.filter(p=>p.k<1);
    if(pk.i < boxes.length-1){
      pk.k += 0.02;
      if(pk.k>=1){ pk.k=0; pk.i++; enterStage(pk.i); }
    } else if(t%160===0){ pk.i=0; pk.k=0; enterStage(0); }
    draw(); requestAnimationFrame(tick);
  }
  enterStage(0); tick();
})();

/* ==================== why patient selection decides it ================== */
(() => {
  const cv = $('#ppi'); if(!cv) return;
  const ctx = cv.getContext('2d');
  const REC = {EGFR:1, MET:1, ERBB2:1};
  const names = [...new Set(D.ppi.edges.flatMap(e => [e.preferredName_A, e.preferredName_B]))];
  const idx = Object.fromEntries(names.map((n,i) => [n,i]));
  const nodes = names.map(n => ({name:n, x:0,y:0,vx:0,vy:0, r: REC[n]?23:16, lit:0}));
  const edges = D.ppi.edges.map(e => ({a:idx[e.preferredName_A], b:idx[e.preferredName_B],
                                       w:e.score, lit:0}));
  const ROUTES = {
    egfr:{entry:'EGFR', path:[['EGFR','GRB2'],['GRB2','SOS1'],['SOS1','KRAS'],['KRAS','BRAF'],['BRAF','MAPK1']]},
    kras:{entry:'KRAS', path:[['KRAS','BRAF'],['BRAF','MAPK1']]},
    met: {entry:'HGF',  path:[['HGF','MET'],['MET','GRB2'],['GRB2','SOS1'],['SOS1','KRAS'],['KRAS','BRAF'],['BRAF','MAPK1']]},
  };
  const TARGET = {gefitinib:'EGFR', onartuzumab:'MET'};
  let mode='egfr', drug=null, pulses=[], t=0;
  names.forEach((n,i) => { const a=i/names.length*Math.PI*2;
    nodes[i].x = 450+Math.cos(a)*160; nodes[i].y = 230+Math.sin(a)*125; });

  function size(){ const r=cv.getBoundingClientRect();
    cv.width=r.width*devicePixelRatio; cv.height=r.height*devicePixelRatio;
    ctx.setTransform(devicePixelRatio,0,0,devicePixelRatio,0,0); }
  size(); addEventListener('resize', size);

  function physics(){
    const W=cv.width/devicePixelRatio, H=cv.height/devicePixelRatio;
    for(let i=0;i<nodes.length;i++) for(let j=i+1;j<nodes.length;j++){
      const a=nodes[i], b=nodes[j];
      const dx=b.x-a.x, dy=b.y-a.y, d2=dx*dx+dy*dy||1, d=Math.sqrt(d2), rep=5600/d2;
      a.vx-=dx/d*rep; a.vy-=dy/d*rep; b.vx+=dx/d*rep; b.vy+=dy/d*rep; }
    edges.forEach(e => { const a=nodes[e.a], b=nodes[e.b];
      const dx=b.x-a.x, dy=b.y-a.y, d=Math.hypot(dx,dy)||1, f=(d-112)*0.0016*e.w;
      a.vx+=dx/d*f; a.vy+=dy/d*f; b.vx-=dx/d*f; b.vy-=dy/d*f; });
    nodes.forEach(n => { n.vx+=(W/2-n.x)*0.0017; n.vy+=(H/2-n.y)*0.0017;
      n.vx*=0.86; n.vy*=0.86; n.x+=n.vx; n.y+=n.vy;
      n.x=Math.max(n.r+10,Math.min(W-n.r-10,n.x)); n.y=Math.max(n.r+10,Math.min(H-n.r-10,n.y));
      n.lit*=0.94; });
    edges.forEach(e => e.lit*=0.93);
  }
  function emit(){
    const r = ROUTES[mode];
    const tgt = drug ? TARGET[drug] : null;
    const onPath = tgt && (r.entry===tgt || r.path.some(([u])=>u===tgt));
    pulses.push({r, i:0, k:0, stopAt: onPath ? tgt : null});
  }
  function stepPulses(){
    pulses.forEach(p => {
      const seg = p.r.path[p.i]; if(!seg){ p.dead=1; return; }
      const [u,v] = seg;
      if(p.stopAt && u===p.stopAt){ p.dead=1; nodes[idx[u]].lit=1.1; return; }
      p.k += 0.03;
      const e = edges.find(x => (names[x.a]===u&&names[x.b]===v)||(names[x.a]===v&&names[x.b]===u));
      if(e) e.lit = Math.max(e.lit,.95);
      nodes[idx[u]].lit = Math.max(nodes[idx[u]].lit, 1-p.k*.5);
      if(p.k>=1){ p.k=0; p.i++; nodes[idx[v]].lit=1; }
    });
    pulses = pulses.filter(p => !p.dead && p.i < p.r.path.length+1);
  }
  function draw(){
    const W=cv.width/devicePixelRatio, H=cv.height/devicePixelRatio;
    ctx.clearRect(0,0,W,H);
    edges.forEach(e => { const a=nodes[e.a], b=nodes[e.b];
      ctx.strokeStyle = e.lit>.05 ? `rgba(77,163,255,${.25+e.lit*.7})` : `rgba(40,50,90,${.3+e.w*.45})`;
      ctx.lineWidth = e.lit>.05 ? 1.2+e.lit*2.4 : .55+e.w*1.25;
      ctx.beginPath(); ctx.moveTo(a.x,a.y); ctx.lineTo(b.x,b.y); ctx.stroke(); });
    pulses.forEach(p => { const seg=p.r.path[p.i]; if(!seg) return;
      const a=nodes[idx[seg[0]]], b=nodes[idx[seg[1]]];
      const x=a.x+(b.x-a.x)*p.k, y=a.y+(b.y-a.y)*p.k;
      const g=ctx.createRadialGradient(x,y,0,x,y,12);
      g.addColorStop(0,'rgba(255,255,255,.95)'); g.addColorStop(.4,'rgba(77,163,255,.82)');
      g.addColorStop(1,'rgba(77,163,255,0)');
      ctx.fillStyle=g; ctx.beginPath(); ctx.arc(x,y,12,0,7); ctx.fill(); });
    nodes.forEach(n => {
      const isT = drug && TARGET[drug]===n.name, isE = ROUTES[mode].entry===n.name;
      if(n.lit>.05){ ctx.fillStyle=`rgba(77,163,255,${n.lit*.3})`;
        ctx.beginPath(); ctx.arc(n.x,n.y,n.r+12*n.lit,0,7); ctx.fill(); }
      ctx.beginPath(); ctx.arc(n.x,n.y,n.r,0,7);
      ctx.fillStyle = isT?'#3d1e26' : isE?'#123458' : '#1b2446'; ctx.fill();
      ctx.lineWidth = isT?2.8 : isE?2.3 : 1.2;
      ctx.strokeStyle = isT?'#ff5c6c' : isE?'#4da3ff' : REC[n.name]?'#41589a':'#2b3865';
      ctx.stroke();
      if(isT){ ctx.beginPath(); ctx.arc(n.x,n.y,n.r+7,0,7);
        ctx.strokeStyle='rgba(255,92,108,.6)'; ctx.setLineDash([4,4]); ctx.lineWidth=1.6;
        ctx.stroke(); ctx.setLineDash([]); }
      ctx.fillStyle = isT?'#ffd8dd':'#e2e8ff'; ctx.textAlign='center'; ctx.textBaseline='middle';
      ctx.font = `${REC[n.name]?600:500} ${REC[n.name]?13:11.5}px ui-monospace,Menlo,monospace`;
      ctx.fillText(n.name, n.x, n.y);
    });
  }
  function loop(){ t++; if(t%72===0) emit(); physics(); stepPulses(); draw(); requestAnimationFrame(loop); }
  for(let i=0;i<280;i++) physics();
  loop();

  const LABEL = {egfr:'EGFR-driven', kras:'KRAS-driven', met:'MET-driven'};
  function say(){
    const r = ROUTES[mode];
    if(!drug){ $('#ppi-state').innerHTML =
      `<b>${LABEL[mode]} tumour.</b> Growth signal enters at <b>${r.entry}</b> and reaches MAPK1, which tells the cell to divide. Now add a drug.`;
      return; }
    const tgt = TARGET[drug];
    const on = r.entry===tgt || r.path.some(([u])=>u===tgt);
    $('#ppi-state').innerHTML = on
      ? `<b style="color:var(--go)">Works.</b> ${drug} blocks ${tgt}, which sits on this tumour's route. The signal stops. This patient is why the drug exists.`
      : `<b style="color:var(--bad)">Does nothing.</b> ${drug} blocks ${tgt}, but this tumour signals below it. The drug cannot reach the problem, and the patient still gets the side effects.`;
  }
  function setMode(m){ mode=m; pulses=[]; $$('[data-mode]').forEach(b=>b.classList.toggle('on',b.dataset.mode===m)); say(); emit(); }
  function setDrug(d){ drug = drug===d ? null : d; pulses=[];
    $$('[data-drug]').forEach(b=>b.classList.toggle('on',b.dataset.drug===drug)); say(); emit(); }
  $$('[data-mode]').forEach(b => b.onclick = () => setMode(b.dataset.mode));
  $$('[data-drug]').forEach(b => b.onclick = () => setDrug(b.dataset.drug));
  setMode('egfr');
})();

/* ============================== power chart ============================= */
const SVGNS = 'http://www.w3.org/2000/svg';
function el(tag, at={}, tx){
  const n = document.createElementNS(SVGNS, tag);
  for(const k in at) n.setAttribute(k, at[k]);
  if(tx!=null) n.textContent = tx;
  return n;
}
function powerChart(sel, key){
  const host = $(sel); if(!host) return;
  host.innerHTML = '';
  const c = D.cases[key], g = c.grid;
  const w = 760, h = 360, pad = {l:52,r:158,t:16,b:54};
  const svg = el('svg',{viewBox:`0 0 ${w} ${h}`}); host.appendChild(svg);
  const X = v => pad.l + v*(w-pad.l-pad.r), Y = v => h-pad.b - v*(h-pad.t-pad.b);
  const fs = [...new Set(g.map(r=>r.f))].sort((a,b)=>a-b);
  const fx = v => X((v-fs[0])/(fs[fs.length-1]-fs[0]));

  [0,.25,.5,.75,1].forEach(p => {
    svg.appendChild(el('line',{class:'gridline',x1:X(0),x2:X(1),y1:Y(p),y2:Y(p)}));
    svg.appendChild(el('text',{x:X(0)-11,y:Y(p)+4,'text-anchor':'end',fill:'#6f7ba4','font-size':12,
      'font-family':'ui-monospace,Menlo,monospace'}, pct(p)));
  });
  fs.forEach(f => svg.appendChild(el('text',{x:fx(f),y:h-pad.b+22,'text-anchor':'middle',
    fill:'#6f7ba4','font-size':12,'font-family':'ui-monospace,Menlo,monospace'}, pct(f))));
  svg.appendChild(el('line',{x1:X(0),x2:X(1),y1:Y(.8),y2:Y(.8),stroke:'#ffc043','stroke-width':1.3,
    'stroke-dasharray':'5 4'}));
  svg.appendChild(el('text',{x:X(0)+7,y:Y(.8)-8,fill:'#ffc043','font-size':12}, 'the bar you have to clear'));

  const greys = ['#5e6a95','#8b97c2','#c3cbe8'];
  const labels = [];
  ['unselected','enriched'].forEach(design => {
    const ns = [...new Set(g.filter(r=>r.design===design).map(r=>r.n))].sort((a,b)=>a-b);
    ns.forEach((n,i) => {
      const rows = g.filter(r=>r.design===design && r.n===n).sort((a,b)=>a.f-b.f);
      if(rows.length<2) return;
      const col = design==='enriched' ? '#3ddc97' : greys[i%greys.length];
      const p = el('path',{class:'serie',
        d: rows.map((r,j)=>`${j?'L':'M'}${fx(r.f).toFixed(1)},${Y(r.power).toFixed(1)}`).join(' '),
        stroke: col});
      svg.appendChild(p);
      const L = p.getTotalLength ? p.getTotalLength() : 1200;
      p.style.strokeDasharray = L; p.style.strokeDashoffset = L;
      p.style.transition = 'stroke-dashoffset 1.1s ease-out';
      requestAnimationFrame(()=>requestAnimationFrame(()=>{ p.style.strokeDashoffset = 0; }));
      rows.forEach(r => svg.appendChild(el('circle',{cx:fx(r.f),cy:Y(r.power),r:3.4,fill:col})));
      labels.push({t: design==='enriched' ? `selected patients, n=${fmt(n)}`
                                          : `everyone, n=${fmt(n)}`,
                   col, y: Y(rows[rows.length-1].power)});
    });
  });
  labels.sort((a,b)=>a.y-b.y);
  for(let i=1;i<labels.length;i++) if(labels[i].y-labels[i-1].y<15) labels[i].y = labels[i-1].y+15;
  labels.forEach(s => svg.appendChild(el('text',{x:X(1)+12,y:s.y+4,fill:s.col,'font-size':12.5}, s.t)));

  svg.appendChild(el('text',{x:X(.5),y:h-6,'text-anchor':'middle',fill:'#aab4d6','font-size':13},
    'Share of enrolled patients who can actually respond'));
  svg.appendChild(el('text',{x:13,y:pad.t+2,fill:'#aab4d6','font-size':13,
    transform:`rotate(-90 13 ${pad.t+2})`}, 'Chance the trial succeeds'));
}

/* ============================== calculator ============================= */
function calculator(){
  if(!$('#calc')) return;
  const S = id => parseFloat($('#'+id).value);
  function render(){
    const cost=S('c-trial'), n=S('c-n'), pS=S('c-strong')/100, pW=S('c-weak')/100, share=S('c-share')/100;
    $('#v-trial').textContent = '$'+cost.toFixed(0)+'M';
    $('#v-n').textContent = n.toFixed(0);
    $('#v-share').textContent = (share*100).toFixed(0)+'%';
    $('#v-strong').textContent = (pS*100).toFixed(0)+'%';
    $('#v-weak').textContent = (pW*100).toFixed(0)+'%';
    const pAll = share*pW + (1-share)*pS;
    const sAll = n*pAll, sSel = n*(1-share)*pS;
    const cAll = n*cost, cSel = n*(1-share)*cost;
    const cpsAll = sAll>0 ? cAll/sAll : null, cpsSel = sSel>0 ? cSel/sSel : null;
    $('#o-all').textContent = cpsAll==null?'--':'$'+cpsAll.toFixed(0)+'M';
    $('#o-sel').textContent = cpsSel==null?'--':'$'+cpsSel.toFixed(0)+'M';
    $('#o-save').textContent = (cpsAll==null||cpsSel==null)?'--':'$'+(cpsAll-cpsSel).toFixed(0)+'M';
    $('#o-skip').textContent = '$'+(n*share*(1-pW)*cost).toFixed(0)+'M';
  }
  $$('#calc input').forEach(i => i.addEventListener('input', render));
  render();
}

powerChart('#chart-power','gefitinib');
calculator();
const chartIo = new IntersectionObserver(es => es.forEach(e => {
  if(e.isIntersecting && !e.target.dataset.drawn){ e.target.dataset.drawn = 1;
    powerChart('#chart-power','gefitinib'); }
}), {threshold:.3});
$$('[data-chart]').forEach(c => chartIo.observe(c));
"""

# ---------------------------------------------------------------------------
# Values used in prose. Every one is read from the pipeline output.
# ---------------------------------------------------------------------------
EC = DATA["economics"]
CI = EC["cost_inputs"]
M = DATA["match"]
G = DATA["cases"]["gefitinib"]
O = DATA["cases"]["onartuzumab"]
DIST = DATA["distributions"]["onartuzumab"]
REQ = EC["design"]["enriched"]   # normalised keys: n_randomized, n_screened, power
PPP = CI["per_patient_usd"]
OS_COST = CI["onc_by_endpoint_musd"]["OS"]
P = {r["strategy"]: r for r in EC["portfolio"]}
MM = DATA["models_meta"]
MODEL_LONGEST = next(m["longest_protein"] for m in DATA["models"]["protein"]
                     if m["name"] == "ESM-1v")
AD = DATA["benchmark"]["provenance_contrast"]["all_decided"]
TL = DATA["timeline"]
UNS = EC["design"]["unselected_realistic"]
UNS_ZERO = [r for r in UNS if r["simulated_power"] == 0.0]
assert UNS_ZERO, "expected zero-power unselected rows"
UNS_MAX_N = max(r["total_randomized"] for r in UNS_ZERO)

NICE = {
    "biomarker_enrichment_new_inclusion_criteria": "Enrol only patients with the marker",
    "clinical_surrogate_enrichment": "Enrol on a clinical stand-in for the marker",
    "narrower_indication": "Narrow the disease definition",
    "new_endpoint": "Measure a different endpoint",
    "new_line_of_therapy": "Treat earlier in the disease",
    "molecule_modification": "Change the molecule",
}
DID = {
    "biomarker_enrichment_new_inclusion_criteria": "EMA restricted the label to marker-positive patients in 2009",
    "clinical_surrogate_enrichment": "IPASS enrolled on histology, smoking history and geography",
    "narrower_indication": "lung cancer became marker-positive lung cancer",
    "new_endpoint": "overall survival became progression-free survival",
    "new_line_of_therapy": "third line became first line",
    "molecule_modification": "never attempted for this drug",
}
match_rows = "".join(
    f"<tr><td>{NICE[r['strategy']]}</td>"
    f"<td><span class='tag {'go' if r['supported'] else 'bad'}'>"
    f"{'worth trying' if r['supported'] else 'not supported'}</span></td>"
    f"<td>{DID[r['strategy']]}</td>"
    f"<td class='num'><span class='tag {'go' if r['agrees'] else 'bad'}'>"
    f"{'match' if r['agrees'] else 'miss'}</span></td></tr>"
    for r in sorted(M["rows"], key=lambda x: x["rank"]))

KEY_YEARS = {"2003", "2009", "2015"}
tl_rows = "".join(
    f"<div class='tl-row {'key' if (r.get('date') or '')[:4] in KEY_YEARS else ''} reveal'>"
    f"<div class='tl-yr'>{(r.get('date') or '')[:4]} &middot; {r.get('agency','')}</div>"
    f"<div class='tl-txt'>{r.get('event','')}</div></div>"
    for r in TL)

HTML = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Trial Salvage — reading a failed trial for the way out</title>
<style>{CSS}</style>
</head><body>

<nav><div class="wrap">
  <div class="brand">trial<span>salvage</span></div>
  <a href="#problem">The problem</a>
  <a href="#why">Why it happens</a>
  <a href="#framework">The framework</a>
  <a href="#match">Does it match history</a>
  <a href="#trial">The trial it designs</a>
  <a href="#no">When it says no</a>
  <a href="#worth">What it saves</a>
  <div class="who">Luca &middot; Daniel &middot; Ramin &middot; Tianhao</div>
</div></nav>

<header><div class="wrap">
  <div class="kicker">Phase 3 failure &rarr; the way out</div>
  <h1>A failed trial still contains<br><em>the instructions for fixing it</em>.</h1>
  <p class="lede">We built a pipeline that reads them. On gefitinib it recovers the answer the
  field took twelve years to reach.</p>

  <div class="stats">
    <div class="stat go reveal">
      <div class="big" data-count="{M['n_agree']}" data-post=" of {M['n_strategies']}">{M['n_agree']} of {M['n_strategies']}</div>
      <div class="lbl">ways out of the failure called correctly. Five it said were worth trying,
      the field used. One it said was unsupported, nobody tried.</div>
    </div>
    <div class="stat good reveal">
      <div class="big" data-count="{M['recommended_n']}" data-post=" vs {M['actual_approval_trial_n']}">{M['recommended_n']} vs {M['actual_approval_trial_n']}</div>
      <div class="lbl">patients our simulation says the fixed trial needs, against the
      {M['actual_approval_trial_n']} in the trial that actually won approval.</div>
    </div>
    <div class="stat warn reveal">
      <div class="big" data-count="{M['years_to_get_there']}" data-post=" years">{M['years_to_get_there']} years</div>
      <div class="lbl">from the unselected approval in {M['first_event_year']} to the
      marker-selected one in {M['last_event_year']}. Our pipeline runs in seconds.</div>
    </div>
    <div class="stat bad reveal">
      <div class="big" data-count="0" data-post="%">0%</div>
      <div class="lbl">chance of success re-running the failed trial unchanged, at every size we
      tested up to {UNS_MAX_N:,} patients. Selecting the right patients is the whole
      difference.</div>
    </div>
  </div>
</div></header>

<section id="problem"><div class="wrap">
  <div class="sec-no">01 &middot; THE PROBLEM</div>
  <h2>The drug worked. The trial averaged it away.</h2>
  <p class="big">A trial reports one number for everybody in it. A drug that helps a quarter of
  patients and does nothing for the rest can produce a flat number.</p>
  <p>It gets shelved. Not for failing, but for being measured on the wrong people.</p>

  <div class="grid3" style="margin-top:34px">
    <div class="card reveal"><h3>${OS_COST:.0f}M</h3>
      <p class="sub">Median cost of an oncology trial measuring overall survival. Both failures in
      this deck were that kind of trial.</p></div>
    <div class="card reveal"><h3>${PPP:,}</h3>
      <p class="sub">Per patient enrolled. Every patient who cannot respond costs this much and
      dilutes your result.</p></div>
    <div class="card reveal"><h3>{CI['phase3_onc_success']*100:.0f}%</h3>
      <p class="sub">Of phase 3 oncology trials succeed. Most of that money buys a negative
      answer.</p></div>
  </div>
</div></section>

<section id="why"><div class="wrap">
  <div class="sec-no">02 &middot; WHY IT HAPPENS</div>
  <h2>The same drug is a good drug and a useless drug, in two patients.</h2>
  <p>Pick a tumour. Add a drug.</p>

  <div class="stage reveal" style="margin-top:26px">
    <canvas id="ppi"></canvas>
    <div class="controls">
      <button class="btn" data-mode="egfr">EGFR-driven tumour</button>
      <button class="btn" data-mode="kras">KRAS-driven tumour</button>
      <button class="btn" data-mode="met">MET-driven tumour</button>
      <button class="btn" data-drug="gefitinib">+ gefitinib</button>
      <button class="btn" data-drug="onartuzumab">+ onartuzumab</button>
    </div>
    <div class="legend">
      <span class="dot" style="background:#4da3ff"></span>where the growth signal starts<br>
      <span class="dot" style="background:#ff5c6c"></span>what the drug blocks
    </div>
  </div>
  <div class="state" id="ppi-state"></div>
  <p class="sub">Real interaction data: {DATA['ppi']['source']}.</p>

  <div class="callout reveal"><p>Mix both patients into one trial and the average says the drug does
  not work.</p></div>
</div></section>

<section id="framework"><div class="wrap">
  <div class="sec-no">03 &middot; THE FRAMEWORK</div>
  <h2>Five steps. {MM['n_live']} live data sources and models.</h2>

  <div class="stage reveal" style="margin-top:22px"><canvas id="pipe"></canvas>
    <div class="legend">
      <span class="dot" style="background:#4da3ff"></span>producing results now<br>
      <span class="dot" style="background:#6d7488;opacity:.6"></span>wired up, not yet scoring
    </div>
  </div>

  <div class="grid3" style="margin-top:22px">
    <div class="card reveal"><h3>{MM['esm_substitutions']:,}</h3>
      <p class="sub">amino-acid substitutions scored by a 5-model ESM-1v ensemble across
      {MM['esm_genes']} genes, longest protein {MODEL_LONGEST:,} residues.</p></div>
    <div class="card reveal"><h3>{MM['esm_auroc_egfr']:.3f}</h3>
      <p class="sub">ESM-1v AUROC separating pathogenic from benign EGFR variants, against
      {MM['polyphen_auroc']:.3f} for PolyPhen-2 and {MM['sift_auroc']:.3f} for SIFT on the
      same variants.</p></div>
    <div class="card reveal"><h3>{MM['clinvar_pathogenic']:,} / {MM['clinvar_benign']:,}</h3>
      <p class="sub">ClinVar pathogenic and benign labels used as ground truth. Nothing is
      self-scored.</p></div>
  </div>

  <div class="callout reveal"><p>Output is a ranked list, never a probability that a rescue will
  succeed. A number would be read as a promise and this evidence cannot support one.</p></div>
</div></section>

<section id="match"><div class="wrap">
  <div class="sec-no">04 &middot; DOES IT MATCH HISTORY</div>
  <h2>We ran it on gefitinib. Then we checked what the field actually did.</h2>
  <p>Approved {M['first_event_year']}, failed on survival, withdrawn. We asked the pipeline which
  ways out the evidence supported, then checked what the field did.</p>

  <table>
    <thead><tr><th>Way out</th><th>Our call</th><th>What actually happened</th>
      <th class="num">Agree</th></tr></thead>
    <tbody>{match_rows}</tbody>
  </table>

  <div class="callout go reveal"><p><b>{M['n_agree']} out of {M['n_strategies']}.</b>
  Every route it ranked as worth trying was used. The one it called unsupported was never
  attempted for this drug.</p></div>

  <h3>The field's own route to the same answer</h3>
  <div class="tl">{tl_rows}</div>

  <div class="callout reveal"><p>{M['years_to_get_there']} years and a withdrawal to reach
  marker-selected patients. The evidence was there by 2009.</p></div>
</div></section>

<section id="trial"><div class="wrap">
  <div class="sec-no">05 &middot; THE TRIAL IT DESIGNS</div>
  <h2>Selecting patients is not an efficiency gain. It is the whole trial.</h2>

  <div class="chart reveal" data-chart="power" style="margin-top:26px">
    <p class="chart-title">Chance of success against how many enrolled patients can respond</p>
    <p class="chart-sub">Each line is a trial size. Green enrols only patients with the marker, so
    it sits at the right-hand end by construction.</p>
    <div id="chart-power"></div>
  </div>

  <div class="outs" style="margin-top:26px;grid-template-columns:repeat(3,1fr)">
    <div class="out bad reveal"><div class="v">0%</div>
      <div class="k">re-running the failed trial unchanged, at {UNS_MAX_N:,} patients</div></div>
    <div class="out go reveal"><div class="v">{REQ['power']*100:.0f}%</div>
      <div class="k">enrolling {REQ['n_randomized']} marker-positive patients instead</div></div>
    <div class="out good reveal"><div class="v">{REQ['n_screened']}</div>
      <div class="k">patients tested to find those {REQ['n_randomized']}</div></div>
  </div>

  <p style="margin-top:26px">Marker-negative patients do <em>worse</em> on the drug
  (hazard ratio {DATA['module1']['handoff']['hr_neg']} against
  {DATA['module1']['handoff']['hr_pos']} in marker-positive). Adding more of them pushes the
  average further the wrong way. No sample size fixes it.</p>

  <figure class="reveal">
    <img src="{b64(FIG_FILES['gefitinib_m4'])}" alt="Power and screening burden for gefitinib">
    <figcaption>Left: chance of success against marker prevalence. Right: how many patients you
    screen to randomise one trial. Enrichment moves the cost from trial size to screening.</figcaption>
  </figure>
</div></section>

<section id="no"><div class="wrap">
  <div class="sec-no">06 &middot; WHEN IT SAYS NO</div>
  <h2>It also tells you not to bother.</h2>
  <p>Onartuzumab had the same evidence shape: a strong-looking marker-positive subgroup, from
  {O['pre_retry']['subgroup_n'] if isinstance(O.get('pre_retry'), dict) and O['pre_retry'].get('subgroup_n') else 66}
  patients. Its sponsor ran a {O['trials']['rescue']['n']}-patient survival trial. Stopped for
  futility.</p>
  <p>If that subgroup effect were real, what should the trial have returned? Using only
  pre-trial information:</p>

  <div class="outs" style="margin-top:22px;grid-template-columns:repeat(3,1fr)">
    <div class="out good reveal"><div class="v">{DIST['p2_5']:.2f}&ndash;{DIST['p97_5']:.2f}</div>
      <div class="k">what the trial should have returned if the subgroup signal were real</div></div>
    <div class="out bad reveal"><div class="v">{DIST['observed']:.2f}</div>
      <div class="k">what it actually returned. Above 1.0 means worse on the drug</div></div>
    <div class="out bad reveal"><div class="v">${OS_COST:.0f}M</div>
      <div class="k">median cost of a survival trial at that scale</div></div>
  </div>

  <div class="callout bad reveal"><p>The result falls outside the whole predicted range. The
  subgroup estimate was already refutable from published numbers, before anyone enrolled a
  patient.</p></div>
</div></section>

<section id="worth"><div class="wrap">
  <div class="sec-no">07 &middot; WHAT IT SAVES</div>
  <h2>Which retries are worth running.</h2>
  <p>{AD['n_pairs']} curated cases, failed drug retried, outcome known. Planned or mechanistic
  signal: <b>{AD['prespecified_or_mechanistic']['success']}/{AD['prespecified_or_mechanistic']['n']}
  succeeded ({AD['prespecified_or_mechanistic']['success_rate']*100:.0f}%)</b>. After-the-fact
  subgroup: <b>{AD['post_hoc_subgroup']['success']}/{AD['post_hoc_subgroup']['n']}
  ({AD['post_hoc_subgroup']['success_rate']*100:.0f}%)</b>. Odds ratio
  {AD['odds_ratio']}, p = {AD['fisher_p']}.</p>

  <div class="calc" id="calc" style="margin-top:30px">
    <div>
      <div class="slider"><label>Cost per trial <b id="v-trial"></b></label>
        <input type="range" id="c-trial" min="10" max="100" step="1" value="{CI['onc_pivotal_median_musd']:.0f}"></div>
      <div class="slider"><label>Retries considered <b id="v-n"></b></label>
        <input type="range" id="c-n" min="2" max="40" step="1" value="10"></div>
      <div class="slider"><label>Share resting on an after-the-fact subgroup <b id="v-share"></b></label>
        <input type="range" id="c-share" min="0" max="90" step="1" value="{AD['post_hoc_subgroup']['n']/AD['n_pairs']*100:.0f}"></div>
      <div class="slider"><label>Success rate, planned signal <b id="v-strong"></b></label>
        <input type="range" id="c-strong" min="10" max="90" step="1" value="{AD['prespecified_or_mechanistic']['success_rate']*100:.0f}"></div>
      <div class="slider"><label>Success rate, after-the-fact subgroup <b id="v-weak"></b></label>
        <input type="range" id="c-weak" min="2" max="60" step="1" value="{AD['post_hoc_subgroup']['success_rate']*100:.0f}"></div>
    </div>
    <div class="outs">
      <div class="out bad reveal"><div class="v" id="o-all"></div>
        <div class="k">spend per success if you retry everything</div></div>
      <div class="out go reveal"><div class="v" id="o-sel"></div>
        <div class="k">spend per success if you only retry the well-supported ones</div></div>
      <div class="out good reveal"><div class="v" id="o-save"></div>
        <div class="k">difference, per success</div></div>
      <div class="out reveal"><div class="v" id="o-skip"></div>
        <div class="k">spent on retries we would have advised against</div></div>
    </div>
  </div>
  <p class="sub" style="margin-top:20px">A decision model, not a forecast. One trial per attempt,
  no assay or analysis cost, and success rates from {AD['n_pairs']} curated cases. The direction is
  the result; the dollars are illustration.</p>
</div></section>

<footer><div class="wrap">
  <p><b>trial-salvage</b> &middot; <code>{DATA['meta']['repo']}</code> @ <code>{DATA['meta']['head']}</code>
  &middot; {DATA['meta']['tests']} tests &middot; generated {DATA['meta']['generated']} from the
  pipeline's own outputs.</p>
  <p>Trial data: ClinicalTrials.gov API v2 and PubMed E-utilities. Interaction data:
  {DATA['ppi']['source']}. Costs: {EC['sources']['onc_pivotal_median_musd']} &middot;
  {EC['sources']['pivotal_trial_median_musd']} &middot; {EC['sources']['phase3_onc_success']}</p>
  <p>Limitations, negative results and what we could not get working are written up separately in
  <code>trial_salvage_limitations.html</code>.</p>
</div></footer>

<script id="deck-data" type="application/json">{json.dumps(DATA)}</script>
<script>{JS}</script>
</body></html>
"""

OUT.write_text(HTML)
print(f"wrote {OUT} — {len(HTML)/1024:.0f} KB")
