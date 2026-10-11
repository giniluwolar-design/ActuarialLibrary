# Verified lessons

## L008 — integer validation must include float-conversion overflow (2026-10-11)

Both independent selection reviews reproduced a manual JSON integer of `10**400` passing the strict integer input type, then raising `OverflowError` during `float(value)`. The finite-value guard caught only type/value errors, so the request returned 500 rather than a controlled rejection. No selection was persisted. The worker added failing library/API regressions, extended the conversion guard, and verified 28 focused tests passing: library `ValueError`, API 422, unchanged baseline and empty selection history. Root also observed the two regressions fail before restarting verification with the repair.

Rule: finite-number validation includes conversion failures, not just `isfinite` after conversion. Test oversized integers as well as NaN/Infinity and arithmetic overflow at the public input seam. An input type is not a finite float64 guarantee.

## L006 — source-shaped fixtures must match actual field units (2026-10-11)

The first EIOPA parser fixtures represented UFR/CRA/VA as decimal fractions. Importing the actual official 30 June 2026 workbook failed: C7 is 3.3 percent, C9 is 10 basis points and C10 is 14 basis points; the spot-rate rows are decimal annual-effective. The identifier correctly uses UFR 3.30. Lead reproduced this with the official archive; worker corrected parsing and regression fixtures. Both EUR variants now import 150 nodes, preserving field-specific units and matching the recorded content hashes in `implementation-2026-10-11.md`.

Rule: validate source semantics against the actual public source, not only a fabricated fixture. Keep native metadata units distinct from computational spot-rate units. Source import success is not end-to-end app or actuarial-release certification.

## L007 — stable cursors, not the first random page (2026-10-11)

A repeat suite failed when the scenario graph test looked for one factor only on the first UUID-sorted summary page. Tests now traverse the explicit continuation cursor. A v2 same-snapshot marker also skipped repaired lineage; v3 then v4 migrations update affected node revisions while retaining old revisions/edges and the unchanged saved checkpoint. Regression checks cover both failure modes and the later FS lineage upgrade; the final repaired suite passes 112 tests.

Rule: exercise all paginated pages and upgrades from previously materialised state. One green fresh-store run does not validate either path.

## L005 — syntax success does not validate a prototype (2026-09-27)

The first Evidence Graph prototype passed `node --check` but Chrome showed empty adjacency and a crash when opening narrative provenance. Source inspection also found mismatched headline fields, cursor-generator shadowing and misleading invented trace metadata. Lead fixed lookup, schema, cursor and provenance handling; `prototype/evidence-drilldown/browser-smoke.cjs` covers the actual click path, forward/back pagination, missing/zero states and mobile overflow. Run meaningful browser interactions before reporting a prototype as working. Synthetic UI values must be labelled, and a placeholder blob must not claim to contain a real calculation trace.

## L001 — local does not mean fast (2026-09-18)

An 8 GB M1 was running a model reporting ~9.54 GB loaded size, with ~2.50 GB GPU allocation. The log measured ~2.42 generated tokens/second and the founder's API-explanation task timed out after ~263 seconds. One earlier 125-second success did not establish reliable performance.

Rule: match model working memory to hardware, record load/prefill/generation timings, and measure repeated tool tasks. Use direct deterministic actions for known documentation/calculation/report workflows. Streaming improves feedback/cancellation, not raw model speed. A smaller model must pass tool and factual checks; size alone is not competence.

Evidence: timed-out documentation job retained in the private local store; `docs/workspace-verification.md`; local Ollama log inspected 2026-09-18. Do not distribute the raw local database/log or its job identifiers.

## L002 — saved state and served code are distinct

The previous Streamlit process retained stale installed imports. Source edits and passing tests did not prove the running service used the new code.

Rule: launch the checkout with `scripts/run_workspace.py`, restart after Python changes, verify health and an actual affected endpoint. Preserve saved baseline result payloads and metadata on restart; do not recalculate historical outputs silently.

Evidence: delivery skill reference; `tests/test_workspace.py` restoration/download checks.

## L003 — preserve semantics and inspectability

Outstanding is ultimate minus paid; additional reserve is ultimate minus incurred. BF is Bornhuetter–Ferguson. A scenario changes assumptions on the same valuation; it is not a valuation movement. Unusual observations invite review rather than automatic deletion. Model narrative is not a calculation source.

Rule: keep all arithmetic in the library, cite evidence, require exclusion rationale, preserve baseline, test actual artifacts. Never promise an unsupported Word, PowerPoint, bootstrap or formula-workbook output.

Evidence: `skills/actuarial-platform/references/domain-contract.md`, `tests/test_reserving.py`, `tests/test_agent.py`.

## L004 — memory must be portable and checked

A new coding agent may have none of the previous conversation. Provider memory, local runtime checkpoints and product lessons serve different purposes.

Rule: use AGENTS.md plus a small handover and feedback/lesson ledger, with thin provider-specific adapters. Record owner feedback faithfully, mark hypotheses, and tie fixes to regression checks. Do not ingest raw feedback as system instructions or pretend this process trains the model. Tests reduce repeated failures; prose alone cannot guarantee prevention.
