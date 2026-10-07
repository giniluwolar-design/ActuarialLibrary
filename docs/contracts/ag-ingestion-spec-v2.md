# AG Mortality Ingestion Specification v2 — ACCEPTED WITH LEAD CORRECTIONS 27 SEP 2026

**Ticket:** #9 AG ingestion — accept-with-revisions
**Supersedes:** `docs/project/review-2026-09-25-wave1.md` section 4 draft (conflicting recommendations superseded by the 27 September 2026 verdict)
**Status:** Specification only — synthetic development unblocked; actual AG caching and AG-containing exports remain a documented source-rights release gate
**Privacy:** synthetic values only; no real AG mortality tables anywhere; no AG content in repo/release/fixtures

---

## 1. Source-rights gate (release blocker)

- **No inferred caching or redistribution permission.** Downloading a file does not license additional storage or redistribution. No legal permission is granted by this review or by founder preference.
- Actual AG caching and AG-containing exports remain a **documented source-rights release blocker** pending applicable permission or terms.
- In-memory use is not asserted to solve that question.
- [AG disclaimer](https://www.actuarieelgenootschap.nl/disclaimer) reserves copying, storage and publication rights.
- Synthetic-only development is unblocked; the spec below governs the technical design only.

---

## 2. Ingestion model

- **User-supplied workbook files only.** The user uploads the parameters/best-estimate XLSX they downloaded from the official AG page themselves, via a workspace upload path.
- The repo, releases, `examples/`, `data/`, docs and test fixtures never contain AG tables, derived qx grids, or workbook copies.
- **Automatic official-source download deferred;** user-supplied adapter remains the planned path.
- Ingestion in a deterministic module (`mortality.py`), adapter pattern as `data.py`.

---

## 3. Validation rules (all machine-checked)

Pipeline: `ingest_workbook(path, confirmed_edition)` → imported tables + validation report, or blocking failure.

1. **Edition confirmation explicit.** User selects AG2024 or AG2026; importer never infers edition silently. Sheet names must match confirmed edition; suffix inconsistent with confirmed edition → blocking error.
2. **Age axis:** column A integers 0–120, contiguous, ascending, starting row 2. Missing/duplicate/out-of-range ages → blocking error.
3. **Year axis:** calendar years read from actual file row 1, never assumed from edition name (AG2026 workbook starts 2024 despite PDF saying 2022 onward). Years integers, ascending, contiguous. First/last year recorded as imported range facts, not hardcoded.
4. **Grid shape:** one numeric qx per (age, year) cell per sex sheet; used ranges to row 126 (non-data cells) ignored, not imported.
5. **qx bounds:** generic mortality contract accepts **0 ≤ q ≤ 1** including synthetic zero/one boundaries. Reject bools, NaN, infinity, text and duplicates. Never convert blanks to zero. Edition-specific expectations may add controls.
6. **Official-workbook adapter:** rejects a missing required grid cell.
7. **Partial custom tables:** report unavailable lookups separately (not as zero).
8. **Sex mapping:** `mannen` → male, `vrouwen` → female, exactly two categories; no unisex table at ingestion (unisex mixing belongs to #8).
9. Validation outcome (pass/block + rule identifiers) persisted with timestamp before any calculation references the table.

---

## 4. Identity and provenance

Each ingested table stored in workspace store, never in repo. Retained fields per import:

- Edition label (user-confirmed), publication date (AG2024 2024-09-12; AG2026 2026-09-08)
- Source URL, **import time** (no invented retrieval time for user files)
- SHA-256 content hash, byte size, sheets imported, imported age range, imported year range
- Sex categories, table form (annual best-estimate qx only)
- Validation outcome + timestamp

### 4.1 Immutable import provenance vs run-specific reporting date

Import provenance is immutable and separated from run-specific reporting date, as-known/scenario role and fractional survival assumptions. Constant force is not a field read from the workbook.

### 4.2 Dedup

Dedup by bytes with separate import events and edition assertions. Two imports same edition different hash → two distinct stored entries; newer never overwrites older silently. New AG editions require explicit re-ingestion; existing keys never remap.

---

## 5. q120 and terminal treatment

- q120 preserved exactly and supplied age/year bounds exposed.
- Terminal treatment **never in the raw grid** — belongs in factor-run assumptions, owned by #8.
- Expose actual terminal-age qx values by sex/year and a computed residual-survival flag; never hardcode q120<1 for every accepted synthetic/user variant. Applies no closure.
- API contract: supplied age/year bounds, terminal qx lookup and source identity. Treatment is selected by the consuming factor run (#8).

---

## 6. Hash mismatch and authenticity

- Hash mismatch is not proof of corruption; structural validity is not official-source authenticity.
- Store as an **unverified user variant**; require explicit variant acknowledgement before calculation.
- **Never labelled verified AG** merely because worksheet names match.

---

## 7. XLSX parsing safety

- Parse uploaded XLSX as inert data: size/decompression bounds, no macros, no external fetches.
- Explicit rejection of formula/error cells in the qx data grid unless a separately reviewed cached-value policy exists.
- Handle unexpected dimensions and extra sheets deliberately.

---

## 8. Fixtures and synthetic guard

- Synthetic public examples and fixtures only (verdict section #9(b)).
- Source titles, URLs, schema descriptions and reference hashes/byte sizes retained as identification metadata under technical inventory policy; they do not establish rights to data.
- Fixtures generated from seeded test code (explicit seed/formula), not copied from real workbooks.
- Fixture provenance comes from seed/formula code. Hash comparisons alone are not proof of synthetic origin.
- AG2024/AG2026 reporting-date selection and publication-date provenance preserved with actual source evidence.

---

## 9. Tests to pin

- Synthetic-only guard (fixtures generated from explicit seed/formula code)
- Happy path: synthetic AG2024-shaped workbook imports; provenance persisted and retrievable after store reopen
- AG2026-shaped workbook: year headers read from file
- Blocking failures: wrong sheet names; edition suffix mismatch; ages not 0–120; non-contiguous years; qx < 0, > 1, or blank in required cell; non-data rows ignored. Endpoints 0 and 1 are valid.
- Hash mismatch: same edition different bytes → warning + unverified variant label; exact hash → matches inspected reference
- Retrospective gate: API never returns AG2026 as as-known basis for 2026-06-30; retrospective result labelled
- Terminal age: qx(120)<1 recorded and surfaced; no closure applied
- Drift: two imports same edition different hash → two entries; old ids stable
- Generic contract: rejects bools, NaN, infinity, text, duplicates; accepts 0 and 1; never converts blanks to zero
- Official adapter: rejects missing required grid cell
- Partial custom table: unavailable lookups reported separately

---

## 10. Marking and review requirement

**ACCEPTED FOR SYNTHETIC ADAPTER IMPLEMENTATION; RIGHTS GATE RETAINED**

No inferred caching or redistribution permission. AG source-rights gate documented as release blocker pending applicable permission or terms. This document supersedes conflicting recommendations in the 25 September draft; it does not certify implementation or close the ticket.
