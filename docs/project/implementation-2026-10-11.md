# First implementation milestone — 11 October 2026

Scope: additive Evidence Graph saved-result review and calculation-library foundations. Refs #4, #5, #6, #7. This does not finish those tickets or the common workbench release.

## Implemented

- `EvidenceGraphStore` beside existing SQLite tables: immutable revision keys, typed edges, atomic/idempotent legacy backfill, unknown original authorship, scenario-scoped fitting membership, lazy payloads and bounded cursor pagination. GET graph routes read persisted checkpoints, not model output or a new calculation. Local-review JSON excludes private nodes/payloads and dangling edges.
- Method comparison opens recorded result → factor → cell dependencies. Keyboard-operable evidence cards, breadcrumbs, provenance details and explicit payload loading preserve the existing workbench visual direction. Export is labelled local/confidential, never public/anonymised.
- `project_payments` uses explicitly selected reserve rows with paid-pattern allocation, signed components, explicit tail timing, external schedules, dimensionless conditioning and currency-aware reconciliation. Partial schedules suppress full totals.
- `discount_payments` accepts injected dated curve evidence, ACT/365F and documented log-linear discount-factor interpolation. Missing/mismatched evidence blocks discounted values while retaining valid undiscounted rows. Bounded XLSX import parses user-supplied bytes, not downloaded or invented source values.

## Verification

- Numerical and integration, after review repairs: `PYTHONPATH=src .venv/bin/python -m pytest -q` → 108 passed, 123 dependency deprecation warnings. Independent literal projection examples include 258/132/90, BF 40/60 and signed -12/+57; discount example uses two distinct payment dates with PV 173.553719008264 at 10%.
- Changed Python Ruff and `node --input-type=module --check < web/app.js` → passed.
- Browser: `tests/browser_evidence.cjs` against an isolated synthetic preview → saved result/factor/cell traversal, lazy recorded payload, breadcrumbs, actual downloaded JSON with resolving endpoints, same identity after refresh, keyboard activation, mobile horizontal-width guard and no page errors. Screenshots are local diagnostic artifacts, not public exports.
- Model reliability: no fresh local-model trial. This workflow calls deterministic tools directly and does not require an inference round.
- Independent review: separate standards/spec reviews of `fbd0dc1...1a891c9` reproduced defects; bounded fixes and regression checks are in the next commit. Re-review pending; see `review-2026-10-11-implementation.md`. A passing suite does not certify the full specifications or release readiness.
- Repairs cover immutable metadata, numerator/latest-balance lineage, actual FS dependencies, v3 backfill upgrades without deleting history, per-origin required CDFs, valid XLSX relationship paths, encoding-independent DTD rejection and typed numerical overflow. Tests now follow every explicit summary page rather than relying on random UUID order.
- Actual official 30 June 2026 EIOPA archive independently imported: both EUR variants produce 150 nodes. Source C7=3.3 is percent; C9=10 and C10=14 are basis points; spot C11=0.02592 is decimal annual-effective. Archive SHA-256 `80d5c4af0f4dd8f025103be4f746ae86d62f99a3c313c3024f4700a8965972fb`; workbook SHA-256 `1d7c280201255b22f8bcb12064ec421f8259c226f65ba892d1838ab07d3248f6`. This is source import verification, not the unfinished app discount workflow.

## Remote execution, separately

The cloud executor cloned the reviewed public source and reported 69 passing tests for its separate baseline + mortality/annuity slice; commit `04f2460`. These historical results are not combined with local totals. Local lead has not integrated/reviewed that code. GitHub connection now independently reports push/admin permission, but on 11 October the existing executor reports `environment_offline`; its unpublished commit is not available on GitHub. Recovery of the existing environment is required before retrieving or publishing exact source. Do not recreate code from chat summaries or claim the commit is preserved/lost without evidence. No private original-machine data/credentials were transferred. Phone push delivery and indefinite execution are not verified.

## Remaining

Human final selections; projection/discount app paths and actual schedule/trace downloads; Q2 2026 example; reviewed annuity integration; source ingestion/rights and terminal gates; independent formula-workbook checks; common navigation/typed analyst tools; installation and release checks. Preserve Streamlit and `dist/` until replacement paths have matching evidence.
