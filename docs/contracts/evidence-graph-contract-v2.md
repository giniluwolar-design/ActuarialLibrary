# REVISED CONTRACT v2 — ACCEPTED WITH LEAD CORRECTIONS 27 SEP 2026
## Evidence Graph Contract (issue #4)

**From:** `contracts_reserving`, 27 September 2026
**Supersedes:** `docs/project/review-2026-09-25-wave1.md` §1 draft
**Status:** Accepted for bounded implementation after lead corrections; implementation and ticket closure require new acceptance evidence.
**Privacy:** no private runtime data, no raw claims, no credentials

---

## Correction checklist — #4 Evidence Graph

| # | Verdict correction (27 Sep verdict) | Contract section |
|---|---|---|
| 1 | Revision-pinned immutable node identity with workspace, run, data-version, config and revision references; labels are display fields | §1 Identity scheme |
| 2 | Separate availability, validation and fitting-membership states; observed zero stays observed; exclusion does not mutate source cell | §3 Node states |
| 3 | Authorship separated from evidential role; tool output is not model narrative | §2 Authorship vs evidential role |
| 4 | Bidirectional edge-type validation; `result derived_from narrative` cannot bypass rules | §4 Edge-type validation |
| 5 | Unknown legacy provenance preserved, never invented; idempotent atomic migration; workspace-scoped legacy T-number mapping | §7 Migration |
| 6 | Default-private graph content; explicit export policy covering metadata, edges and ids | §6 Export policy |
| 7 | Paginated adjacency with deterministic cursors; no silent omission; 100/50 KB targets measured on fixtures | §5 Lazy loading |
| 8 | Recompute-versus-stored rules with canonical serialization; hash alone cannot reproduce evidence | §8 Recompute vs stored |
| 9 | Engine-neutral node categories for assumptions/patterns, mortality/discount inputs, payment traces | §9 Node categories |

---

## 0. Grounding

No graph exists today. `WorkspaceStore` writes one JSON blob per row (`workspace.py:93-98`); `workspace_view` returns the whole workspace in one response (`server.py:122-145`). Evidence is a list of `{id: "T{n}", tool, arguments, result}` records with sequential per-workspace ids, no timestamps or hashes (`agent.py:376-384`). F004 requires every displayed relationship to resolve to recorded evidence from headline result to source data, assumptions, methods, controls and explanations. This contract is a pure interface specification; no code changes yet.

## 1. Identity scheme (answers correction #1)

**Opaque immutable IDs.** Every node and edge carries an opaque immutable ID that cannot be derived from display labels. Identity format:

```
node_id = UUID
edge_id = UUID
node_revision_key = (node_id, revision)
edge_endpoints = (source_node_id, source_revision, target_node_id, target_revision)
```

The following are separate metadata fields, never concatenated into an opaque ID:

- `class` — node class from §9 (engine-neutral categories)
- `workspace_id` — workspace identifier
- `run_id` — exact run that produced the node
- `data_version` — data version hash or snapshot id
- `config_hash` — full hash of the configuration revision that produced this node
- `local_key` — human-readable display label (e.g. `baseline`, `paid:2023:3`) — **display field only, not identity**
- `revision` — integer, starts at 1; new revision on any payload change; old revision preserved, never overwritten
- `direction` — incoming/outgoing relative to the inspected node, not edge identity

Both endpoint revisions are stored on every edge and verified on read. A missing endpoint is a broken-reference control, never silently repaired. Changing recorded labels or payload creates a new revision; old revisions remain unchanged.

**Why opaque:** `result:<workspace>:baseline` and `cell:<workspace>:paid:2023:3` are insufficient when a workspace contains multiple runs or data versions. The opaque ID is the only stable reference for saved-result reproduction.

## 2. Authorship vs evidential role (answers correction #3)

Every node carries two separate fields:

- **`authorship`** — `{actor, role, action, created_at}`. `actor` is a local identifier; `role` is one of `analyst`, `tool`, `model`, `migration`; `action` is the explicit user action or tool call id. Authorship records who/what produced the node, not whether its content is factual.
- **`evidential_role`** — one of `calculation_evidence`, `human_judgement`, `model_explanation`, `import_provenance`, `execution_record`. Determines graph-validator enforcement.

A `tool/invocation` is an execution record (`evidential_role = execution_record`) referencing separately classified request and output nodes. A model request is not calculation evidence; deterministic tool output may be calculation evidence with pinned inputs and computation provenance. A `judgement/selection` has `evidential_role = human_judgement` and requires an explicit user-action id. The analyst may propose labelled scenarios through permitted tools; it cannot create final human selections.

## 3. Node states (answers correction #2)

Three orthogonal state dimensions, never conflated:

| Dimension | Values | Meaning |
|---|---|---|
| **Availability** | `observed`, `missing`, `future` | Whether a value is present at valuation |
| **Validation** | `valid`, `invalid`, `unavailable-blocked` | Whether the value passes schema/rule checks |
| **Fitting membership** | `included`, `excluded`, `outside-window` | Whether the observation enters the current fit |

Rules:
- An observed zero is `observed` — never reclassified as missing because the value is zero.
- An observation may be `excluded` in one scenario and `included` in another; exclusion must not mutate the source-cell state. The fitting-membership link is scenario-scoped, not cell-scoped.
- `outside-window` means present but outside the averaging window; the governing config revision is recorded.
- `unavailable-blocked` means a required input is missing and dependent calculation is blocked; reason code + blocker node id required.
- `invalid` means failed validation (e.g. non-positive denominator); control code recorded.

## 4. Edge-type validation (answers correction #4)

Each edge type declares permitted `(source_class, target_class)` pairs. Validation runs in **both directions** on write:

- Forbid any edge whose source or target class is not in the allowed pair list for that edge type.
- Forbid `supports` edges originating from `narrative/*` nodes — citation does not confer numerical authority.
- Reject `calc/result derived_from narrative/explanation`; model narrative is never a numeric dependency, regardless of edge direction. Permit explanation-to-result `explains` and `cites` edges only where their typed pair contract allows them.
- `explains` edges are one-directional (explanation → result).
- `cites` edges carry optional `{page, offset, length}` spans and do not convey numerical authority.

Edge types (immutable rows): `derived_from`, `used_observation` (factor→cell pair), `excludes` (exclusion→cell pair), `based_on` (scenario→baseline result), `has_control` (result→control), `produced` (tool call→artifact/scenario), `cites` (narrative/judgement/explanation→any), `explains` (explanation→result), `supersedes` (node→node), `responds_to` (tool call→transcript turn).

## 5. Lazy loading (answers correction #7)

Three levels replacing the single mega-response:

- **L0 (upfront):** workspace summary — metadata, headline result rows, scenario labels, node/id stubs. Budget ≤ 100 KB measured on fixtures.
- **L1 (on expand):** node summary + adjacency stubs with id, type, direction, label. Budget ≤ 50 KB measured on fixtures. Adjacency is paginated by unique edge ID within a pinned snapshot, configurable limit (default 200). Clients request the next page with its opaque cursor; large payloads belong at L2.
- **L2 (on demand):** blobs — artifact bytes, document text, claim drill-down rows, full factor matrices.

Pagination contract: response includes `{items, next_cursor, has_more}`. Sort adjacency by unique edge ID, not target node ID (multiple edges may share a target). A cursor pins node revision, adjacency snapshot, filters and last edge ID. Omitted cursor starts page one; malformed/incompatible cursors return 400. No skipped or duplicated edges across pages, including concurrent appends.

## 6. Export policy (answers correction #6)

**Default: all graph content is local/private.** Numeric arrays, artifacts, source summaries and graph labels are all potentially confidential even without claim rows. Private IDs, filenames and hashes can disclose information.

**Explicit export policy:**
- **Public synthetic example:** generated from test fixtures with no linkage to any real workspace. Exported IDs are synthetic, metadata is stripped to display fields only, edge types are generalised, hashes are replaced with synthetic placeholders.
- **Analyst local review export:** includes metadata and edges but scopes IDs to the selected workspace; private-class payloads are excluded by default; the export carries an `export_policy` manifest listing what was included (metadata, edges, blob references) and what was excluded.
- **Blob export:** explicit opt-in per blob; hash and filename recorded in the export manifest but the blob itself is exported only on explicit selection.

No public export occurs without the export manifest. The manifest is part of the export artifact and is machine-checked on import.

## 7. Migration (answers correction #5)

Additive, transactional, idempotent, scoped to one workspace:

1. Add `nodes` and `edges` tables beside existing `sessions/jobs/feedback`; old blob schema unchanged.
2. Backfill on first graph request: blob → nodes. Legacy `T{n}` ids are mapped via a `legacy_t_map(workspace_id, legacy_id → node_id)` table.
3. **Unknown provenance preserved:** if computation time, library version or actor is unknown in the legacy blob, the migrated node records `unknown` for those fields; migration time/version is recorded separately in a `migration` row. **Never backfill invented original provenance.**
4. **Idempotent:** running migration twice on the same workspace produces identical node/edge sets and the same legacy T-number mapping; second run is a no-op detected by a migration marker row.
5. **Atomic:** migration runs in a single transaction; on failure the workspace is unchanged and the marker is not written.
6. **Workspace-scoped T-number mapping:** the legacy map keys on `(workspace_id, legacy_id)`; a T-number from workspace A never resolves in workspace B.

Legacy warning strings are preserved as display text; typed controls are added alongside them. No gratuitous breaking change to existing results or exports.

## 8. Recompute vs stored (answers correction #8)

Rule: a value is recomputed on demand iff it is a pure deterministic function of immutable ancestors and is not referenced by a saved result (per-cell observations, factor triangles — today already recomputed via `review.py`). Anything referenced by a saved result, scenario or artifact, or expensive (a full reserving run), is stored at save time.

When both stored and recomputed copies exist, compare `content_sha256` under versioned canonical serialization: sorted object keys, ordered arrays, finite numbers in a round-trip-safe representation, explicit missing values and no volatile timestamps. Do not round distinct numeric results to the same hash. Pin computation version and immutable ancestors for recomputation; use stored historical evidence when that version cannot be reproduced. A hash alone cannot reproduce evidence.

## 9. Node categories (answers correction #9)

Engine-neutral categories (not tied to any one actuarial engine):

| Category | Classes | Content |
|---|---|---|
| Assumptions / patterns | `assumption/exclusion`, `assumption/terminal`, `assumption/timing` | Human or authored inputs |
| Mortality / discount inputs | `mortality/source`, `discount/curve`, `mortality/edition` | External source references |
| Payment traces | `payment/trace`, `payment/schedule`, `payment/projection` | Cash-flow rows |
| Calculation evidence | `data/source`, `triangle/cell`, `calc/factor`, `calc/result`, `control/check` | Deterministic outputs |
| Judgement | `judgement/selection` | Human-authored selections |
| Explanation | `narrative/explanation` | Labelled model output |
| Execution | `tool/invocation` | Typed execution record referencing request and deterministic output separately |

The shared graph is independent of any one engine. No graph rewrite of Streamlit is required for the first additive slice.

## 10. Acceptance criteria

1. Existing suite passes unchanged; new workflow test expands one result cell and every edge resolves to a stored node within the three levels (F004).
2. Saved baseline payload is byte-identical after restart and a simulated `library_version` bump; a new run creates a `supersedes` node instead of mutating.
3. Recomputed pure-function nodes (observations, factor matrices) match stored `content_sha256` under canonical serialization.
4. Creating a `judgement/selection` via `/tools` returns 4xx; graph validator rejects calculation dependency on narrative in either direction while allowing correctly typed `explains`/`cites` edges. Test deterministic tool output separately from model request.
5. An exported graph artifact contains no private-class payload bytes; the export manifest lists included/excluded classes.
6. Every missing-evidence presentation carries `{state, reason_code}`; the discounting case yields `unavailable-blocked`.
7. L0 ≤ 100 KB and L1 ≤ 50 KB on largest example workspace; pagination returns deterministic cursors.
8. Migration is idempotent and atomic; legacy T-number mapping is workspace-scoped; unknown provenance is preserved, never invented.
