# Explicit human selection milestone — 11 October 2026

Initial implementation: `263b3355afd4c974df516e08ad5ce136bc633c4a`; repaired code: `6cf650759cd7eacef576962ec20a4157ada2b481`; review baseline: `a32ccd88e394c0266f83343741a92ec426640f3e`. Refs #6/#12; prerequisite slice, not completion of either issue. Existing draft PR #14; no merge, deployment or issue closure.

## Implemented

- Deterministic `select_reserve` applies one explicit saved-method/manual/clear choice without rerunning reserving. It preserves baseline/scenario outputs and deep-copies result metadata/configuration.
- Saved baseline method must be available. Manual ultimate must be finite; overflow is rejected. Outstanding and additional reserve retain their signs. A nonblank rationale is mandatory.
- Dedicated human-only API appends revision/action/time/authorship/rationale/result snapshots. Optimistic concurrency rejects stale edits; failed persistence leaves the live state unchanged. No analyst model selection tool or silent reserve approval.
- Existing Methods screen includes explicit confirmation, partial-selection status, exact selected rows, warnings, history and revision-pinned downloads. Clearing preserves history. The existing workbench visual direction, Streamlit workflow and `dist/` prototype remain.
- Saved workspace restoration no longer invokes the reserving constructor/engine before loading historical outputs. Legacy checkpoints without selection fields still restore.
- Exact revision ZIP contains results/factors/history CSV and JSON. Per-row rationale is distinct from the last action's rationale. CSV textual formula prefixes are escaped once; JSON preserves exact source values.

## Verification

- Numerical/library + API at repaired code `6cf6507`: 28 focused selection tests passed; fresh full Python suite 140 passed, 123 dependency deprecation warnings. This includes signed outcomes, nonfinite/overflow rejection (including oversized integers), warning lifecycle, immutable prior records, persistence failure, conflicts and no restoration recalculation. Earlier 138-pass result preceded two independent review regressions.
- Integration at repaired code: actual synthetic browser workflow passed for saved method, manual negative ultimate, reload, stale second-browser rejection/refresh, clear and historical immutability. The downloaded ZIP was opened and its exact JSON revision/action/selected rows checked. The existing evidence browser workflow also passed after the Python service restart.
- Visual: lead inspected desktop/mobile synthetic screenshots; teal workbench direction retained. Both browser journeys passed viewport-width and page-error checks. Wide selected tables scroll inside their card.
- Static: changed Python Ruff, JavaScript syntax and diff-whitespace checks passed.
- Model: no new inference reliability trial. This workflow uses deterministic APIs directly.
- Independent review repair: an oversized integer previously leaked conversion overflow as HTTP 500. Failing public library/API regressions now pass with controlled rejection and unchanged state. Shared `decode_analysis` also removes duplicated restoration logic; existing restore/export seams remain green. See L008.
- Independent Standards/Spec re-reviews at `6cf6507`: zero remaining findings per axis for this bounded slice. Each independently passed 33 selection/workspace tests and repeated the original oversized-integer counterexample. Reports remain separate in `review-2026-10-11-selections.md`; this is not full-product release approval.

Browser tests used an isolated synthetic database. No private runtime store, original claims, credentials or cloud source were inspected or transferred. Tests first reproduced the absent UI and worker regressions before fixes; an initial browser-test relative-URL setup error was repaired separately and was not an app defect.

## Unfinished / exact next action

Connect saved selection revision to paid-pattern projection API/UI and actual schedule download, with explicit dated tail and annual/quarterly input availability. Preserve partial/unavailable states and signed reconciliation. Then integrate injected discounting trace/download and the Q2 2026 synthetic reference. Scenario-source selection and graph judgement links remain pending; full #6/#12 acceptance remains open.

Cloud GitHub permission is verified, but the existing executor still has no available workspace/shell tool. Its unpublished mortality/annuity source cannot currently be retrieved or independently reviewed. Do not reconstruct it from summaries or claim phone push/background continuity verified. Local preview/agents require the Mac online.
