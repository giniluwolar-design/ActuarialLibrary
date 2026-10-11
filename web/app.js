const $ = (id) => document.getElementById(id);
const state = {
  workspace: null,
  basis: "paid",
  display: "factors",
  tab: "triangles",
  job: null,
  busy: false,
  selected: null,
  evidence: null,
  evidenceRequest: 0,
};
const names = {
  paid_cl: "Paid Chain Ladder",
  incurred_cl: "Incurred Chain Ladder",
  paid_bf: "Paid Bornhuetter–Ferguson",
  incurred_bf: "Incurred Bornhuetter–Ferguson",
  frequency_severity: "Frequency × severity",
  manual: "Manual ultimate",
};
const esc = (value) =>
  String(value ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
const currency = () => state.workspace?.metadata.currency || "EUR";
const money = (v, compact = false) =>
  v == null
    ? "Unavailable"
    : new Intl.NumberFormat("en-GB", {
        style: "currency",
        currency: currency(),
        notation: compact ? "compact" : "standard",
        maximumFractionDigits: compact ? 2 : 0,
      }).format(v);
const number = (v, d = 3) =>
  v == null
    ? "Unavailable"
    : Number(v).toLocaleString("en-GB", {
        minimumFractionDigits: d,
        maximumFractionDigits: d,
      });
async function api(path, body) {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : JSON.stringify(data.detail || "Request failed"),
    );
  return data;
}
function notice(message) {
  $("notice").textContent = message || "";
  $("notice").hidden = !message;
}
function remember(key, value) {
  try {
    if (value === null) localStorage.removeItem(key);
    else localStorage.setItem(key, value);
  } catch {
    /* API saves still work without browser storage. */
  }
}
function recalled(key) {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
function setBusy(value) {
  $("explain-library").disabled = value || !!state.job || !state.workspace;
  state.busy = value;
  document
    .querySelectorAll(
      "#setup button,#report,#scenario-form button,#exclude-form button",
    )
    .forEach((el) => (el.disabled = value || !!state.job));
  $("send").disabled =
    value || !!state.job || !$("model").value || !state.workspace;
  document
    .querySelectorAll("[data-prompt]")
    .forEach((el) => (el.disabled = $("send").disabled));
}
function showTab(tab) {
  state.tab = tab;
  document
    .querySelectorAll(".view")
    .forEach((el) => (el.hidden = el.id !== `view-${tab}`));
  document.querySelectorAll("[data-tab]").forEach((el) => {
    el.classList.toggle("active", el.dataset.tab === tab);
    if (el.getAttribute("role") === "tab")
      el.setAttribute("aria-selected", String(el.dataset.tab === tab));
  });
}
function latest(values) {
  return values.map((row, i) => row[values.length - i - 1]);
}
function total(values) {
  return values.every((v) => v !== null)
    ? values.reduce((a, b) => a + b, 0)
    : null;
}
function render() {
  const w = state.workspace;
  if (!w) return;
  const portfolio = w.metadata.portfolio;
  $("portfolio").value = portfolio;
  $("valuation").value = w.valuation;
  $("grain").value = w.grain;
  $("side-portfolio").textContent = portfolio;
  $("side-valuation").textContent = new Date(
    `${w.valuation}T12:00:00`,
  ).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "long",
    year: "numeric",
  });
  $("agent-context").textContent =
    `${portfolio} · ${w.valuation} · ${w.grain === "Y" ? "Annual" : "Quarterly"}`;
  $("save-state").textContent = "Saved locally";
  $("run-id").textContent = `WORKSPACE ${w.id.slice(0, 8)}`;
  const paid = total(latest(w.triangles.paid)),
    incurred = total(latest(w.triangles.incurred));
  $("kpi-paid").textContent = money(paid, true);
  $("kpi-incurred").textContent = money(incurred, true);
  $("kpi-case").textContent = money(
    paid == null || incurred == null ? null : incurred - paid,
    true,
  );
  $("kpi-paid").title = money(paid);
  $("kpi-incurred").title = money(incurred);
  $("kpi-case").title = money(
    paid == null || incurred == null ? null : incurred - paid,
  );
  const origin = $("origin").value;
  $("origin").innerHTML = w.origins
    .map((o) => `<option>${esc(o)}</option>`)
    .join("");
  $("origin").value = w.origins.includes(origin) ? origin : w.origins.at(-1);
  $("diagnostic-count").textContent =
    `${w.analysis.warnings.length} calculation diagnostics`;
  $("diagnostics").innerHTML = w.analysis.warnings
    .map((x) => `<li>${esc(x)}</li>`)
    .join("");
  $("export").href = `/api/workspaces/${w.id}/export`;
  renderTriangle();
  renderLosses();
  renderMethods();
  renderScenarios();
  renderChat();
  renderFiles();
  setBusy(state.busy);
}
function renderTriangle() {
  const w = state.workspace;
  if (!w) return;
  const factors = state.display === "factors",
    values = factors
      ? w.development_factors[state.basis]
      : w.triangles[state.basis];
  $("triangle-title").textContent = factors
    ? "Age-to-age factors"
    : "Cumulative observations";
  $("triangle-periods").textContent =
    `${w.origins.length} ${w.grain === "Y" ? "annual" : "quarterly"} periods`;
  let html =
    "<table><thead><tr><th>Accident<br>period</th>" +
    values[0]
      .map(
        (_, j) =>
          `<th>${factors ? `${j + 1} → ${j + 2}` : `Age ${j + 1}`}</th>`,
      )
      .join("") +
    "</tr></thead><tbody>";
  values.forEach((row, i) => {
    html +=
      `<tr><td>${esc(w.origins[i])}</td>` +
      row
        .map((v, j) => {
          const future = factors
            ? w.states[i][j + 1] === "future"
            : w.states[i][j] === "future";
          if (v == null)
            return `<td class="${future ? "future" : "missing"}" title="${future ? "Future observation" : factors ? "Missing or invalid denominator" : "Missing observation"}">${future ? "·" : "—"}</td>`;
          const strength = factors
            ? Math.min(1, Math.max(0, Math.log(Math.max(v, 1)) / Math.log(4)))
            : 0;
          const light = 96 - strength * 61;
          const style = `--cell:hsl(164 24% ${light}%);color:${strength > 0.67 ? "#fff" : "#355d53"}`;
          return factors
            ? `<td class="factor-cell ${v < 1 ? "below" : ""}" style="${style}"><button data-origin="${esc(w.origins[i])}" data-development="${j + 1}" aria-label="Inspect ${esc(w.origins[i])}, development ${j + 1} to ${j + 2}, factor ${number(v)}">${number(v)}</button></td>`
            : `<td class="factor-cell" style="${style}" title="${number(v, 0)}">${number(v, 0)}</td>`;
        })
        .join("") +
      "</tr>";
  });
  $("factor-table").innerHTML = html + "</tbody></table>";
}
function renderLosses() {
  const w = state.workspace,
    p = latest(w.triangles.paid),
    inc = latest(w.triangles.incurred);
  const max = Math.max(...inc.filter((v) => v != null), 1);
  $("chart-unit").textContent = currency();
  $("loss-chart").innerHTML = w.origins
    .map((o, i) => {
      if (p[i] == null || inc[i] == null || p[i] < 0 || inc[i] < p[i])
        return `<div class="loss-bar" title="${esc(o)}: missing or negative components; inspect triangle"><span>${i % Math.ceil(w.origins.length / 9) === 0 ? esc(o) : ""}</span></div>`;
      return `<div class="loss-bar" title="${esc(o)} · paid ${money(p[i])} · case ${money(inc[i] - p[i])}"><div class="case" style="height:${((inc[i] - p[i]) / max) * 100}%"></div><div class="paid" style="height:${(p[i] / max) * 100}%"></div><span>${i % Math.ceil(w.origins.length / 9) === 0 ? esc(o) : ""}</span></div>`;
    })
    .join("");
}
function renderMethods() {
  if (!state.workspace) return;
  const rows = state.workspace.analysis.results.filter(
    (r) => r.origin === $("origin").value,
  );
  const max = Math.max(...rows.map((r) => Math.abs(r.ultimate || 0)), 1);
  $("method-chart").innerHTML = rows
    .map(
      (r) =>
        `<div class="method-bar"><span>${esc(names[r.method] || r.method)}</span><div class="track"><div class="fill" style="width:${(Math.abs(r.ultimate || 0) / max) * 100}%"></div></div><strong>${r.ultimate == null ? "Unavailable" : money(r.ultimate, true)}</strong></div>`,
    )
    .join("");
  $("method-table").innerHTML =
    '<table class="method-table"><thead><tr><th>Method</th><th>Ultimate</th><th>Outstanding</th><th>Additional reserve</th><th>Evidence</th></tr></thead><tbody>' +
    rows
      .map(
        (r) =>
          `<tr><td>${esc(names[r.method] || r.method)}${r.reason ? `<small class="method-reason">${esc(r.reason)}</small>` : ""}</td><td>${money(r.ultimate)}</td><td>${money(r.outstanding)}</td><td>${money(r.additional_reserve)}</td><td><button type="button" class="text-button" data-evidence-method="${esc(r.method)}" data-evidence-origin="${esc(r.origin)}">Review evidence</button></td></tr>`,
      )
      .join("") +
    "</tbody></table>";
}
function closeEvidence() {
  state.evidenceRequest += 1;
  $("evidence-review").hidden = true;
  state.evidence?.trigger?.focus();
  state.evidence = null;
}
function evidencePath(node) {
  return `/api/workspaces/${state.workspace.id}/graph/nodes/${encodeURIComponent(node.node_id)}`;
}
function evidenceLinks(items) {
  return items.map((item) => `<button type="button" class="evidence-link" data-evidence-node="${esc(item.node_id)}" data-evidence-revision="${item.revision}" data-evidence-class="${esc(item.node_class)}"><small>${esc(item.direction)} · ${esc(item.type.replaceAll("_", " "))}</small><strong>${esc(item.label)}</strong><span>${esc(item.node_class)}${item.metadata?.fitting_membership ? ` · ${esc(item.metadata.fitting_membership)}` : ""}</span></button>`).join("");
}
function evidenceLabel(node) {
  return node.node_class === "calc/result" && node.summary?.method
    ? `${node.summary.origin} · ${names[node.summary.method] || node.summary.method}`
    : node.label;
}
function evidenceValue(key, value) {
  if (["ultimate", "outstanding", "additional_reserve"].includes(key) && typeof value === "number")
    return new Intl.NumberFormat("en-GB", { style: "currency", currency: currency(), minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value);
  if (key === "method") return names[value] || value;
  if (typeof value === "object") return Array.isArray(value) ? `${value.length} recorded entries · load payload to inspect` : JSON.stringify(value);
  return value;
}
function displayEvidence(node, page) {
  const trail = state.evidence.trail;
  $("evidence-title").textContent = evidenceLabel(node);
  $("evidence-breadcrumbs").innerHTML = trail.map((entry, index) => `<button type="button" class="text-button" data-evidence-trail="${index}" ${index === trail.length - 1 ? 'aria-current="page"' : ""}>${esc(evidenceLabel(entry))}</button>`).join('<span aria-hidden="true">›</span>');
  const fields = { ...node.summary, availability: node.state || node.summary?.availability, reason: node.reason_code || node.summary?.reason_code };
  $("evidence-summary").innerHTML = Object.entries(fields).filter(([, value]) => value != null).map(([key, value]) => `<div><dt>${esc(key.replaceAll("_", " "))}</dt><dd>${esc(evidenceValue(key, value))}</dd></div>`).join("");
  $("evidence-provenance").textContent = JSON.stringify({ node_id: node.node_id, revision: node.revision, run_id: node.run_id, node_class: node.node_class, data_version: node.data_version, config_hash: node.config_hash, content_sha256: node.content_sha256, authorship: node.authorship, evidential_role: node.evidential_role }, null, 2);
  $("evidence-links").innerHTML = evidenceLinks(page.items);
  $("evidence-next").hidden = !page.has_more;
  state.evidence.cursor = page.next_cursor;
  $("evidence-status").textContent = page.items.length ? `${page.items.length} connections loaded${page.has_more ? " · more available" : ""}.` : "No connections are recorded for this node.";
  $("evidence-load-payload").disabled = false;
  $("evidence-payload").hidden = true;
  $("evidence-payload").textContent = "";
  $("evidence-export").href = `/api/workspaces/${state.workspace.id}/graph/export?run=${encodeURIComponent(node.run_id)}`;
  $("evidence-title").focus({ preventScroll: true });
}
async function openEvidenceNode(reference, trailIndex = null) {
  const request = ++state.evidenceRequest;
  $("evidence-review").hidden = false;
  $("evidence-status").textContent = "Loading recorded evidence…";
  $("evidence-links").innerHTML = "";
  $("evidence-next").hidden = true;
  $("evidence-load-payload").disabled = true;
  $("evidence-payload").hidden = true;
  const query = `?revision=${reference.revision}`;
  try {
    const [node, page] = await Promise.all([api(evidencePath(reference) + query), api(evidencePath(reference) + `/adjacency${query}&limit=50`)]);
    if (request !== state.evidenceRequest || !state.evidence) return;
    state.evidence.trail = trailIndex == null ? [...state.evidence.trail, node] : state.evidence.trail.slice(0, trailIndex + 1);
    state.evidence.node = node;
    displayEvidence(node, page);
  } catch (error) {
    if (request === state.evidenceRequest) $("evidence-status").textContent = `Evidence unavailable: ${error.message}`;
  }
}
async function reviewResult(button) {
  closeEvidence();
  const request = ++state.evidenceRequest;
  state.evidence = { trail: [], trigger: button, node: null, cursor: null };
  $("evidence-review").hidden = false;
  $("evidence-status").textContent = "Loading saved result references…";
  try {
    const summary = await api(`/api/workspaces/${state.workspace.id}/graph`);
    if (request !== state.evidenceRequest) return;
    const result = summary.headline.find(row => row.origin === button.dataset.evidenceOrigin && row.method === button.dataset.evidenceMethod);
    if (!result) throw new Error("No stored result reference exists for this method and period.");
    await openEvidenceNode({ node_id: result.result_node_id, revision: result.revision });
    $("evidence-review").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) {
    if (request === state.evidenceRequest) $("evidence-status").textContent = `Evidence unavailable: ${error.message}`;
  }
}
async function moreEvidence() {
  const evidence = state.evidence;
  if (!evidence?.cursor || !evidence.node) return;
  const request = state.evidenceRequest;
  $("evidence-next").disabled = true;
  try {
    const page = await api(evidencePath(evidence.node) + `/adjacency?revision=${evidence.node.revision}&limit=50&cursor=${encodeURIComponent(evidence.cursor)}`);
    if (request !== state.evidenceRequest) return;
    $("evidence-links").insertAdjacentHTML("beforeend", evidenceLinks(page.items));
    evidence.cursor = page.next_cursor;
    $("evidence-next").hidden = !page.has_more;
    $("evidence-status").textContent = `${$("evidence-links").children.length} connections loaded${page.has_more ? " · more available" : ""}.`;
  } catch (error) {
    if (request === state.evidenceRequest) $("evidence-status").textContent = error.message;
  } finally {
    $("evidence-next").disabled = false;
  }
}
async function loadEvidencePayload() {
  const node = state.evidence?.node;
  if (!node) return;
  const request = state.evidenceRequest;
  $("evidence-load-payload").disabled = true;
  try {
    const payload = await api(evidencePath(node) + `/payload?revision=${node.revision}`);
    if (request !== state.evidenceRequest) return;
    $("evidence-payload").textContent = JSON.stringify(payload, null, 2);
    $("evidence-payload").hidden = false;
  } catch (error) {
    if (request === state.evidenceRequest) $("evidence-status").textContent = error.message;
  } finally {
    $("evidence-load-payload").disabled = false;
  }
}
function renderScenarios() {
  const w = state.workspace;
  $("scenario-count").textContent = w.scenarios.length;
  if (!w.scenarios.length) {
    $("scenario-list").innerHTML =
      '<div class="empty">No scenarios yet. Inspect a factor or test a window and tail above.</div>';
    return;
  }
  $("scenario-list").innerHTML = w.scenarios
    .map((s) => {
      const changes = ["paid", "incurred", "count"].filter(
        (b) =>
          JSON.stringify(s.config[b]) !== JSON.stringify(w.analysis.config[b]),
      );
      const rows = s.impact.filter((r) => r.origin === w.origins.at(-1));
      return `<article class="card scenario-card"><div class="eyebrow">EXPLORATORY · BASELINE UNCHANGED</div><h2>${esc(s.id.replace("_", " "))} · ${esc(changes.join(", "))}</h2><p>${esc(changes.map((b) => s.config[b].rationale).join(" "))}</p><p>Latest accident period: ${esc(w.origins.at(-1))}. Same data and valuation.</p><div class="table-scroll"><table><thead><tr><th>Method</th><th>Baseline ultimate</th><th>Scenario ultimate</th><th>Change</th></tr></thead><tbody>${rows.map((r) => `<tr><td>${esc(names[r.method] || r.method)}</td><td>${money(r.baseline_ultimate)}</td><td>${money(r.scenario_ultimate)}</td><td>${money(r.ultimate_change)}</td></tr>`).join("")}</tbody></table></div><a class="text-button" href="/api/workspaces/${w.id}/export?scenario=${s.id}">Download all periods & assumptions ↓</a></article>`;
    })
    .join("");
}
function renderFiles() {
  const w = state.workspace;
  $("files").innerHTML = w.record.files
    .map(
      (f) =>
        `<a class="download-card" href="/api/workspaces/${w.id}/files/${f.id}"><span class="file-icon">${f.filename.endsWith(".md") ? "MD" : "ZIP"}</span><div><strong>${esc(f.filename)}</strong><p>${number(f.bytes / 1024, 1)} KB · ${esc(f.id)} · saved locally</p></div><span>↓</span></a>`,
    )
    .join("");
}
function renderChat() {
  const w = state.workspace;
  $("chat-messages").innerHTML = w.record.transcript
    .map(
      (m) =>
        `<div class="message ${m.role === "user" ? "user" : "assistant"}"><strong>${m.role === "user" ? "YOU" : "LOCAL ANALYST"}</strong>${esc(m.content)}</div>`,
    )
    .join("");
  if (w.record.evidence.length) {
    $("chat-messages").insertAdjacentHTML(
      "beforeend",
      `<div class="message"><details><summary>Inspect ${w.record.evidence.length} evidence calls</summary>${w.record.evidence.map((e) => `<details><summary>${esc(e.id)} · ${esc(e.tool)}</summary><pre>${esc(JSON.stringify(e, null, 2))}</pre></details>`).join("")}</details></div>`,
    );
  }
  if (w.record.files.length) {
    $("chat-messages").insertAdjacentHTML(
      "beforeend",
      `<button class="text-button" data-tab="files">${w.record.files.length} saved file(s) · Open downloads →</button>`,
    );
  }
}
async function loadWorkspace(newView = false) {
  if (state.busy || state.job) return;
  setBusy(true);
  notice("");
  try {
    const saved = newView ? null : recalled("actuarial-workspace");
    let w;
    if (saved) {
      try {
        w = await api(`/api/workspaces/${saved}`);
      } catch (e) {
        remember("actuarial-workspace", null);
        notice(`Previous workspace unavailable: ${e.message}`);
      }
    }
    if (!w)
      w = await api("/api/workspaces", {
        portfolio: $("portfolio").value,
        valuation: $("valuation").value,
        grain: $("grain").value,
      });
    closeEvidence();
    state.workspace = w;
    remember("actuarial-workspace", w.id);
    $("observation").hidden = true;
    render();
  } catch (e) {
    notice(e.message);
    $("save-state").textContent = "Could not open workspace";
  } finally {
    setBusy(false);
  }
}
async function refreshModels() {
  try {
    const data = await api("/api/health");
    const current = $("model").value || recalled("actuarial-model");
    $("model").innerHTML = data.ollama_models
      .map((m) => `<option value="${esc(m)}">${esc(m)}</option>`)
      .join("");
    if (data.ollama_models.includes(current)) $("model").value = current;
    $("model-status").textContent = data.ollama_models.length
      ? "Local model ready"
      : "Ollama is not connected";
    $("model-help").textContent =
      data.model_error ||
      "Runs on this computer without a paid API key. Hardware and electricity costs still apply.";
  } catch (e) {
    $("model-status").textContent = "Local service unavailable";
    $("model-help").textContent = e.message;
  }
  setBusy(state.busy);
}
async function tool(name, args) {
  if (!state.workspace || state.busy || state.job) return;
  setBusy(true);
  notice("");
  try {
    const result = await api(`/api/workspaces/${state.workspace.id}/tools`, {
      name,
      arguments: args,
    });
    state.workspace = result.workspace;
    render();
    return result.result;
  } catch (e) {
    notice(e.message);
    return null;
  } finally {
    setBusy(false);
  }
}
async function inspect(origin, development) {
  if (!state.workspace) return;
  const key = state.workspace.id,
    basis = state.basis;
  try {
    const rows = await api(
      `/api/workspaces/${key}/observations?basis=${basis}&development=${development}`,
    );
    if (key !== state.workspace.id || basis !== state.basis) return;
    const row = rows.find((r) => r.origin === origin);
    if (!row) return;
    state.selected = { origin, development, basis };
    $("observation-title").textContent =
      `${origin} · ${basis} · ${development} → ${development + 1}`;
    $("observation-detail").innerHTML =
      `<dl><div><dt>Observed ratio</dt><dd>${number(row.link_ratio)}</dd></div><div><dt>Fitting weight</dt><dd>${row.volume_weight == null ? "Not used" : number(row.volume_weight * 100, 1) + "%"}</dd></div><div><dt>Selected factor</dt><dd>${number(row.selected_factor)}</dd></div><div><dt>Membership</dt><dd>${esc(row.status)}</dd></div></dl><p class="footnote">From ${basis === "count" ? number(row.from_amount, 0) : money(row.from_amount)} to ${basis === "count" ? number(row.to_amount, 0) : money(row.to_amount)}. An unusual observation is a prompt to investigate.</p>`;
    $("observation").hidden = false;
    $("observation").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) {
    notice(e.message);
  }
}
async function ask(prompt) {
  if (!prompt.trim() || !state.workspace || state.job || state.busy) return;
  setBusy(true);
  notice("");
  try {
    const job = await api(`/api/workspaces/${state.workspace.id}/chat`, {
      prompt,
      model: $("model").value,
    });
    state.job = job;
    remember("actuarial-job", job.id);
    $("prompt").value = "";
    $("chat-messages").insertAdjacentHTML(
      "beforeend",
      `<div class="message user"><strong>YOU</strong>${esc(prompt)}</div>`,
    );
    $("chat-scroll").scrollTop = $("chat-scroll").scrollHeight;
    pollJob();
  } catch (e) {
    notice(e.message);
  } finally {
    setBusy(false);
  }
}
async function pollJob() {
  if (!state.job) return;
  try {
    const job = await api(`/api/jobs/${state.job.id}`);
    state.job = job;
    $("job-progress").hidden = false;
    $("job-label").textContent =
      `${job.progress} · ${Math.floor((Date.now() / 1000 - job.started_at) / 60)}m ${Math.floor((Date.now() / 1000 - job.started_at) % 60)}s`;
    $("cancel-job").disabled = job.status === "cancelling";
    if (!["queued", "running", "cancelling"].includes(job.status)) {
      state.job = null;
      remember("actuarial-job", null);
      $("job-progress").hidden = true;
      state.workspace = await api(`/api/workspaces/${job.workspace_id}`);
      remember("actuarial-workspace", state.workspace.id);
      render();
      if (job.status !== "completed")
        notice(`Analyst ${job.status}: ${job.progress}`);
      $("chat-scroll").scrollTop = $("chat-scroll").scrollHeight;
      setBusy(false);
      return;
    }
  } catch (e) {
    $("job-label").textContent =
      `Connection interrupted. Reconnecting… ${e.message}`;
  }
  $("job-progress").hidden = false;
  setBusy(state.busy);
  setTimeout(pollJob, 1800);
}
document.addEventListener("click", (e) => {
  const tab = e.target.closest("[data-tab]");
  if (tab) showTab(tab.dataset.tab);
  const starter = e.target.closest("[data-prompt]");
  if (starter && !starter.disabled) ask(starter.dataset.prompt);
  const cell = e.target.closest("[data-origin]");
  if (cell) inspect(cell.dataset.origin, Number(cell.dataset.development));
  const result = e.target.closest("[data-evidence-method]");
  if (result) reviewResult(result);
  const node = e.target.closest("[data-evidence-node]");
  if (node) openEvidenceNode({ node_id: node.dataset.evidenceNode, revision: Number(node.dataset.evidenceRevision) });
  const trail = e.target.closest("[data-evidence-trail]");
  if (trail && state.evidence) {
    const index = Number(trail.dataset.evidenceTrail);
    openEvidenceNode(state.evidence.trail[index], index);
  }
});
$("close-evidence").onclick = closeEvidence;
$("evidence-next").onclick = moreEvidence;
$("evidence-load-payload").onclick = loadEvidencePayload;
$("setup").onsubmit = (e) => {
  e.preventDefault();
  loadWorkspace(true);
};
$("origin").onchange = renderMethods;
$("basis").onchange = () => {
  state.basis = $("basis").value;
  $("observation").hidden = true;
  renderTriangle();
};
for (const display of ["factors", "amounts"])
  $(`show-${display}`).onclick = () => {
    state.display = display;
    for (const d of ["factors", "amounts"]) {
      $(`show-${d}`).classList.toggle("active", d === display);
      $(`show-${d}`).setAttribute("aria-pressed", String(d === display));
    }
    renderTriangle();
  };
$("close-observation").onclick = () => {
  $("observation").hidden = true;
};
$("exclude-form").onsubmit = async (e) => {
  e.preventDefault();
  if (!state.selected) return;
  const s = state.selected;
  const result = await tool("compare_scenario", {
    basis: s.basis,
    exclude_origin: s.origin,
    exclude_development: s.development,
    reason: $("exclusion-reason").value,
  });
  if (result) {
    $("observation").hidden = true;
    showTab("scenarios");
  }
};
$("scenario-form").onsubmit = async (e) => {
  e.preventDefault();
  const result = await tool("compare_scenario", {
    basis: $("scenario-basis").value,
    window: $("scenario-window").value
      ? Number($("scenario-window").value)
      : null,
    tail: Number($("scenario-tail").value),
    reason: $("scenario-reason").value,
  });
  if (result) showTab("scenarios");
};
$("report").onclick = async () => {
  const result = await tool("create_artifact", { artifact: "report" });
  if (result) showTab("files");
};
$("chat-form").onsubmit = (e) => {
  e.preventDefault();
  ask($("prompt").value);
};
$("prompt").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    ask(e.target.value);
  }
});
$("refresh-models").onclick = refreshModels;
$("model").onchange = () => {
  remember("actuarial-model", $("model").value);
  setBusy(state.busy);
};
$("cancel-job").onclick = async () => {
  if (state.job) {
    try {
      await api(`/api/jobs/${state.job.id}/cancel`, {});
    } catch (e) {
      notice(e.message);
    }
  }
};
// Keyboard navigation for the tab list.
document.querySelector(".tabs").addEventListener("keydown", (e) => {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key)) return;
  const tabs = [...document.querySelectorAll(".tabs button")],
    current = tabs.indexOf(document.activeElement);
  if (current < 0) return;
  e.preventDefault();
  const index =
    e.key === "Home"
      ? 0
      : e.key === "End"
        ? tabs.length - 1
        : (current + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) %
          tabs.length;
  tabs[index].focus();
  showTab(tabs[index].dataset.tab);
});
await Promise.all([loadWorkspace(), refreshModels()]);
const jobId = recalled("actuarial-job");
if (jobId) {
  try {
    const job = await api(`/api/jobs/${jobId}`);
    state.job = job;
    pollJob();
  } catch {
    remember("actuarial-job", null);
  }
}

$("explain-library").onclick = async () => {
  if (!state.workspace || state.busy || state.job) return;
  setBusy(true); notice("");
  try {
    const response = await api(`/api/workspaces/${state.workspace.id}/explain`, {});
    state.workspace = response.workspace; render();
    $("chat-scroll").scrollTop = $("chat-scroll").scrollHeight;
  } catch (e) { notice(e.message); } finally { setBusy(false); }
};
$("feedback-form").onsubmit = async (event) => {
  event.preventDefault(); if (!state.workspace) return;
  $("feedback-submit").disabled = true;
  try {
    const saved = await api(`/api/workspaces/${state.workspace.id}/feedback`, {
      kind: $("feedback-kind").value, message: $("feedback-message").value
    });
    $("feedback-status").textContent = `Saved locally · ${saved.id.slice(0, 8)}. Thank you.`;
    $("feedback-message").value = "";
  } catch (e) { $("feedback-status").textContent = e.message; }
  finally { $("feedback-submit").disabled = false; }
};
