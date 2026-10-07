# Wave 1 review package — for the lead architect (Codex)

**From:** `project_manager` pane (OpenCode), 25 September 2026
**Status:** DRAFTS FOR REVIEW — nothing accepted, no code changed, no GitHub mutations, no issues closed.
**Review update, 27 September:** See [lead-architect verdict](review-2026-09-27-wave1-verdict.md) for decisions, required corrections and next assignments. The original draft below is preserved as review history; conflicting recommendations are superseded.
**Privacy:** contains only non-private repository source, documentation and issue content. No `local_runs/`, `data/private/`, credentials, secrets or raw claims data.

## 0. Delegation log

| Task | Agent type | Local session reference |
|---|---|---|
| First-commit inventory scan | general (read-only) | omitted from public memory |
| Evidence inventory scan (input to #4) | explore (very thorough) | omitted from public memory |
| Cash-flow semantics scan (input to #6) | explore (very thorough) | omitted from public memory |
| AG ingestion scan (input to #9) | explore (medium) | omitted from public memory |
| Draft #4 Evidence Graph contract | general (read-only) | omitted from public memory |
| Draft #6 cash-flow projection | general (read-only) | omitted from public memory |
| Draft #8 unisex annuity factors | general (read-only) | omitted from public memory |
| Draft #9 AG ingestion + rights | general (read-only) | omitted from public memory |

Verification at delegation time: `PYTHONPATH=src .venv/bin/python -m pytest -q` → 33 passed; `node --input-type=module --check < web/app.js` → OK; workspace service not running (expected in blueprint phase). All subagents were read-only and privacy-bounded.

---

## 1. DRAFT — #4 Evidence Graph contract

**DRAFT — FOR LEAD-ARCHITECT REVIEW, NOT AN ACCEPTED DECISION**

**Evidence Graph Contract — proposal for issue #4**
Grounded in code scan of `src/actuarial_library/workspace.py:81-118`, `workspace.py:17-78`, `agent.py:376-384`, `server.py:122-145`, `models.py:16-76`, `review.py:10-67`, `tests/test_workspace.py`; product decisions F004 (FEEDBACK.md), HANDOVER.md 25 Sept decisions; LESSONS.md L002/L003.

### 0. Grounding

Today there is no graph, only adjacency inside one payload: `WorkspaceStore` writes one JSON blob per row with `INSERT OR REPLACE` (`src/actuarial_library/workspace.py:93-98`); `workspace_view` returns the entire workspace in one response (`server.py:122-145`). Evidence is a list of `{id: "T{n}", tool, arguments, result}` records with sequential per-workspace ids, no timestamps or hashes (`agent.py:376-384`). The F004 acceptance — every displayed relationship resolves to recorded evidence, from headline result to source data, assumptions, methods, controls and explanations — requires a real typed graph.

### 1. Node and relationship types

**Identity scheme.** `node_id = "{type}:{workspace_id}:{local_key}"` (e.g. `result:w40c1:baseline`, `cell:w40c1:paid:2023:3`), namespaced, globally unique, never reused. Each node carries `schema_version: int`, typed with a Pydantic `StrictModel` like `models.py:12-13` (extra=forbid). Every node has required provenance: `created_at` (UTC), `actor` + `role`, `library_version`, `workspace_id`, `class` (see §6), and `content_sha256` where a payload exists.

| Type | Local key | Payload highlights | Immutability |
|---|---|---|---|
| `data/source` | source slug | portfolio, currency, amount_basis, grain, valuation, `claims_hash`/`coverage_hash`, **privacy_class: private** | Immutable; new upload = new node |
| `triangle/cell` | basis:origin:dev | value, state (§5), `derived_from` source | Immutable value; state fixed at source version |
| `assumption/exclusion` | basis:origin:dev | rationale (required, per `models.py:28-29`), author, scope | Never deleted; superseded only |
| `calc/factor` | basis:dev | selected factor, method, window, volume weights (schema per `review.py:10-67`) | Immutable per config revision |
| `calc/result` | baseline \| scenario slug | full `AnalysisResult.to_dict()` + config snapshot + input hashes | Immutable once saved (L002) |
| `analysis/scenario` | slug | label, `based_on` result id, config delta | Immutable; labelled, never final |
| `control/check` | code:subject | typed warning `{code, severity, message, subject_ids, state}` replacing flat strings | Immutable evaluation record |
| `artifact/file` | slug | filename, bytes, sha256, created_at, created_by, result/scenario ref | Immutable content; content blob separate |
| `doc/source` | slug | filename, mime, sha256, privacy_class | Immutable; text in blob store |
| `tool/invocation` | legacy `T{n}` | tool, arguments, result, created_at (migrated §7) | Immutable |
| `narrative/explanation` | slug | text, model_info, refs — **model-authored only** | Immutable; labelled |
| `judgement/selection` | slug | method selection, manual ultimate, sign-off; author, role, created_at | Human-authored only; superseded, never deleted |

**Privacy rule (hard):** the claims Parquet and any raw claim rows are never node payloads. `data/source` stores hashes and summary metadata only; raw rows live in the private blob store, reachable only via a local content route (today `/observations` and `Triangle.trace`, `models.py:127-137`). The public/exportable graph contains zero private-class payload bytes.

**Edge types (immutable rows):** `derived_from`, `used_observation` (factor→cell pair), `excludes` (exclusion→cell pair), `based_on` (scenario→baseline result), `has_control` (result→control), `produced` (tool call→artifact/scenario), `cites` (narrative/judgement/explanation→any node, with optional `{page, offset, length}` span), `explains` (explanation→result, one-directional), `supersedes` (node→node), `responds_to` (tool call→transcript turn). No `supports` edge may originate from a `narrative/*` node — that is the enforcement hook for "no model explanation as calculation evidence."

### 2. Immutability and versioning

Replace whole-payload overwrite with append-only history: `nodes(node_id, revision, payload, created_at, class)` keyed on `(node_id, revision)`, plus `edges` rows that are never updated — a changed fact is a new node revision (or superseding node) plus new edges. The current `sessions` blob (`workspace.py:17-46`) survives during migration (§7).

- **Saved baseline under code change:** a saved `calc/result` is a recorded historical output forever (L002). New library version → new run creates a *new* node with `supersedes` edge and its own `library_version`; the old payload is never rewritten. The UI shows "computed under v0.x" rather than recomputing silently.
- **Recompute-on-demand vs stored:** rule — a value is recomputed on demand iff it is a pure deterministic function of immutable ancestors and not referenced by a saved result (per-cell observations, factor triangles: today already recomputed via `review.py:10-67` and `server.py` routes). Anything referenced by a saved result, scenario or artifact, or expensive (a full reserving run), is stored at save time. When both stored and recomputed copies exist, compare `content_sha256`; mismatch raises a typed control, never a silent overwrite.

### 3. Structured vs unstructured evidence

Free text never floats: exclusion rationale and `selection_notes` are required *fields* of typed nodes (`models.py:28-29`, `models.py:73-75` precedent); uploaded documents become `doc/source` nodes with `cites` edges carrying spans; model narrative becomes `narrative/explanation` nodes. Today's prose `[T1]` citations migrate to explicit `cites` edges while keeping the text unchanged, so both views resolve.

### 4. Lazy loading

Three levels, replacing the single mega-response (`server.py:122-145`):

- **L0 (upfront):** workspace summary — metadata, headline result rows, scenario labels, node counts/id stubs. Budget ≤ 100 KB.
- **L1 (on expand, per node):** one node payload + adjacency stubs (id, type, direction, label). Budget ≤ 50 KB; cells are trivial.
- **L2 (on demand):** blobs — artifact bytes, document text, claim drill-down rows, full factor matrices (today's `/observations` is the precedent; it stays).

Routes: `GET /api/workspaces/{id}/graph` (L0), `GET /api/graph/{node_id}` (L1), `GET /api/graph/{node_id}/content` (L2). The F004 drill-down — click a result, see linked blocks — is L0→L1→L1 hops; the payload boundary keeps the "futuristic drill down" instant on synthetic-scale data.

### 5. Missing-evidence states

Typed enum on cells, result rows and controls — never nulls or flat warning strings:

| State | Meaning | Required metadata |
|---|---|---|
| `observed` | value present | — |
| `not-yet-observed` | development age beyond valuation (cell `future`) | valuation, grain |
| `unavailable-blocked` | required input missing; **blocks** dependent calc | reason_code, blocker node id |
| `excluded` | removed from fitting, retained in triangle (L003) | edge to `assumption/exclusion` with rationale |
| `outside-window` | present, not used (averaging window) | window param, governing config revision |
| `invalid` | failed validation (e.g. non-positive denominator) | control code |

Today's `reason` strings in result rows and the four statuses in `review.py:34-42` map one-to-one. F006 already fixes the semantics: unavailable curve evidence blocks discounting rather than inventing values — that becomes `unavailable-blocked` with a blocking edge.

### 6. The evidence boundary — three classes, three enforcement rules

Every node declares `class`:

1. **Calculation evidence** (`data/source`, `triangle/cell`, `assumption/exclusion`, `calc/*`, `control/*`): deterministic. *Enforcement:* created only by library/server code, carries `library_version` + input hashes; any recomputation must reproduce `content_sha256` or raise a control. Never authored or edited through the analyst.
2. **Human judgement** (`judgement/selection`): authored. *Enforcement:* requires `actor` + `role` + `created_at` + an explicit user-action id; the analyst tool registry cannot create it (tool allowlist rejection, testable at the `/tools` boundary); never auto-derived; a final selection requires a `judgement/selection` node and can never be produced by a model call. This is the durable form of "the analyst may never silently approve a final reserve."
3. **Model explanation** (`narrative/explanation`, `tool/invocation` content authored by the model): labelled. *Enforcement:* graph validator rejects any edge from a `narrative/*` node into a calculation-class node except `explains`/`cites` (outward); UI must render the class badge; explanations can never be an input edge to a result or selection.

### 7. Migration without breaking `tests/test_workspace.py`

Additive, three phases:

1. **Additive:** new `nodes`/`edges` tables beside `sessions/jobs/feedback` (`workspace.py:86-88`); `encode/decode_session` and `workspace_view` keys unchanged (`server.py:122-145`), so all five tests in `tests/test_workspace.py` — including `test_saved_scenario_report_and_export_keep_the_same_run` (line 30) asserting `scenario["analysis"] == baseline["analysis"]` — pass untouched.
2. **Backfill on first graph request:** blob → nodes: triangle → `data/source` + `triangle/cell`s; `evidence` list → `tool/invocation` nodes with `legacy_id: "T{n}"` (transcript `[T1]` text still resolves; `feedback.evidence_ids` still resolve via the legacy map); artifacts → `artifact/file` nodes gaining the missing provenance; baseline/scenarios → `calc/result` nodes with `based_on` edges.
3. **Native writes:** new runs write nodes directly; the blob remains a derived snapshot for the Streamlit path until a tested replacement exists (AGENTS.md boundary). Blob removal is a separate, later decision.

### 8. Acceptance criteria (testable)

1. Existing suite passes unchanged; a new workflow test expands one result cell and every edge resolves to a stored node within the three levels (F004).
2. Saved baseline payload is byte-identical after restart and a simulated `library_version` bump; a new run creates a `supersedes` node instead of mutating (extends `tests/test_workspace.py:30`).
3. Recomputed pure-function nodes (observations, factor matrices) match stored `content_sha256`.
4. Creating a `judgement/selection` via `/tools` returns 4xx; graph validator rejects a `narrative/*` → calculation edge.
5. An exported graph artifact contains no private-class payload bytes, no base64 claims (assert on the exported JSON).
6. Every missing-evidence presentation carries `{state, reason_code}`; the discounting case yields `unavailable-blocked`.
7. L0 ≤ 100 KB and L1 ≤ 50 KB on the largest example workspace.

### 9. Open questions for lead architect / founder

1. **Edge versioning:** immutable edges + `supersedes`, vs `valid_from/valid_to` ranges. *Recommend* the former — simpler, matches append-only.
2. **Author identity:** is a role string ("analyst") sufficient in single-user local mode, or do we want a local key-pair signature before public release? *Recommend* role string now; revisit at release gate.
3. **Factor granularity:** per-development-age nodes with `used_observation` edges (recommendation, matches `review.py` rows) vs per-cell-pair nodes only.
4. **One SQLite file** with new tables (recommended: one private artifact to back up) vs a second graph DB.
5. **Flat `warnings` list in `AnalysisResult`:** keep for compatibility and add typed `control/check` nodes in parallel (recommended), removing only at a v2 schema break.
6. **Founder:** should the drill-down default to per-origin result rows (recommended) or headline totals as the first expandable block?

**Recommendation:** accept the three-class boundary, typed missing-evidence states, L0/L1/L2 lazy loading, and the additive migration as the contract core; resolve §9 before implementation sizing.

---

## 2. DRAFT — #6 Reserving cash-flow projection

**DRAFT — FOR LEAD-ARCHITECT REVIEW, NOT AN ACCEPTED DECISION**

Grounded in `src/actuarial_library/reserving.py`, `data.py`, `models.py`, `review.py`; no runtime/private data was read.

### Scope and placement

New deterministic module `src/actuarial_library/projection.py`: `project_payments(triangle, result, config) -> ProjectionResult` consuming an existing `AnalysisResult` (models.py:141). No I/O, no RNG; values clock-independent. `ProjectionConfig` added to `models.py`. Surfaced as a web panel + export; `dist/` untouched (person-level income-minus-cost model, unrelated).

**Grain note:** 30 June 2026 is a valid valuation only for quarterly grain (data.py:197 requires year-end for "Y"), so the reference case *is* the quarterly path. Annual acceptance case: 31 Dec 2025.

### P1 — Pattern and allocation formula

The paid CDFs from `development()` (reserving.py:61-68; `cdf[n-1] = tail ≥ 1`) define cumulative paid proportions, 1-based age `a`:

- `p_a = 1 / cdf_a` (share of ultimate paid by end of age `a`), `p_∞ = 1`
- future step increments `d_m = p_m − p_{m−1}` for `m = a+1 … n`, and `d_tail = 1 − p_n`
- per origin `i` with valuation age `a_i = n − i` (models.py:121-125: latest = valuation diagonal, never an earlier cell): remaining share `R_i = 1 − p_{a_i}`
- **renormalized weight** `w_{i,m} = d_m / R_i` (sums to 1 over the origin's steps)
- **payment** `= outstanding_i × w_{i,m}`, where `outstanding_i` is the *selected* row's outstanding (reserving.py:211), regardless of method.

Renormalization to the selected outstanding is mandatory — it makes BF/incurred/FS/manual selections schedule correctly and guarantees reconciliation. For paid CL the identity `outstanding_i / R_i = ultimate_i` holds exactly, so payments ≡ ultimate×d_m, the classic CL allocation; the outstanding base is the spec because it generalizes.

**Rounding:** float64 throughout, no intermediate rounding; exports display cents; €0.01 tolerance (F006) applies to unrounded sums.

**Guards (per origin, reasons carried, never invented values):** `cdf_{a_i}` is None → blocked ("paid pattern unavailable at valuation age"). `|R_i| < 1e-6` with `|outstanding_i| > €0.005` → blocked ("pattern fully developed at latest age; supply a tail or external pattern"). `R_i < 0` (cdf < 1) → allowed, warning, mixed-sign schedule diagnosed. Selected-but-unavailable methods cannot occur downstream (reserving.py:207-208 raises), so "partial" means only *missing* selections (P6).

### P2 — Calendar mapping

Payment at step `m` (increment between ages `m−1` and `m`) lands in calendar period index `o_i + m − 1`, where `o_i` is the origin's period index (data.py:31-32); label via `label()` (data.py:35-36), payment date via `period_end()` (data.py:39-41). This matches cell `[i, j]` being observed at `o_i + j` (data.py:243, models.py:136).

### P3 — Tail timing

- **Default:** the tail increment `d_tail` lands wholly in the single period `o_i + n`. Deterministic, transparent, no invented decay.
- **Explicit external timing:** optional fractions over future periods (sum 1, source + rationale required) spreading `d_tail`; validated sum-to-1 within 1e-9.
- **Not blocked** when unspecified — the default applies and every row carries `tail_timing = "default_next_period" | "external:<name>"`. Tail = 1 produces no tail step.

### P4 — Negative implied payments

Arise when (a) some `d_m < 0` because a selected factor < 1, or (b) the selected outstanding itself is negative. Both retained, never floored, never removed. Each affected row carries `diagnosis = "negative implied payment: paid factor below one at age m"` / `"negative outstanding base retained"`. Calendar-period aggregates are net sums with a warning whenever any component is negative; per-origin detail always stays visible.

### P5 — Quarterly gate (hard rule)

- Output grain = triangle grain. An annual triangle **never** produces quarterly rows; requesting them is a hard error. No 1/4 splitting, ever.
- Quarterly flows require `triangle.grain == "Q"` (observations through the reporting quarter) **or** an explicit external quarterly pattern with source + rationale, renormalized identically.
- External quarterly pattern on annual origins needs an alignment convention: recommend annual origin year `Y` ↔ quarter index `YQ4`, first payment quarter `(Y+1)Q1`. Open question 2.
- Quarterly → annual roll-up is pure aggregation (allowed, offered as display/export); detail retained.

### P6 — Reconciliation and partial selections

- Per origin: Σ undiscounted payments = selected outstanding, |diff| ≤ €0.01 → status `ok`; otherwise `error` (should be impossible by construction; the test pins it).
- Portfolio total equals Σ origin outstanding **only when every origin has a selection**. Missing selections do not block: the schedule is produced for selected origins and the output carries `selection_complete = false` plus the excluded origins with reasons. Exports must be unmistakably partial. Recommendation: annotate, don't block; a hard block remains an option for exports specifically (open question 3).
- Calendar totals cross-check: Σ over calendar periods = Σ over origins.

### P7 — Discounting boundary (ticket #7)

The undiscounted schedule is the primary output of #6 and is always produced. Discounting is a separate adapter consuming schedule rows (period-end dates): default 30 June 2026 basic EUR EIOPA curve without VA; with-VA only as an explicit option recording exact source (publication, retrieval timestamp/hash). Missing curve evidence blocks the discounted view with an F006 warning — never interpolated — while the undiscounted schedule stands. Both columns shown when evidence exists. In-period timing convention (end vs mid-period) belongs to #7 (open question 4).

### P8 — Evidence traceability (node names provisional, pending #4)

Every payment row carries: origin; selected method + note; outstanding; valuation age and source cell; `pattern_source = "triangle" | "external:<name>"`; the factor rows used (`pairs`, `origins_used`, `override`, `rationale`, reserving.py:48-60); tail value + timing source; `w`, `d`; calendar label + period end; diagnosis. Provisional nodes: `payment_projection_run`, `payment_schedule[origin]`, `external_pattern`, `tail_timing`, `reconciliation`, linking to the existing run/selection/factor evidence.

### Worked example (annual 3×3, valuation 2025-12-31; exact arithmetic)

Paid triangle: 2023: 100, 200, 240 · 2024: 120, 240, — · 2025: 150, —, —.
Volume-weighted: f₁ = 440/220 = **2.0**; f₂ = 240/200 = **1.2**; tail = **1.25**.
CDFs: age1 **3.0**, age2 **1.5**, age3 **1.25** → p = 1/3, 2/3, 4/5, 1 → d = **1/3, 2/15, 1/5**.

| origin | a | paid | ultimate | outstanding | R = 1−p_a | weights | payments (period) |
|---|---|---|---|---|---|---|---|
| 2023 | 3 | 240 | 300 | 60 | 1/5 | tail: 1 | **60** (2026) |
| 2024 | 2 | 240 | 360 | 120 | 1/3 | m=3: 2/5; tail: 3/5 | **48** (2026), **72** (2027) |
| 2025 | 1 | 150 | 450 | 300 | 2/3 | m=2: 1/2; m=3: 1/5; tail: 3/10 | **150** (2026), **60** (2027), **90** (2028) |

Calendar: 2026 = 60+48+150 = **258**; 2027 = 72+60 = **132**; 2028 = **90**; total **480** = Σ outstanding (60+120+300) ✓.

**BF base:** if 2024 selects paid_bf, ultimate 340 → outstanding 100 → **40** (2026), **60** (2027): paid shape, selected base. ✓

**Negative:** override f₂ = 0.95 (tail 1.25): CDF₂ = 19/16, p₂ = 16/19, d₃ = 4/5 − 16/19 = **−4/95** < 0. 2024: ultimate 240×19/16 = 285, outstanding 45, R = 3/19; weights −4/15 and 19/15 → payments **−12.00** (2026, labelled negative implied payment) and **+57.00** (2027); Σ = 45 ✓. Retained, unfloored.

### Tests to pin (new `tests/test_projection.py`)

1. `test_projection_reconciles_to_selected_outstanding`
2. `test_projection_paid_cl_identity_with_ultimate_increment`
3. `test_projection_calendar_mapping_and_tail_default` — pins 258/132/90 and tail-in-2026 for 2023
4. `test_projection_bf_uses_selected_outstanding_base` — 40/60 case
5. `test_projection_negative_implied_payments_retained_and_labelled` — −12/57 case
6. `test_projection_negative_outstanding_projects_negative_schedule`
7. `test_projection_blocked_when_pattern_closed_but_outstanding_nonzero`
8. `test_projection_quarterly_gate_rejects_invented_quarterly_split`
9. `test_projection_quarterly_triangle_maps_quarter_labels`
10. `test_projection_external_pattern_requires_source_and_rationale`
11. `test_projection_partial_selection_annotates_missing_origins`
12. `test_projection_export_roundtrip` — actual download verified
13. `test_projection_evidence_columns_present`

### Acceptance criteria

1. All tests pass: `PYTHONPATH=src .venv/bin/python -m pytest -q`; `ruff check` clean on new files; `node --input-type=module --check < web/app.js` unchanged.
2. Worked example reproduces exactly (258/132/90).
3. Per-origin reconciliation ≤ €0.01 on every test triangle; portfolio total only when `selection_complete`.
4. No origin appears in the schedule without complete pattern + selection evidence, except as an annotated exclusion with a reason.
5. Annual data never yields quarterly rows; quarterly flows only via Q-grain observations or an explicit external pattern.
6. Negative payments/outstandings present, labelled, unfloored.
7. Export contains the payment schedule as a real, verified downloaded file; `dist/` untouched.
8. Undiscounted schedule always produced; discounted view only with verified curve evidence (F006), both shown; default = 30 June 2026 basic EUR no-VA.
9. Every row traceable to factors, exclusions, selection and source cells; UI shows provenance.

### Open questions (recommendation in brackets)

1. **Tail default:** single next period [recommended: yes, labelled; external multi-period optional; not blocked].
2. **Origin alignment for external quarterly patterns on annual triangles** [recommended: Y ↔ YQ4; needs lead-architect sign-off].
3. **Partial selections:** annotate vs block [recommended: annotate + explicit incomplete flag on exports; founder may prefer a confirmation step before exporting a partial schedule].
4. **In-period payment timing for discounting** (end vs mid-quarter/year) → #7 [no recommendation; schedule supplies period ends].
5. **Reference-case grain:** 30 June 2026 forces quarterly grain (data.py:197). Confirm the founder intends the quarterly path as the acceptance reference, with 31 Dec 2025 annual as secondary [recommended: yes].
6. **Netting in the default calendar chart:** net totals with negative-component warnings, per-origin table primary [recommended: yes].
7. **External pattern versioning:** pin source hash + retrieval timestamp like curves [recommended: yes].

---

## 3. DRAFT — #8 Unisex regular and partner annuity factors

**DRAFT — FOR LEAD-ARCHITECT REVIEW, NOT AN ACCEPTED DECISION**

Inputs: `docs/project/FEEDBACK.md` (F007), `docs/research-ag-mortality.md`, `src/actuarial_library/models.py`, `tests/test_reserving.py`. AG tables are not embedded; all example numbers are synthetic.

### 1. Scope and placement

New deterministic module `src/actuarial_library/annuity.py`; typed request/result models co-located there following `StrictModel` (`model_config = ConfigDict(extra="forbid", allow_inf_nan=False)`, see `src/actuarial_library/models.py:12`). Mortality table loading (AG workbooks → qx grid + SHA-256 provenance) is a separate loader in the same module. Tests: `tests/test_annuity.py`, style of `tests/test_reserving.py`.

### 2. Definitions (binding decisions restated)

- **Regular factor**: payments while the participant is alive.
- **Partner factor** (reversionary): payments to a known partner, starting after participant death, while the partner lives. Payment at time t requires *partner alive at t* AND *participant dead at t*.
- **Unisex**: source mortality stays sex-specific; unisex factors are mixed explicitly, weights adjustable, default 50/50, recorded in provenance.
- **Basis**: AG2024 is the as-known-at-30-June-2026 table; AG2026 only as a labelled retrospective scenario.

### 3. Decision points and recommendations

**D1 — Unisex mixing: recommend (a) factor-space mixing.**
ä_unisex = w_m·ä_male + w_f·ä_female, w_m + w_f = 1 (validated). Rationale: each branch is computed exactly from published tables — no derived table enters provenance; it equals the *expected factor* if weights are true portfolio sex proportions; it is the conventional pension unisex approach; it is linear, so it composes cleanly with per-life weighting for partner factors. Rejecting (b) (constructed unisex qx): cohort survival from averaged qx is an arithmetic mix of probabilities, not the average of the two cohort survivals (geometric), creating a derived table that no published source reproduces and complicating audit.

**D2 — Partner factor: independence, explicit per-life weighting.**
Both lives assumed initially alive; deaths independent: P(partner alive, participant dead at t) = S_p(t)·[1 − S_a(t)] (consequence of the independence assumption, not supplied by AG — `docs/research-ag-mortality.md:50`). Sex handling: each life uses its own sex category from the sex-specific table; if a life's sex is unknown/unspecified, its factor is unisex-mixed with that life's weights, i.e. the combination factor is averaged over the 2×2 (or 2×1) sex grid with product weights w_a(s_a)·w_p(s_p) — well-defined under (a). Known-sex combinations are computed directly.

**D3 — Ages and date basis.**
Reference date default 30 June 2026 (parameter). Exact ages derived from date of birth. **Cohort** mortality: attained age and calendar year advance together (`docs/research-ag-mortality.md:35`). Cell key = age last birthday at 1 January of the calendar year (AG formal reference life ages on 1 January). Constant force within each (age, year) cell: survival over fraction u is (1−q)^u; the cohort walk splits at 1 January boundaries. Worked examples use a 1 January anchor; the same rule handles the production mid-year anchor with half-cell exponents.

**D4 — Frequency and timing.** Annual (m=1) and monthly (m=12); payment times t_k = k/m from the reference date. **Primo**: paid at period start, contingent on survival to the payment date, k = 0, 1, … **Ultimo**: paid at period end, k = 1, 2, … Monthly timing needs no separate approximation: constant force gives S(k/12) = (1−q)^{k/12} within a cell.

**D5 — Terminal age: recommend (a) close at 120.**
The last cell is (120, Y*); S(t) = 0 once the cohort completes the age-120 cell; no payments beyond. Rationale: never invents mortality outside the published 0–120 domain (age-120 qx < 1, so this is a real choice — `docs/research-ag-mortality.md:31`); the omitted value is demonstrably immaterial (discount factor ~v^56 × survival-to-121 for a 65-year-old); simple to test. Honest note: this marginally *understates* the factor — not conservative for a liability; alternative (b) extends with the last qx and adds unverifiable tail value. Recorded as `terminal_age_rule = "close_at_age_120"`.

**D6 — Indexation.** Constant annual rate g: payment at t_k = (1+g)^{t_k} (monthly: (1+g)^{k/12}). Validation: −5% ≤ g ≤ 10%; outside a documented rationale band is rejected. Discounting enters only via the **discount basis parameter** (ticket #7): default 30 June 2026 basic EUR EIOPA without VA; unavailable curve evidence → hard error, no factor produced, values never invented.

**D7 — Provenance.** Every result carries: table edition, publication date, source SHA-256, reference date, DOB-derived exact ages, frequency, timing, per-life unisex weights, terminal-age rule, indexation g, discount-curve identity (ticket #7 fields), plus a full intermediate trace (§5). Evidence Graph node names provisional pending #4.

### 4. Formulas

- Survival: S(t₀+t) = Π over crossed cells of (1 − q_{x_i, Y_i})^{u_i}, Σu_i = t.
- Regular, m payments/year, timing τ (τ=0 primo, τ=1 ultimo), horizon K periods: **ä = Σ_{k=τ}^{K} v(t_k)·(1+g)^{t_k}·S(t_k)**, t_k = k/m.
- Partner (reversionary) on the same grid: **ä_rev = Σ_{k=τ}^{K} v(t_k)·(1+g)^{t_k}·S_p(t_k)·[1 − S_a(t_k)]**.
- Unisex per life: ä_unisex = w·ä_male + (1−w)·ä_female (D1/D2).

### 5. Worked micro-examples (synthetic; NOT AG)

Common: t₀ = 1 Jan 2027, participant exact age 65, i = 2% flat (synthetic), g = 0, 3 terms (truncated for illustration; production runs to closure). Synthetic qx: male 65–67: 0.0100, 0.0120, 0.0140; female: 0.0080, 0.0096, 0.0112. v(k) = 1.02^−k.

**A. Regular annual ultimo (unisex 50/50).**

| k | S_male | term_male = v^k·S | S_female | term_female |
|---|---|---|---|---|
| 1 | 0.990000 | 0.970588 | 0.992000 | 0.972549 |
| 2 | 0.978120 | 0.940138 | 0.982477 | 0.944326 |
| 3 | 0.964426 | 0.908800 | 0.971473 | 0.915441 |
| Σ | | **2.819527** | | **2.832316** |

ä_unisex = 0.5·2.819527 + 0.5·2.832316 = **2.825921**.

**B. Regular monthly primo (unisex 50/50), 12 payments within cell (65, 2027).**
term_k = v^{k/12}·S(k/12). Male: term₀ = 1.000000 … term₁₁ = 0.973006; Σ = **11.837363**. Female: Σ = **11.848261**. ä_unisex = **11.842812** (monthly amount; annual-equivalent ÷12).

**C. Partner annual ultimo.** Participant male, exact age 68 (synthetic q 68–70: 0.0160, 0.0180, 0.0200 → S = 0.984000, 0.966288, 0.946962); partner female, age 65 (S from A). Known sexes → direct, no mixing.

| k | S_p·[1−S_a] | term = v^k·… |
|---|---|---|
| 1 | 0.992000×0.016000 = 0.015872 | 0.015561 |
| 2 | 0.982477×0.033712 = 0.033121 | 0.031835 |
| 3 | 0.971473×0.053038 = 0.051523 | 0.048553 |

ä_rev = **0.095949**. Cross-check identity: partner-single ultimo − joint ultimo = 0.095949 ✓.

### 6. Tests to pin (`tests/test_annuity.py`)

1. Micro-example A/B/C values reproduced exactly from the synthetic table.
2. Unisex mixing: weighted average; w_m + w_f ≠ 1 → validation error; weights in provenance; factor between sex extremes, monotone in w.
3. Timing identity: ä_primo − ä_ultimo = 1 − v(t_N)S(t_N) (verified: 0.029412 = 1 − 0.970588).
4. Ordering: monthly-primo ≥ annual-primo ≥ annual-ultimo ≥ monthly-ultimo.
5. Reversionary identity: ä_rev = ä_partner-single − ä_joint (holds under independence; verified above).
6. Degenerate cases: participant q=0 → ä_rev = 0; partner q=0 → ä_rev = Σv^k(1−S_a(k)).
7. Terminal age: payments cease after the age-120 cell; `terminal_age_rule` present; factor finite.
8. Constant force: Π of 12 monthly factors in one cell = (1−q); cohort ≠ period when qx varies by year; equal when flat.
9. Mid-year anchor: reference 30 June with DOB mid-year gives half-cell exponents (spot-check vs hand value).
10. AG2026 requires a labelled scenario flag; default is AG2024; edition + hash in provenance.
11. Missing discount-curve evidence → error, no factor, no fallback.
12. Indexation: g=0 equals base; g>0 factor ≥ base; out-of-band g without rationale rejected.
13. StrictModel: unknown request fields rejected (extra=forbid).

### 7. Acceptance criteria

F007 acceptance fully met when: calculator exposes mortality-table version, reference date/age basis, frequency, primo/ultimo, unisex weights; definitions and mixing rules are explicit (D1–D6); all tests pass; a one-case formula workbook (contents specified here, creation is a later task) independently reproduces the selected example; every result retains source/version metadata and the exact per-payment survival, discount, payment and term values.

### 8. Open questions — lead architect / founder (with recommendations)

1. **Founder — unisex mixing rule**: factor-space (recommended, D1) vs constructed unisex table.
2. **Founder — terminal age**: close at 120 (recommended, D5) vs extend with last qx.
3. **Founder — partner-sex weighting**: per-life weighting with known-sex direct lookup (recommended, D2) vs always mixing both lives. Also: should the UI default partner age difference to a stated assumption (AG's example uses a 3-year difference — illustrative, not inherent)?
4. **Lead architect — discount basis parameter**: confirm the 30 June 2026 basic EUR EIOPA-without-VA default and blocking behaviour once ticket #7 lands; the factor API must take the curve as a dependency, not assume flat rates (examples above use a synthetic 2% for arithmetic only).
5. **Lead architect — Evidence Graph node naming** for the per-payment trace (provisional pending #4/F004).
6. **Lead architect — cohort cell key**: age last birthday at 1 January (recommended, D3) vs birthday-driven cell crossing.

**Recommendation:** adopt D1(a), D2 per-life weighting, D3 cohort/1-January key, D5 close-at-120; implement `src/actuarial_library/annuity.py` against the golden values above once the lead architect confirms and the founder has seen decisions 1–3.

---

## 4. DRAFT — #9 AG mortality ingestion and rights boundary

**DRAFT — FOR LEAD-ARCHITECT REVIEW, NOT AN ACCEPTED DECISION**

Grounded in `docs/research-ag-mortality.md` (verified observations only), `docs/project/HANDOVER.md`, `docs/project/FEEDBACK.md` F007, `docs/project/DECISIONS.md`, `THIRD_PARTY.md`. No private/runtime data was read.

### Binding decisions this spec must implement

AG2024 is the as-known-at-30-June-2026 mortality basis; AG2026 is available only as an explicitly labelled retrospective scenario for that reporting date. Single-user, local-first, no telemetry, no silent cloud fallback. The Wayfinder out-of-scope note prohibits silent redistribution of AG workbooks.

### 1. Ingestion model

- **User-supplied workbook files only.** The user uploads the parameters/best-estimate XLSX they downloaded from the official AG page themselves, via a workspace upload path served by `server.py`. The repo, releases, `examples/`, `data/`, docs and test fixtures never contain AG tables, derived qx grids, or workbook copies.
- **Recommendation: defer an official-source fetch feature beyond v1.** A built-in fetch adds a network egress path, a redistribution-adjacent caching question, and URL-drift maintenance, for marginal convenience. v1 documents the official page URL so the user can fetch the file themselves under their own access.
- Ingestion happens in a new deterministic module (proposed `src/actuarial_library/mortality.py`), following the adapter pattern used for reserving in `src/actuarial_library/data.py`; the UI calls the same functions, per D001.

### 2. Validation rules (all machine-checked)

Pipeline: `ingest_workbook(path, confirmed_edition)` → imported tables + validation report, or a blocking failure.

1. **Edition confirmation is explicit.** The user selects AG2024 or AG2026; the importer never infers edition silently. Sheet names must match the confirmed edition: `Voorblad`, edition-specific `Parameterwaarden`, `qx mannen 2024`/`qx vrouwen 2024` (AG2024) or `qx mannen 2026`/`qx vrouwen 2026` (AG2026). Sheet-name suffix inconsistent with the confirmed edition → blocking error.
2. **Age axis:** column A of each qx sheet contains integers 0–120, contiguous, ascending, starting row 2. Missing/duplicate/out-of-range ages → blocking error.
3. **Year axis:** calendar years read from row 1 of the actual file, never assumed from the edition name (AG2026's delivered grid starts 2024 although its PDF says 2022 onward). Years must be integers, ascending, contiguous. First/last year recorded as imported range facts, not hardcoded.
4. **Grid shape:** one numeric qx per (age, year) cell for each sex sheet; used ranges extending to row 126 (non-data cells) must be ignored, not imported.
5. **qx bounds:** every imported qx ∈ (0, 1]; blank treated as "not supplied" and blocks lookups in that cell — never silently zero. The inspected male age-120 qx < 1 is a recorded fact, not an error.
6. **Sex mapping:** `mannen` → male, `vrouwen` → female, exactly two categories; no unisex table is created at ingestion (unisex mixing belongs to #8).
7. Validation outcome (pass/block + rule identifiers) is persisted with a timestamp before any calculation may reference the table.

### 3. Identity and provenance

Each ingested table is stored in the local `WorkspaceStore` (`src/actuarial_library/workspace.py`; the user's `local_runs/workspace.sqlite3`), never in the repo. Retained fields per import: edition label (user-confirmed), publication date (AG2024 2024-09-12; AG2026 2026-09-08), source URL, retrieval date, SHA-256 content hash, byte size, sheets imported, imported age range, imported year range, sex categories, table form (annual best-estimate qx; constant force within cell), basis role (as-known or retrospective-scenario), reporting date in scope, validation outcome + timestamp. Mirrors the EIOPA pattern in `docs/research-eiopa-rfr-2026q2.md`.

- **Hash policy:** the known hashes (`e118…fb6e` 706,033 B; `8880…37fd` 648,972 B) identify inspected files, not immutable URLs; no patch scheme exists. A byte-size/SHA mismatch against the recorded reference is a **warning, not a block**: import proceeds, stored and displayed as "hash differs from inspected reference (variant unverified)". Exact-match imports are labelled "matches inspected reference". Hash is never the identity key alone (see §7).

### 4. Rights boundary

- No redistribution of AG tables, workbooks, derived qx grids or calibration datasets in the public repo, releases, docs, examples, screenshots or test fixtures. Docs (`docs/`, `THIRD_PARTY.md`) may describe workbook structure and cite the official source; they must not reproduce table content.
- The user's stored local copy is the user's own copy under their own permission: local caching solely to run calculations is the recommended reading of the disclaimer, **pending founder/legal confirmation** (Open Question a). The workbench must never publish, transmit, or export it: ingestion artifacts stay in the workspace store; AG grids are excluded from any export bundle by default.
- Calibration-dataset XLSXs: not ingested in v1; third-party rights unverified, out of scope entirely.
- Requires founder/legal verification before any public release: (a) user-local storage acceptability; (b) whether docs may show illustrative real-qx snippets (recommendation: **synthetic only**); (c) derived-factor examples in docs — synthetic only; (d) whether the repo may retain the two reference hashes + byte sizes (recommendation: yes — factual identifiers, not content).

### 5. As-known vs retrospective behaviour

- For reporting date 2026-06-30, **AG2024 is the default and only as-known basis**. AG2026 (published 2026-09-08, after the reporting date) is selectable only as an explicitly labelled retrospective scenario: UI labels it e.g. "Retrospective scenario — published after reporting date".
- The UI/API **never lists AG2026 among bases available at the reporting date**; absence of AG2026 at 30 June is a fact to display, not a gap to paper over.
- Every annuity/factor result and export carries **basis role + scenario label + edition + provenance id** (F007). A retrospective-scenario result is visually distinct from the as-known baseline; per L003, a scenario is an assumption change on the same valuation, never silently the default.

### 6. Terminal-age handoff with #8

Ingestion **records** `qx(120) < 1` as a data fact in provenance and exposes it to callers; it **must not** silently close the table. The treatment decision is owned by #8. The ingestion API contract states: `max_age_supplied=120`, `qx_at_max_age < 1`, `treatment: DECIDED_ELSEWHERE (#8)`. #8 must resolve it before whole-life factors are usable.

### 7. Version drift

An ingested table is keyed on **content hash + user-confirmed edition + import timestamp**, not filename or silent sheet-name matching. Two imports with the same edition label but different hashes are distinct stored entries; the newer one never overwrites the older silently. New AG editions (AG2028…) require explicit re-ingestion; existing keys never remap.

### 8. Tests to pin (new `tests/test_mortality_ingestion.py`; fixtures synthetic, generated in-test)

- **Synthetic-only guard:** fixtures are small generated XLSXs; a hygiene test asserts no fixture path/hash equals the known AG reference hashes/byte sizes.
- Happy path: synthetic AG2024-shaped workbook imports; provenance fields persisted and retrievable after a store reopen (L002).
- AG2026-shaped workbook: year headers read from file — imported range equals file headers, not edition defaults.
- Blocking failures: wrong sheet names; sheet suffix vs confirmed edition mismatch; ages not 0–120; non-contiguous years; qx ≤ 0, ≥ 1, or blank in an expected cell; non-data cells at rows 123–126 ignored.
- Hash mismatch: same edition, different bytes → warning + "unverified variant" label, import succeeds; exact hash → "matches inspected reference".
- Retrospective gate: API never returns AG2026 as an as-known basis for 2026-06-30; a factor result from it carries the retrospective scenario label in payload and export.
- Terminal age: `qx(120)<1` recorded and surfaced; ingestion applies no closure.
- Drift: two imports, same edition, different hash → two entries; old ids stable.

### Acceptance criteria

1. A user can supply both official workbooks and obtain validated, provenance-complete local tables; no AG content exists in repo/release/fixtures.
2. All validation rules are machine-enforced and test-pinned; failures block with named rule ids.
3. AG2024 is the only as-known basis at 2026-06-30; AG2026 runs only as a labelled retrospective scenario; every result/export carries basis role + scenario label + edition + provenance id.
4. `PYTHONPATH=src .venv/bin/python -m pytest -q` passes; ingestion tested at the API boundary per `tests/test_workspace.py` conventions.

### Open questions (lead architect + founder)

- **(a) User-local caching under the AG disclaimer** (reproduction/storage reserved without written permission). *Recommendation: acceptable for the user's own local calculation use — the user already lawfully downloaded the file; the workbench adds no redistribution. Founder confirms; if not, ingestion becomes in-memory-only per session.*
- **(b) Docs examples: illustrative real-qx snippets or strictly synthetic?** *Recommendation: strictly synthetic; avoids creating a derived-dataset publication in the repo.*
- **(c) User-triggered official-source fetch in v1?** *Recommendation: defer; revisit after (a) is confirmed and a release need exists.*
- Lead architect: confirm the `qx(120)<1` handoff contract with #8, and whether reference hashes/byte sizes may appear in public docs.

---

## 5. First-commit inventory proposal (input to the pending inventory decision)

All verification complete; nothing was modified. Analysis only.

**Tracked at e62a1e9 (5 files):** `.openai/hosting.json`, `dist/app.js`, `dist/index.html`, `dist/style.css`, `dist/worker.js` (cash-flow prototype). No tracked file is modified — the working tree is clean except untracked paths. **72 untracked non-ignored entries** (= 63 proposed + 9 review); everything else on disk is already ignored.

**A) PROPOSE (63 files)**
- Root (13): `AGENTS.md`, `CLAUDE.md`, `CONTEXT.md` (glossary), `CONTRIBUTING.md`, `GEMINI.md`, `LICENSE`, `README.md`, `THIRD_PARTY.md`, `app.py`, `server.py`, `constraints.txt`, `pyproject.toml`, `.gitignore`
- Config/CI (2): `.github/workflows/tests.yml`, `.streamlit/config.toml` (224 B, no secret patterns)
- `src/actuarial_library/` (12 .py): core deterministic library
- `tests/` (7): `test_agent.py`, `test_app.py`, `test_data.py`, `test_exploration.py`, `test_local_inference.py`, `test_reserving.py`, `test_workspace.py`
- `scripts/` (6): `benchmark.py`, `check_local_agent.py`, `evaluate_local_agent.py`, `prepare_workbook.py`, `project_memory.py`, `run_workspace.py`
- `web/` (3): `app.js`, `index.html`, `styles.css`
- `skills/actuarial-platform/` (3): `SKILL.md`, `references/domain-contract.md`, `references/delivery-and-architecture.md`
- `docs/` (15): methodology, api, data_dictionary, research, verification, agents/, etc.
- Other: `examples/analyse_demo.py` (741 B), `artifacts/workbook-authoring/build_workbook.mjs` (handwritten build script; .gitignore deliberately keeps this folder)

**B) EXCLUDE — already covered by `.gitignore`:** `.venv/` (31,148 files), `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `node_modules/`, `build/`, `artifacts/previews/`, `artifacts/workbook_payload.json`, `artifacts/workbook_checks.json`, `local_runs/` (runtime SQLite), `data/private/` and `data/test_truth/` (not on disk today — defensive entries), `.DS_Store`. **Two escapes found:** `artifacts/workbook-authoring/node_modules` (symlink) and `.scratch/` (not ignored).

**C) REVIEW NEEDED (9 + 1 tracked):**
- `data/demo/claims.parquet` (453 KB), `data/demo/coverage.csv`, `data/demo/invalid_claims.csv` — claims-shaped fixtures referenced by `src/actuarial_library/demo.py` and README; docs describe demo data as synthetic; **verify no real claimant/policy identifiers before publish** (contents not opened).
- `examples/reserving_worked_example.xlsx` — 3.3 MB binary, largest file; if regenerable via `scripts/prepare_workbook.py`/`build_workbook.mjs`, exclude and document regeneration instead.
- `docs/benchmark.json` (753 B) — generated by `scripts/benchmark.py`; commit as recorded evidence or exclude as generated output.
- `docs/project/DECISIONS.md`, `FEEDBACK.md`, `HANDOVER.md`, `LESSONS.md` — internal process docs incl. founder quotes; non-private by rule, but decide whether internal workflow belongs in a public repo.
- `.openai/hosting.json` — already tracked/in history; 91 B, 0 secret-pattern matches; human-confirm it is benign since history keeps it even if removed.

**Recommended `.gitignore` additions (before first commit):**
1. `node_modules` (no trailing slash) — current `node_modules/` matches directories only, so it misses the symlink.
2. `.scratch/` — agent scratch dir, unignored.
3. Pending C-decisions: `examples/*.xlsx` if the workbook is regenerable; `docs/benchmark.json` if treated as generated.
4. Defense-in-depth (optional): `.env`, `.env.*`, `*.sqlite3`.

**Top 5 risks before first commit:**
1. `artifacts/workbook-authoring/node_modules` symlink was untracked and NOT ignored (`git check-ignore` RC=1); it points to a machine-specific runtime cache — a blanket `git add .` would commit a nonportable symlink. This ignore defect was subsequently corrected; see the lead verdict.
2. `.gitignore` itself is untracked — none of these protections exist in a clone until `.gitignore` is in the first commit (commit it first, with additions).
3. `data/demo/` claims fixtures — must be confirmed fully synthetic; `data/private/` doesn't exist on disk, so the private-data boundary currently holds only by convention.
4. Large binaries — `examples/reserving_worked_example.xlsx` (3.3 MB) bloats the repo permanently once pushed; decide regenerable-vs-curated.
5. Internal docs and existing history — `docs/project/` (founder feedback) and already-tracked `.openai/hosting.json` need a human sensitivity check; secret-pattern scans were clean and no `/Users/` paths appear in proposed text files.

---

## 6. Grounding scans (summaries)

Three further read-only scans grounded the drafts; their key facts are embedded in the respective draft texts above and are verifiable against the cited file paths:

- **Evidence inventory** (→ draft #4): no node/edge model exists; evidence is blob fields and DataFrame rows; only persisted cross-references are `workspace_id` and `feedback.evidence_ids`; whole-payload overwrites; only `/observations` is a targeted fetch; human judgement is Streamlit-only and unpersisted; narrative is untyped free text.
- **Cash-flow semantics** (→ draft #6): no projection code exists in `src/`; paid pattern/CDF semantics live in `reserving.py`; `dist/` is an unrelated person-level income-minus-cost model; tail timing, calendar mapping, negative payments, reconciliation and the quarterly gate are all currently unimplemented.
- **AG ingestion facts** (→ draft #9): table dimensions, sheet names, hashes, rights constraints and as-known/retrospective distinction as recorded in `docs/research-ag-mortality.md`.

---

## 7. Reviewer checklist for Codex (lead architect)

- [ ] Verdict per draft: accept / accept-with-revisions / reject, with reasons tied to actuarial semantics, architecture, security, integration.
- [ ] Draft #4 §9 open questions 1–6 (edge versioning, author identity, factor granularity, one SQLite file, warnings compatibility, drill-down default).
- [ ] Draft #6 open questions 1–7 (tail default, origin alignment for external quarterly patterns, partial selections, discounting timing → #7, quarterly reference case, netting, external pattern versioning).
- [ ] Draft #8 open questions 1–6 (unisex mixing, terminal age, partner-sex weighting for the founder; discount basis parameter, Evidence Graph naming, cohort cell key for the architect).
- [ ] Draft #9 open questions a–c (local caching under the AG disclaimer, synthetic-only docs, official-source fetch deferral) and the `qx(120)<1` handoff with #8.
- [ ] First-commit inventory: sign off sections A/B/C, the `.gitignore` additions (especially the node_modules symlink escape), and the review-needed items.
- [ ] Confirm whether wave 2 (#7 EIOPA conventions draft, #5 evidence drill-down prototype) may start before these reviews are fully resolved, or strictly after.

## 8. Open questions for the founder

1. **Slack notifications:** you asked to be pinged on Slack. No Slack integration exists in the agent toolset (no CLI, no MCP server), and agents must not touch credentials. Options: (a) connect a Slack MCP server to OpenCode/Herdr, (b) provide an approved webhook mechanism through Herdr config, (c) keep updates in the Herdr pane + `docs/project/` artifacts as today. Which do you prefer? Tracked as FEEDBACK F009.
2. **GitHub posting:** may reviewed drafts/decisions be posted as GitHub issue comments (the durable issue tracker), or should all state stay in repo files until you approve publication?
3. **#8 actuarial conventions:** unisex mixing (factor-space recommended), terminal age (close-at-120 recommended), partner-sex weighting (per-life recommended) — decide directly, or accept the drafting agents' recommendations after codex review?
4. **Reference-case grain:** a 30 June 2026 reporting date forces quarterly grain for the reserving reference case (annual triangles require year-end valuations). Confirm the quarterly path is the acceptance reference.
5. **Partial-selection exports:** when some origins lack a selection, should the projection export be produced with an explicit incomplete flag (recommended) or blocked pending a confirmation step?

## 9. Verification commands

```bash
git status --short
git remote -v
PYTHONPATH=src .venv/bin/python -m pytest -q
node --input-type=module --check < web/app.js
.venv/bin/python scripts/run_workspace.py   # then check /api/health
```
