# Verified lessons

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
