// === Evidence Drill-Down Prototype — F004 / #4 ===
// Self-contained static prototype. All data is synthetic inline data.
// No network, no build step, no external dependencies.

(function () {
  'use strict';

  // ── Synthetic inline data ──────────────────────────────────────────
  // Opaque immutable node IDs carry workspace, run, data-version, config, revision.
  const WS = 'WS-42';
  const RUN = 'RUN-7';
  const DV = 'DV-2026-Q2';
  const CFG = 'CFG-RES-01';

  function nid(kind, rev) { return `00000000-0000-4000-8000-${String(rev).replace(/\D/g, '').padStart(12, '0')}`; }

  // Evidence class enum: calc | human | narrative
  const ECalc = 'calculation evidence';
  const EHuman = 'human judgement';
  const ENarr = 'model explanation';

  // Availability: observed | missing | future
  // Validation: valid | warning | invalid
  // Fitting: included | excluded | outside-window

  // Stable cursors for this immutable, synthetic fixture only.

  // ── L0: Workspace summary ──────────────────────────────────────────
  const L0 = {
    level: 0,
    label: 'L0 — Workspace Summary',
    headline: {
      id: nid('headline', 'r1'),
      label: 'Review subtotal — 2026 Q2',
      value: '€17,750,000 · incomplete',
      cls: ECalc,
      avail: 'observed',
      valid: 'warning',
      fit: 'included',
      note: 'Illustrative subtotal for 2023 + 2024. Origin 2025 is blocked. Synthetic UI fixture, not a calculated reserve.',
      provenance: {
        created_at: '2026-09-27T08:14:00Z',
        actor: 'synthetic fixture',
        role: 'illustrative review only',
        library_version: 'not calculated by the library',
        content_hash: 'not computed for this prototype'
      }
    },
    origins: [
      { id: nid('origin', 'r2'), label: 'Origin 2023 — Paid', value: '€8,210,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included',
        assumptions: [
          { id: nid('assumption', 'r3'), label: 'Paid development selection', value: 'Volume-weighted · illustrative', cls: EHuman, avail: 'observed', valid: 'valid', fit: 'included',
            factors: [
              { id: nid('factor', 'r4'), label: 'Illustrative observed pair ratio', value: '1.500 = 1,860,000 / 1,240,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included',
                cells: [
                  { id: nid('cell', 'r5'), label: 'Pair numerator base — earlier paid', value: '€1,240,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included' },
                  { id: nid('cell', 'r6'), label: 'Pair later paid', value: '€1,860,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included' },
                  { id: nid('cell', 'r7'), label: 'Separate zero observation — not in pair', value: '€0', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'outside-window', note: 'observed zero — stays observed' }
                ]
              }
            ]
          }
        ]
      },
      { id: nid('origin', 'r8'), label: 'Origin 2024 — Paid', value: '€9,540,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included',
        assumptions: [
          { id: nid('assumption', 'r9'), label: 'Scenario observation selection', value: 'Inspect inclusion rationale', cls: EHuman, avail: 'observed', valid: 'valid', fit: 'included',
            factors: [
              { id: nid('factor', 'r10'), label: 'Illustrative observed pair ratio', value: '0.642857 = 1,350,000 / 2,100,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'excluded',
                rationale: 'Scenario A excludes the observation pair for a documented correction; Scenario B retains it. Source values are unchanged.',
                cells: [
                  { id: nid('cell', 'r11'), label: 'Paid 2024 Q3', value: '€2,100,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included' },
                  { id: nid('cell', 'r12'), label: 'Paid 2024 Q4', value: '€1,350,000', cls: ECalc, avail: 'observed', valid: 'valid', fit: 'included' }
                ]
              }
            ]
          }
        ]
      },
      { id: nid('origin', 'r13'), label: 'Origin 2025 — Paid', value: 'Unavailable', cls: ECalc, avail: 'missing', valid: 'invalid', fit: 'excluded',
        assumptions: [
          { id: nid('assumption', 'r14'), label: 'Selected paid development pattern', value: 'Required evidence missing', cls: EHuman, avail: 'missing', valid: 'invalid', fit: 'excluded',
            factors: [
              { id: nid('factor', 'r15'), label: 'Paid development factor', value: 'Unavailable', cls: ECalc, avail: 'missing', valid: 'invalid', fit: 'outside-window',
                cells: [
                  { id: nid('cell', 'r16'), label: 'Paid 2025 Q3', value: 'unavailable', cls: ECalc, avail: 'missing', valid: 'invalid', fit: 'excluded',
                    note: 'unavailable-blocked — dependent calculation blocked' }
                ]
              }
            ]
          }
        ]
      }
    ],
    narrativeNode: {
      id: nid('narrative', 'r99'),
      label: 'Model summary paragraph',
      content: 'Illustrative narrative: origin 2025 lacks supporting observations. This prototype cannot establish reserve adequacy or movements.',
      cls: ENarr,
      // CRITICAL: narrative is NEVER a calculation input — shown separately
      cannotBeInput: true
    }
  };

  // ── L1: Node payload + paginated adjacency stubs ────────────────────
  function fetchL1(nodeId, cursor, limit) {
    cursor = cursor || null;
    limit = limit || 5;
    // Simulate async lazy loading
    return new Promise(function (resolve) {
      setTimeout(function () {
        const node = findNode(L0, nodeId);
        if (!node) { resolve({ level: 1, node: null, adjacency: [], nextCursor: null, pageInfo: { limit: limit, returned: 0 } }); return; }
        // Build adjacency stubs from children of this node
        const children = getChildren(L0, nodeId);
        const start = cursor ? Number(cursor.replace('fixture-v1:', '')) : 0;
        const page = children.slice(start, start + limit);
        const nextPageCursor = start + limit < children.length ? `fixture-v1:${start + limit}` : null;
        resolve({
          level: 1,
          node: { id: node.id, label: node.label, value: node.value, cls: node.cls, avail: node.avail, valid: node.valid, fit: node.fit },
          adjacency: page.map(function (c) { return { id: c.id, label: c.label, value: c.value, cls: c.cls, avail: c.avail, valid: c.valid, fit: c.fit }; }),
          nextCursor: nextPageCursor,
          pageInfo: { limit: limit, returned: page.length, total: children.length }
        });
      }, 120); // simulated network delay
    });
  }

  // ── L2: On-demand blobs ────────────────────────────────────────────
  function fetchL2(nodeId) {
    return new Promise(function (resolve) {
      setTimeout(function () {
        const node = findNode(L0, nodeId);
        if (!node) { resolve({ level: 2, nodeId: nodeId, blob: null }); return; }
        resolve({
          level: 2,
          nodeId: nodeId,
          blob: {
            fullLabel: node.label + ' — full detail blob',
            detail: JSON.stringify({ fixture: true, node: node, warning: 'Synthetic UI fixture; not an actuarial calculation trace.' }, null, 2),
            derivedFrom: 'synthetic UI fixture',
            sizeBytes: new TextEncoder().encode(JSON.stringify(node)).length,
            fetchedAt: new Date().toISOString()
          }
        });
      }, 200);
    });
  }

  // ── Data traversal helpers ─────────────────────────────────────────
  function findNode(root, id) {
    if (root.id === id) return root;
    const children = [root.headline, root.narrativeNode, ...(root.origins || []), ...(root.assumptions || []), ...(root.factors || []), ...(root.cells || [])].filter(Boolean);
    for (const child of children) {
      const found = findNode(child, id);
      if (found) return found;
    }
    return null;
  }

  function getChildren(root, id) {
    if (id === root.headline.id) return root.origins;
    const node = findNode(root, id);
    if (!node) return [];
    const out = [];
    if (node.assumptions) node.assumptions.forEach(function (a) { out.push(a); });
    if (node.factors) node.factors.forEach(function (f) { out.push(f); });
    if (node.cells) node.cells.forEach(function (c) { out.push(c); });
    if (node.origins) node.origins.forEach(function (o) { out.push(o); });
    return out;
  }

  // ── UI State ───────────────────────────────────────────────────────
  let currentLevel = 0;
  let expandedNodes = new Set();
  let currentAdjacencyCursor = null;
  let renderRevision = 0;

  // ── Render ─────────────────────────────────────────────────────────
  const surfaceTitle = document.getElementById('surface-title');
  const surfaceContent = document.getElementById('surface-content');
  const surfaceLevelBadge = document.getElementById('surface-level-badge');
  const levelLabel = document.getElementById('level-label');
  const levelDot = document.getElementById('level-dot');
  const provenancePanel = document.getElementById('provenance-panel');
  const provenanceContent = document.getElementById('provenance-content');
  const paginationEl = document.getElementById('surface-pagination');
  const toastEl = document.getElementById('toast');

  function setLevel(lvl) {
    currentLevel = lvl;
    document.querySelectorAll('.nav-btn').forEach(function (b) {
      b.classList.toggle('active', b.dataset.lvl == lvl);
    });
    levelLabel.textContent = ['L0 — Workspace Summary', 'L1 — Node Payloads + Adjacency', 'L2 — On-Demand Blobs'][lvl];
    levelDot.style.background = ['var(--teal)', 'var(--amber)', 'var(--violet)'][lvl];
    surfaceLevelBadge.textContent = 'L' + lvl;
    render();
  }

  function render() {
    renderRevision += 1;
    surfaceContent.innerHTML = '';
    if (currentLevel === 0) renderL0();
    else if (currentLevel === 1) renderL1();
    else renderL2();
  }

  function renderL0() {
    surfaceTitle.textContent = 'Reserve review · follow the evidence';
    // Headline total card
    const h = L0.headline;
    const hCard = mkCard(h, 'card--headline');
    hCard.addEventListener('click', function () { showProvenance(h.provenance); fetchL2(h.id).then(function (r) { showToast('L2 blob fetched for ' + h.id); } ); });
    surfaceContent.appendChild(hCard);

    // Narrative node — shown separately, flagged as non-input
    const n = L0.narrativeNode;
    const nCard = document.createElement('div');
    nCard.className = 'card';
    nCard.style.borderLeftColor = 'var(--violet)';
    nCard.innerHTML = `
      <div class="card__body">
        <div class="card__label">${esc(n.label)} <span class="badge badge--narrative">${n.cls}</span> <span class="badge badge--unavailable">model narrative — never a calculation input</span></div>
        <div class="card__meta"><span>${esc(n.id)}</span></div>
        <div class="card__meta" style="color:var(--violet);margin-top:4px;">"${esc(n.content)}"</div>
      </div>`;
    nCard.addEventListener('click', function () { showProvenance(n.provenance); });
    surfaceContent.appendChild(nCard);

    // Origin rows
    L0.origins.forEach(function (o) {
      const oCard = mkCard(o, 'card--origin');
      oCard.addEventListener('click', function () { toggleExpand(o.id); render(); });
      surfaceContent.appendChild(oCard);
      if (expandedNodes.has(o.id)) {
        // Direct expansion: show assumptions
        o.assumptions.forEach(function (a) {
          const aCard = mkCard(a, 'card--assumption');
          aCard.addEventListener('click', function () { toggleExpand(a.id); render(); });
          surfaceContent.appendChild(aCard);
          if (expandedNodes.has(a.id)) {
            a.factors.forEach(function (f) {
              const fCard = mkCard(f, 'card--factor');
              fCard.addEventListener('click', function () { toggleExpand(f.id); render(); });
              surfaceContent.appendChild(fCard);
              if (expandedNodes.has(f.id)) {
                f.cells.forEach(function (c) {
                  const cCard = mkCard(c, 'card--cell');
                  cCard.addEventListener('click', function () { showProvenance(c.provenance || emptyProv()); });
                  surfaceContent.appendChild(cCard);
                });
              }
            });
          }
        });
      }
    });

    // Exclusion comparison demo (F004: same observation, different scenarios)
    const exDiv = document.createElement('div');
    exDiv.className = 'scenario-compare';
    exDiv.innerHTML = `
      <div class="scenario-col">
        <h4>Scenario A — Factor excluded</h4>
        <div class="card" style="border-left:3px solid var(--red);">
          <div class="card__body">
            <div class="card__label">Origin 2024 Factor <span class="badge badge--excluded">excluded</span></div>
            <div class="card__rationale">Excluded at scenario level — source cell state unchanged</div>
          </div>
        </div>
      </div>
      <div class="scenario-col">
        <h4>Scenario B — Same observation included</h4>
        <div class="card" style="border-left:3px solid var(--green);">
          <div class="card__body">
            <div class="card__label">Origin 2024 Factor <span class="badge badge--included">included</span></div>
            <div class="card__meta" style="color:var(--green);">No mutation of source state</div>
          </div>
        </div>
      </div>`;
    surfaceContent.appendChild(exDiv);

    // Blocked state demo
    const blockedDiv = document.createElement('div');
    blockedDiv.style.marginTop = '12px';
    blockedDiv.innerHTML = `
      <div class="card card--blocked">
        <div class="card__body">
          <div class="card__label">Origin 2025 — Missing Evidence <span class="badge badge--blocked">unavailable-blocked</span></div>
          <div class="card__blocker">Dependent calculation blocked: paid development evidence unavailable. Origin excluded from the review subtotal.</div>
          <div class="card__meta"><span>${esc(L0.origins[2].assumptions[0].factors[0].cells[0].id)}</span></div>
        </div>
      </div>`;
    surfaceContent.appendChild(blockedDiv);
  }

  function renderL1() {
    surfaceTitle.textContent = 'Connected evidence';
    const revision = renderRevision;
    // Show the headline node as selected example
    const h = L0.headline;
    const card = document.createElement('div');
    card.className = 'card card--headline';
    card.innerHTML = `
      <div class="card__body">
        <div class="card__label">${esc(h.label)} <span class="badge badge--calc">${h.cls}</span></div>
        <div class="card__meta"><span class="badge badge--observed">${h.avail}</span> <span class="badge badge--valid">${h.valid}</span> <span class="badge badge--included">${h.fit}</span></div>
        <div class="card__id">${esc(h.id)}</div>
      </div>`;
    card.addEventListener('click', function () { showProvenance(h.provenance); });
    surfaceContent.appendChild(card);

    // Paginated adjacency stubs
    const cursor = currentAdjacencyCursor || null;
    fetchL1(h.id, cursor, 2).then(function (resp) {
      if (revision !== renderRevision) return;
      const list = document.createElement('div');
      list.style.marginTop = '12px';
      list.innerHTML = '<h3 style="font-size:13px;color:var(--text-dim);margin-bottom:8px;">Adjacency Stubs (paginated)</h3>';
      resp.adjacency.forEach(function (adj) {
        const row = document.createElement('div');
        row.className = 'card';
        row.style.cursor = 'pointer';
        row.innerHTML = `
          <div class="card__body">
            <div class="card__label">${esc(adj.label)} <span class="badge badge--${adj.cls === ECalc ? 'calc' : adj.cls === EHuman ? 'human' : 'narrative'}">${adj.cls}</span></div>
            <div class="card__meta"><span>${esc(adj.id)}</span> <span class="badge badge--${adj.avail === 'observed' ? 'observed' : adj.avail === 'missing' ? 'missing' : 'future'}">${adj.avail}</span> <span class="badge badge--${adj.fit === 'included' ? 'included' : adj.fit === 'excluded' ? 'excluded' : 'outside-window'}">${adj.fit}</span></div>
          </div>`;
        row.addEventListener('click', function () { expandedNodes.add(adj.id); currentAdjacencyCursor = null; setLevel(0); });
        list.appendChild(row);
      });
      surfaceContent.appendChild(list);

      // Pagination controls
      const pag = document.createElement('div');
      pag.className = 'pagination';
      pag.innerHTML = `
        <button ${!cursor ? 'disabled' : ''} id="btn-prev-page">← Prev</button>
        <span>Page cursor: ${cursor || 'start'}</span>
        <button ${!resp.nextCursor ? 'disabled' : ''} id="btn-next-page">Next →</button>
        <span style="color:var(--text-dim);font-size:11px;">returned: ${resp.pageInfo.returned}/${resp.pageInfo.total}</span>`;
      surfaceContent.appendChild(pag);
      document.getElementById('btn-prev-page')?.addEventListener('click', function () { /* simplified: reset */ currentAdjacencyCursor = null; render(); });
      document.getElementById('btn-next-page')?.addEventListener('click', function () { currentAdjacencyCursor = resp.nextCursor; render(); });
    });
  }

  function renderL2() {
    surfaceTitle.textContent = 'Source details · synthetic fixture';
    const h = L0.headline;
    surfaceContent.innerHTML = '<p style="color:var(--text-dim);font-size:13px;margin-bottom:12px;">Inspect the actual synthetic fixture behind a card. No live calculation or private data.</p>';
    [L0.headline, ...L0.origins].forEach(function (node) {
      const btn = document.createElement('button');
      btn.className = 'btn';
      btn.style.marginRight = '8px';
      btn.style.marginBottom = '8px';
      btn.textContent = node.label;
      btn.addEventListener('click', function () {
        fetchL2(node.id).then(function (resp) {
          if (currentLevel !== 2) return;
          if (!resp.blob) { showToast('Blob not found'); return; }
          const blobCard = document.createElement('div');
          blobCard.className = 'card';
          blobCard.style.marginTop = '12px';
          blobCard.innerHTML = `
            <div class="card__body">
              <div class="card__label">${esc(resp.blob.fullLabel)} <span class="badge badge--calc">L2 blob</span></div>
              <pre class="fixture-detail">${esc(resp.blob.detail)}</pre>
              <div class="card__meta">Size: ${resp.blob.sizeBytes} bytes | Fetched: ${resp.blob.fetchedAt}</div>
              <div class="card__meta">Derived from: ${resp.blob.derivedFrom}</div>
            </div>`;
          surfaceContent.appendChild(blobCard);
          showToast('L2 blob loaded');
        });
      });
      surfaceContent.appendChild(btn);
    });
  }

  function mkCard(node, extraClass) {
    const clsBadge = node.cls === ECalc ? 'badge--calc' : node.cls === EHuman ? 'badge--human' : 'badge--narrative';
    const availBadge = node.avail === 'observed' ? 'badge--observed' : node.avail === 'missing' ? 'badge--missing' : 'badge--future';
    const fitBadge = node.fit === 'included' ? 'badge--included' : node.fit === 'excluded' ? 'badge--excluded' : 'badge--outside-window';
    const isBlocked = node.avail === 'missing' && node.valid === 'invalid';
    const card = document.createElement('div');
    card.className = 'card ' + (extraClass || '') + (isBlocked ? ' card--blocked' : '');
    card.tabIndex = 0;
    card.setAttribute('role', 'button');
    card.addEventListener('keydown', function (event) { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); card.click(); } });
    let html = `<div class="card__id">${esc(node.id)}</div><div class="card__body">`;
    html += `<div class="card__label">${esc(node.label)} <span class="badge ${clsBadge}">${node.cls}</span></div>`;
    html += `<div class="card__meta"><span class="badge ${availBadge}">${node.avail}</span> <span class="badge badge--${node.valid}">${node.valid}</span> <span class="badge ${fitBadge}">${node.fit}</span>`;
    if (node.value !== undefined) html += ` <strong>${esc(String(node.value))}</strong>`;
    html += `</div>`;
    if (node.note) html += `<div class="card__meta" style="color:var(--teal);">${esc(node.note)}</div>`;
    if (node.rationale) html += `<div class="card__rationale">${esc(node.rationale)}</div>`;
    if (node.cls !== ENarr && !isBlocked) html += `<div class="card__expand">Click to expand / view provenance</div>`;
    html += `</div>`;
    card.innerHTML = html;
    return card;
  }

  function showProvenance(p) {
    p = p || emptyProv();
    provenancePanel.classList.remove('hidden');
    provenanceContent.innerHTML = `
      <dl class="provenance-grid">
        <dt>Created At</dt><dd>${esc(p.created_at || 'unknown')}</dd>
        <dt>Actor</dt><dd>${esc(p.actor || 'unknown')}</dd>
        <dt>Role</dt><dd>${esc(p.role || 'unknown')}</dd>
        <dt>Library Version</dt><dd>${esc(p.library_version || 'unknown')}</dd>
        <dt>Content Hash</dt><dd>${esc(p.content_hash || 'unknown')}</dd>
      </dl>`;
  }

  function toggleExpand(id) {
    if (expandedNodes.has(id)) expandedNodes.delete(id);
    else expandedNodes.add(id);
  }

  function emptyProv() {
    return { created_at: 'unknown (legacy)', actor: 'unknown', role: 'unknown', library_version: 'unknown', content_hash: 'unknown' };
  }

  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // ── Export policy demo ─────────────────────────────────────────────
  document.getElementById('btn-export-local').addEventListener('click', function () {
    const out = document.getElementById('export-output');
    out.classList.remove('hidden');
    out.innerHTML = '<strong style="color:var(--amber)">LOCAL / PRIVATE EXPORT</strong>\n' +
      'Includes: full node IDs (opaque, workspace-scoped), raw hashes, private provenance,\n' +
      'scenario-level exclusion rationales, all adjacency edges.\n' +
      'Never includes: raw claim rows, credentials, private runtime data.\n' +
      '---\n' + JSON.stringify({ headline: L0.headline.id, origins: L0.origins.map(function(o){return o.id;}), narrativeExcluded: true }, null, 2);
    showToast('Local/private export shown');
  });

  document.getElementById('btn-export-public').addEventListener('click', function () {
    const out = document.getElementById('export-output');
    out.classList.remove('hidden');
    out.innerHTML = '<strong style="color:var(--teal)">PUBLIC SYNTHETIC EXPORT</strong> (labelled)\n' +
      'Redacted: opaque IDs truncated, hashes stripped, provenance anonymized.\n' +
      'Only aggregated values + evidence-class badges + availability states.\n' +
      '---\n' + JSON.stringify({ headline: { label: L0.headline.label, value: L0.headline.value, cls: 'calculation', avail: 'observed' }, origins: L0.origins.map(function(o){return {label:o.label,value:o.value,cls:o.cls,avail:o.avail};}) }, null, 2);
    showToast('Public synthetic export shown — clearly labelled');
  });

  // ── Navigation ─────────────────────────────────────────────────────
  document.querySelectorAll('.nav-btn').forEach(function (btn) {
    btn.addEventListener('click', function () { setLevel(parseInt(btn.dataset.lvl, 10)); });
  });

  document.getElementById('btn-close-provenance').addEventListener('click', function () {
    provenancePanel.classList.add('hidden');
  });

  // ── Toast ──────────────────────────────────────────────────────────
  function showToast(msg) {
    toastEl.textContent = msg;
    toastEl.classList.remove('hidden');
    setTimeout(function () { toastEl.classList.add('hidden'); }, 2500);
  }

  // ── Init ───────────────────────────────────────────────────────────
  setLevel(0);

})();
