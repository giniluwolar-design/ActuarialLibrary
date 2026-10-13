import { mountScene } from './scene.js';

const $ = id => document.getElementById(id);
const variants = { A: 'Spatial library', B: 'Quiet worktable', C: 'Evidence constellation' };
const state = { variant: new URL(location.href).searchParams.get('variant') || 'A', tool: null, example: 'baseline', annuity: 'regular' };
const fixtures = {
  baseline: { title: 'Paid Chain Ladder', amount: 480, payments: [258, 132, 90], origin2024: 120, rationale: 'Volume-weighted paid factors 2.0 and 1.2; explicit tail 1.25.' },
  bf: { title: 'BF alternative', amount: 460, payments: [250, 120, 90], origin2024: 100, rationale: 'Reference scenario: 2024 paid BF ultimate 340, paid 240. All other origins unchanged.' },
  expert: { title: 'Expert judgement', amount: 470, payments: [254, 126, 90], origin2024: 110, rationale: 'Illustrative human rationale: choose ultimate 350 for 2024, with paid 240. This is a demonstration, not a saved or approved decision.' },
};
const regular = [0.9715686274509804, 0.9422322183775469, 0.9121206115295022];
const partner = [0.015560784313725503, 0.03183511907112656, 0.0485529274131552];
const sources = 'https://github.com/giniluwolar-design/ActuarialLibrary/blob/414ef6ae83be9c5e9c4f0d0b5b071bac2ae56041/docs/contracts/';
const tools = {
  reserving: { name: 'Reserving', index: '01', topic: 'NON-LIFE', copy: 'From a development picture to a considered reserve.', description: 'Explore the triangle. Compare methods and scenarios. Bring your judgement into the result—with its reasons intact.', capability: 'Methods · scenarios · expert opinion', number: 'A reserve is a decision.<br>Make its reasoning visible.' },
  annuity: { name: 'Annuity factors', index: '02', topic: 'LIFE & PENSIONS', copy: 'See the cash flows behind every factor.', description: 'Participant and partner benefits, payment timing and survival assumptions—revealed as a connected, inspectable story.', capability: 'Old-age · partner benefits · cash flows', number: 'Two lives.<br>Each assumption in view.' },
};
let disposers = [];
const reduced = matchMedia('(prefers-reduced-motion: reduce)');
$('previous-variant').parentElement.hidden = !location.pathname.includes('/vision-prototype/') && location.pathname !== '/index.html';
const money = value => new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR', maximumFractionDigits: 2 }).format(value);
function teardown() { disposers.forEach(dispose => dispose()); disposers = []; }
function scenes() { document.querySelectorAll('canvas[data-scene]').forEach(canvas => disposers.push(mountScene(canvas, { kind: canvas.dataset.scene, reducedMotion: reduced.matches }))); }
function surfaceState() {
  $('state-description').textContent = `Design ${state.variant}: ${variants[state.variant]}. ${state.tool ? `${tools[state.tool].name}; illustrative ${state.tool === 'reserving' ? state.example : state.annuity} case.` : 'Library entrance; two tools.'} In-memory prototype, no calculation or saved decisions.`;
}
const art = kind => `<canvas data-scene="${kind}" aria-hidden="true"></canvas>`;
function toolButton(kind, structure = '') {
  const t = tools[kind];
  return `<button class="tool-entry ${structure}" data-tool="${kind}"><span class="tool-number">${t.index}</span><span class="entry-copy"><small>${t.topic}</small><strong>${t.name}</strong><span>${t.copy}</span></span><span class="entry-arrow" aria-hidden="true">↗</span></button>`;
}
function VariantA() {
  return `<div class="spatial-layout"><div class="hero-copy"><p class="eyebrow">A DIFFERENT WAY TO WORK</p><h1 id="page-title">Complexity,<br><em>made clear.</em></h1><p class="intro">An open library for actuarial thinking.<br>Depth when you need it. Space when you don’t.</p><div class="hero-meta"><span>Two tools to begin.</span><span>Your expertise stays in the picture.</span></div></div><div class="hero-art">${art('reserving')}<span class="art-label">A DEVELOPMENT PICTURE,<br>SEEN DIFFERENTLY.</span><span class="art-coordinate">01 / 02</span></div><div class="tool-shelf">${toolButton('reserving')}${toolButton('annuity')}</div><div class="library-baseline"><span>Explore a tool to reveal its assumptions and evidence.</span><span>VISION PROTOTYPE · SYNTHETIC EXAMPLES</span></div></div>`;
}
function VariantB() {
  return `<div class="worktable-layout"><div class="worktable-heading"><p class="eyebrow">YOUR ACTUARIAL WORKTABLE</p><h1 id="page-title">Less interface.<br><em>More understanding.</em></h1><p>Choose the question you’re working on.<br>The tools and their reasoning come into view.</p></div><div class="worktable-tools"><div class="worktable-row">${toolButton('reserving', 'editorial-entry')}<div class="row-art">${art('reserving')}</div></div><div class="worktable-row">${toolButton('annuity', 'editorial-entry')}<div class="row-art">${art('annuity')}</div></div></div><p class="worktable-caption">Open methodology. Explicit judgement. Outcomes you can inspect.<span>Read-only design prototype</span></p></div>`;
}
function VariantC() {
  return `<div class="constellation-layout"><p class="eyebrow">FOLLOW THE REASONING</p><h1 id="page-title">Everything connects.<br><em>Nothing is hidden.</em></h1><p class="intro">Start with a tool. Move through its outcomes,<br>assumptions and evidence—without losing the thread.</p><div class="constellation"><div class="orbital-art">${art('annuity')}</div><div class="hub"><span>ACTUARIAL<br>LIBRARY</span></div><div class="constellation-node node-one">${toolButton('reserving', 'orbital-entry')}</div><div class="constellation-node node-two">${toolButton('annuity', 'orbital-entry')}</div><span class="orbit-caption">OUTCOME → ASSUMPTION → EVIDENCE</span></div><div class="constellation-bottom"><p>Human judgement is part of the model.<br>Evidence is part of the experience.</p><span>Read-only design prototype · two tools</span></div></div>`;
}
function renderLibrary() {
  teardown();
  if (!variants[state.variant]) state.variant = 'A';
  document.body.dataset.variant = state.variant;
  $('library').hidden = false; $('workspace').hidden = true;
  $('library').innerHTML = ({ A: VariantA, B: VariantB, C: VariantC }[state.variant])();
  $('variant-label').textContent = `${state.variant} · ${variants[state.variant]}`;
  document.title = `Actuarial Library · ${variants[state.variant]}`;
  scenes(); surfaceState();
}
function showEvidence(kind) {
  let title, body;
  if (kind === 'triangle') {
    title = 'The observed development picture';
    body = `<p>Accepted three-origin reference fixture. Future observations are not zeros.</p><div class="table-wrap"><table><thead><tr><th>Origin</th><th>Age 1</th><th>Age 2</th><th>Age 3</th></tr></thead><tbody><tr><th>2023</th><td>100</td><td>200</td><td>240</td></tr><tr><th>2024</th><td>120</td><td>240</td><td class="future">Future</td></tr><tr><th>2025</th><td>150</td><td class="future">Future</td><td class="future">Future</td></tr></tbody></table></div><p>Paid factors: 440 / 220 = 2.0; 240 / 200 = 1.2. Tail 1.25 is an explicit assumption, not an observed value.</p>`;
  } else if (kind === 'judgement') {
    title = 'Judgement with its reasons intact';
    body = `<p>${fixtures[state.example].rationale}</p><dl><dt>Reference decision</dt><dd>${fixtures[state.example].title}</dd><dt>2024 outstanding</dt><dd>${money(fixtures[state.example].origin2024)}</dd><dt>What stays unchanged</dt><dd>The baseline fixture and every other origin.</dd><dt>Authorship</dt><dd>Synthetic authored example; no runtime action recorded.</dd></dl><p>A production choice would require rationale, an action identity, versioned result and linked supporting evidence. This preview does not save or approve a reserve.</p>`;
  } else if (kind === 'survival') {
    title = 'Two lives. An explicit contingency.';
    body = `<p>The partner example is a fixed-partner, independent-lifetimes case: participant male aged 68, eligible partner female aged 65. It is not a marriage-frequency model.</p><div class="formula">S<sub>partner</sub>(t) × [1 − S<sub>participant</sub>(t)]</div><p>Synthetic annual qx: participant 0.016 / 0.018 / 0.020; partner 0.008 / 0.0096 / 0.0112. Flat annual-effective 2% discount is a test fixture, not EIOPA evidence.</p><dl><dt>At reference term 3</dt><dd>Participant survival 0.94696224; partner survival 0.97147305984.</dd><dt>Horizon</dt><dd>Three reference terms; truncated, not whole-life.</dd><dt>Extension gate</dt><dd>Marriage, divorce, remarriage, changing eligibility and unknown-partner age distributions require separately specified models.</dd></dl>`;
  } else if (kind === 'performance') {
    title = 'Fast is something we measure';
    body = `<p>The visual prototype has no portfolio engine and makes no large-data speed claim.</p><ol><li>Measure import, validation, triangle construction, calculation and export separately.</li><li>Record named dataset sizes, hardware, software, repeat timings and peak memory.</li><li>Keep large payloads behind lazy evidence expansion rather than loading every record into the screen.</li><li>Agree latency and memory targets against the measured baseline.</li></ol><p>Calm graphics have capped animation, reduced-motion support and static mobile scenes. That is an interface policy, not a numerical-performance benchmark.</p>`;
  } else {
    title = 'A trace you can follow—not an audit claim';
    body = `<p>These are inspectable reference fixtures, not saved production runs. No invented hashes, timestamps or approval badges.</p><div class="trace-chain"><span>Outcome</span><i>→</i><span>Explicit assumptions</span><i>→</i><span>Source fixture</span></div><p>Real tools must preserve data version, method/configuration, human decisions, software version and immutable result references. Formal approvals and authenticated audit governance are separate release requirements.</p>`;
  }
  $('evidence-content').innerHTML = `<p class="eyebrow">REFERENCE EVIDENCE · SYNTHETIC</p><h2 id="evidence-title">${title}</h2>${body}`;
  $('evidence-dialog').showModal();
}
function curveSvg(values, color = '#bfd3b7') {
  const max = Math.max(...values), points = values.map((v,i) => `${52+i*210},${180-v/max*135}`);
  return `<svg class="payment-curve" viewBox="0 0 520 215" role="img" aria-label="Illustrative three-term payment contributions"><path d="M52 180H472" class="chart-baseline"/><polyline points="${points.join(' ')}" fill="none" stroke="${color}" stroke-width="2"/>${values.map((v,i)=>`<circle cx="${52+i*210}" cy="${180-v/max*135}" r="5" fill="${color}"/><text x="${52+i*210}" y="206" text-anchor="middle">${state.tool==='reserving' ? 2026+i : `Term ${i+1}`}</text>`).join('')}</svg>`;
}
function renderWorkspace() {
  teardown(); $('library').hidden = true; $('workspace').hidden = false;
  const t = tools[state.tool], reserving = state.tool === 'reserving', f = fixtures[state.example];
  const annual = state.annuity === 'regular', values = reserving ? f.payments : annual ? regular : partner;
  const headline = reserving ? money(f.amount) : annual ? '2.825921' : '0.095949';
  const caseLabel = reserving ? f.title : annual ? 'Regular annual · explicit 50/50 factor mix' : 'Partner annual · fixed M68/F65 pair';
  $('workspace').innerHTML = `<div class="workspace-top"><button class="back-button" data-home>← Library</button><span>${t.topic} / ${t.name.toUpperCase()}</span><span class="fixture-label">READ-ONLY SYNTHETIC EXAMPLE</span></div><div class="workspace-title"><p class="eyebrow">${t.index} / ${t.capability.toUpperCase()}</p><h1 id="workspace-title">${t.number}</h1><p>${t.description}</p></div><div class="result-layout"><article class="result-panel"><div class="result-kicker">${reserving ? 'SELECTED OUTSTANDING · ILLUSTRATIVE' : 'FACTOR PER UNIT ANNUAL BENEFIT · TRUNCATED'}</div><button class="headline-value" data-evidence="${reserving ? 'judgement' : 'survival'}" aria-label="Inspect the reasoning behind ${headline}">${headline}<span>↗</span></button><p class="result-context">${caseLabel}</p>${curveSvg(values, reserving ? '#d6b284' : '#bfd3b7')}<div class="payment-values">${values.map((v,i)=>`<div><small>${reserving ? 2026+i : `Reference term ${i+1}`}</small><strong>${reserving ? money(v) : v.toFixed(6)}</strong></div>`).join('')}</div><p class="result-footnote">${reserving ? 'Explicit paid development pattern; tail after the final modelled age. Unrounded payments reconcile to the selected fixture reserve.' : 'Three-term numerical reference, not calendar-engine output. No AG table or whole-life result is implied.'}</p></article><aside class="reasoning-panel"><div class="eyebrow">THE REASONING, WITHIN REACH</div><h2>Start with the result.<br>Follow what matters.</h2><button class="reasoning-link" data-evidence="${reserving?'triangle':'survival'}"><span>01</span><div><strong>${reserving ? 'Source & development' : 'Survival & contingency'}</strong><small>${reserving ? 'Observed cells → fitted factors' : 'Participant → eligible partner'}</small></div><b>↗</b></button><button class="reasoning-link" data-evidence="judgement" ${reserving?'':'hidden'}><span>02</span><div><strong>Human judgement</strong><small>Selection → reasons → unchanged baseline</small></div><b>↗</b></button><button class="reasoning-link" data-evidence="trail"><span>${reserving?'03':'02'}</span><div><strong>Reference trail</strong><small>Assumptions, source and review boundaries</small></div><b>↗</b></button><details class="scenario-details"><summary>${reserving ? 'Compare a scenario or expert view' : 'Explore benefit cases'} <span>+</span></summary><div class="case-choices">${reserving ? Object.entries(fixtures).map(([id,item])=>`<button data-case="${id}" aria-pressed="${id===state.example}">${item.title}</button>`).join('') : `<button data-annuity="regular" aria-pressed="${annual}">Regular factor</button><button data-annuity="partner" aria-pressed="${!annual}">Fixed-partner benefit</button>`}</div><p>${reserving ? 'Switches between authored reference examples in memory. No calculation, persistence or approval occurs.' : 'Partner cases are not interchangeable: in-payment survivor benefits, known-partner reversionary benefits and marriage-frequency models need distinct contracts.'}</p></details><details class="scope-details"><summary>Method, limits & next cases <span>+</span></summary><p>${reserving ? 'P&C methods, exclusions, tail/window assumptions and manual selections already have deterministic contracts. Bootstrap, reinsurance and universal “every edge case” coverage are not implemented by this prototype.' : 'Annual/monthly timing, finite horizons, both lives, unisex weights and dependence must stay explicit. Marriage-frequency curves or dynamic marriage/divorce/remarriage states are the next specification choice—not a hidden default.'}</p><a href="${sources}${reserving?'cashflow-projection-spec-v2.md':'annuity-factors-spec-v2.md'}" target="_blank" rel="noopener noreferrer">Read the accepted contract ↗</a></details></aside></div><footer class="workspace-footer"><span>No live run. No saved decisions. All figures are authored synthetic references.</span><button data-evidence="performance">Performance & scale policy ↗</button></footer>`;
  surfaceState(); $('workspace-title').tabIndex = -1; $('workspace-title').focus({preventScroll:true}); window.scrollTo({top:0,behavior:'instant'});
}
function variantShift(step) {
  const keys = Object.keys(variants); state.variant = keys[(keys.indexOf(state.variant)+step+keys.length)%keys.length];
  const url = new URL(location.href); url.searchParams.set('variant', state.variant); history.replaceState(null,'',url);
  state.tool = null; renderLibrary(); window.scrollTo({top:0,behavior:'instant'});
}
document.addEventListener('click', event => {
  const tool = event.target.closest('[data-tool]'); if (tool) { state.tool=tool.dataset.tool; renderWorkspace(); }
  if (event.target.closest('[data-home]')) { state.tool=null; renderLibrary(); }
  const evidence = event.target.closest('[data-evidence]'); if (evidence) showEvidence(evidence.dataset.evidence);
  const choice = event.target.closest('[data-case]'); if (choice) { state.example=choice.dataset.case; renderWorkspace(); $('workspace').querySelector('.scenario-details').open=true; $('workspace').querySelector(`[data-case="${state.example}"]`).focus({preventScroll:true}); }
  const benefit = event.target.closest('[data-annuity]'); if (benefit) { state.annuity=benefit.dataset.annuity; renderWorkspace(); $('workspace').querySelector('.scenario-details').open=true; $('workspace').querySelector(`[data-annuity="${state.annuity}"]`).focus({preventScroll:true}); }
});
$('previous-variant').onclick=()=>variantShift(-1); $('next-variant').onclick=()=>variantShift(1);
document.querySelector('.dialog-close').onclick=()=>$('evidence-dialog').close();
document.addEventListener('keydown', event => { if (!$('evidence-dialog').open && ['ArrowLeft','ArrowRight'].includes(event.key) && !event.target.closest('input,textarea,select,[contenteditable="true"]')) { event.preventDefault(); variantShift(event.key==='ArrowRight'?1:-1); } });
reduced.addEventListener('change',()=>state.tool ? surfaceState() : renderLibrary());
window.addEventListener('pagehide',teardown);
renderLibrary();
