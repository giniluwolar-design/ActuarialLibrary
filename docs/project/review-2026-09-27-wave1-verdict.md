# Wave 1 lead-architect verdict — 27 September 2026

Review of `review-2026-09-25-wave1.md`. This response resolves the reviewer checklist and supersedes conflicting recommendations in that draft; it does not certify implementation or close GitHub tickets. Founder authorization to resolve routine questions and coordinate agents remains in force. No new founder decision is needed to start the assignments below.

## Verdicts

| Ticket | Verdict | Required correction before implementation acceptance |
| --- | --- | --- |
| #4 Evidence Graph | Accept-with-revisions | Revision-pinned identity, contextual fitting states, evidence authorship, safe migration and export boundaries |
| #6 Reserving cash flows | Accept-with-revisions | Explicit tail timing, valuation-relative external schedules, cancellation/zero-share cases and partial totals |
| #8 Annuity factors | Reject current calculation specification; retain product direction | Calendar payment dates, annual normalization, mortality age basis, terminal treatment and invalid test expectations must be rewritten |
| #9 AG ingestion | Accept-with-revisions | No inferred caching permission, consistent probability validation, separate source facts from run assumptions, workbook safety |

“Accept-with-revisions” authorizes drafting and bounded implementation against this response. It does not mean the existing draft may be copied verbatim into code. #8 needs another specification review before production factor implementation; independent synthetic reference calculations may proceed.

## #4 — decisions and required revisions

Answers to questions 1–6:

1. Use immutable edges and superseding records. Each endpoint must identify an exact immutable node revision. Do not use a mutable “latest” lookup when reproducing a saved result.
2. A local actor identifier, role and explicit user-action record are sufficient now. These are attribution, not authenticated signatures or formal actuarial approval. No key-pair infrastructure is required for this milestone.
3. Use one selected-factor node per development age, basis and calculation/configuration revision, with membership links to both observed cells of each fitting pair. Derived fitting statistics and observation weights remain inspectable.
4. Use the existing local SQLite database with additive tables and transactional migration. A second graph database is unnecessary.
5. Preserve legacy warning strings and add typed controls alongside them. No gratuitous breaking change to existing results or exports.
6. Start the review experience at the headline total, then show origin rows, then the selected origin's assumptions, factors and source evidence. Origin rows also have direct expansion. This follows the founder's result-centred request without requiring a new preference question.

Additional corrections:

- `result:<workspace>:baseline` and `cell:<workspace>:paid:2023:3` are insufficient identities when a workspace contains multiple runs or data versions. Use opaque immutable IDs with explicit workspace, run/data-version, configuration and revision references. Labels are display fields. Edge IDs and both endpoint revisions must be unambiguous.
- Separate observation availability (observed/missing/future), validation outcome, and fitting membership (included/excluded/outside-window). An observed zero remains observed. The same observation may be excluded in one scenario and included in another; exclusion must not mutate its source-cell state.
- Authorship and evidential role are separate fields. A tool invocation contains a model request and deterministic tool output; do not classify its calculated result as model narrative. Assumptions and human selections are authored inputs to deterministic calculations, not facts magically proven by the library.
- The analyst may propose labelled scenarios through permitted deterministic tools. It cannot create final human selections. Validate edge types by source and target types in both directions; otherwise `result derived_from narrative` bypasses a rule that checks only edges originating at narrative nodes. Citation does not confer numerical authority.
- Legacy provenance may be unknown. Preserve unknown computation time, library version and actor; separately record migration time/version. Never backfill invented original provenance. Migration must be idempotent and atomic, with stable legacy T-number mapping scoped to its workspace.
- Numeric arrays, artifacts, source summaries and graph labels may all be confidential even without claim rows. Default graph content to local/private and apply explicit export policy to metadata and edges as well as blobs. Private IDs, filenames and hashes can also disclose information. A public synthetic example and an analyst's local review export are distinct products.
- Large result payloads belong at L2; L1 holds summaries. Paginate adjacency using deterministic cursors and configurable limits; do not silently omit edges to meet the proposed byte budgets. Measure the 100/50 KB targets on fixtures rather than promising latency from size alone.
- Never recalculate historical evidence using changed code and call it equivalent. Store evidence needed by saved runs or pin a reproducible computation specification. A hash alone cannot reproduce evidence. Define canonical serialization before comparing hashes; separate numeric content from volatile timestamps.
- Add neutral node categories for assumptions/patterns, mortality/discount inputs and payment traces. Keep the shared graph independent of any one actuarial engine. No graph rewrite of Streamlit is required for the first additive slice.

## #6 — decisions and required revisions

Answers to questions 1–7:

1. A non-unit tail requires an explicit dated timing selection. “All remaining tail next period” is a selectable assumption with rationale, not a silent default. Tail=1 needs no timing input. The worked example remains valid when this assumption is explicitly selected. Undated tail amounts can be shown as pending; a complete dated/discounted schedule is unavailable until they are assigned.
2. Reject aligning every annual origin automatically to Q4. External quarterly schedules must specify payment dates or quarter offsets measured from the valuation, coverage of each origin/age, and whether weights are future-conditional or cumulative development proportions. An annual triangle at year-end plus an explicit future quarterly pattern is valid; it cannot manufacture a 30 June observed balance from December data.
3. Permit local partial exports with an unmistakable incomplete label, included/excluded origin list, reasons and reconciliation to the selected, projectable subset. Suppress the full-portfolio total when selections or required patterns are missing. No repeated confirmation dialog is needed.
4. Use period-end dates for the initial reserving schedule. #7 must document day count, fractional maturities and optional timing scenarios. Payment timing is an assumption, not a fact supplied by EIOPA.
5. Yes: quarterly observations through 30 June 2026 are the primary acceptance fixture under the existing triangle contract. Retain 31 December 2025 annual tests. This is a current implementation constraint, not a universal claim about actuarial annual triangles.
6. Net calendar totals are acceptable; expose positive and negative components and per-origin amounts. Never combine currencies or amount bases. Explain that negative projected payments may represent recoveries/corrections rather than gross claim payments.
7. Pin source bytes/hash, import time, source description, effective/valuation date, units, frequency, normalization and rationale. Retrieval time can be unknown for a manually supplied file. Preserve each pattern version.

Additional corrections:

- The residual-weight formula is accepted for valid nonzero remaining shares. Preserve selected ultimate minus paid as the projection base, regardless of selected reserving method. Verify the triangle and selected result have matching valuation, origin set, input version, currency and amount basis.
- `a=n-i` is valid for the current complete square triangle contract; future rectangular/sparse inputs must compute age from dates or reject unsupported geometry.
- Do not silently erase a nonzero reserve below half a cent. Reconciliation uses unrounded values with an explicitly documented currency-aware absolute and relative tolerance; display rounding is separate.
- Replace the unexplained `1e-6` cutoff with a documented numerical conditioning rule. A near-zero denominator can greatly amplify offsetting increments. Surface that condition and require an explicit external schedule when normalization is unstable.
- A zero net reserve and zero remaining share do not prove all future cash flows are zero: positive and negative increments can cancel. Return an empty/zero schedule only when remaining increments are all zero and the reserve is zero. Otherwise require explicit signed cash-flow amounts or another independently justified scale. Include a zero-net recovery/payment regression case.
- Negative remaining share and negative increments may be retained as signed development coefficients; do not describe them as probabilities. Warn on negative components and scale-sign reversals; do not clip or silently rescale away recoveries.
- “Undiscounted schedule always produced” means valid projectable rows can be produced independently of curve availability. Missing factors, selection or timing still block affected rows. An available curve may use the approved interpolation convention; a missing curve cannot be invented. Correct the draft's blanket “never interpolated” wording.
- Reproduce the annual 258/132/90, BF 40/60 and signed -12/57 examples with explicit tail timing. Add quarterly, irregular external-date, partial-selection and mismatched-run tests.

## #8 — replacement specification instructions and answers

1. Adopt factor-space mixing as this product's explicit convention: compute sex-specific factors and weight them. Do not claim a universal pension convention without supporting evidence. Averaged qx and averaged survival are different constructions; neither is justified merely by calling one arithmetic and the other geometric.
2. Do not accept silent forced death at 120 or the unsupported claim that its effect is immaterial. Retain the supplied q120 unchanged. Start the replacement draft with an explicitly finite horizon ending no later than the first unsupported age/year for either required life, expose residual survival at that horizon, and label the result truncated rather than whole-life. Any whole-life closure/extension is a separate explicit actuarial assumption needing sensitivity evidence and later review. In particular, do not kill the participant artificially and thereby create partner benefits. This lets implementation research proceed without pretending a whole-life release requirement is resolved.
3. Keep the public factor workflow unisex for both lives, default 50/50 per life and independently adjustable. Use the product of per-life weights across the four sex pairs as a disclosed composition-independence assumption, alongside the separate independent-lifetimes assumption. Known-sex branches are useful calculation traces/tests, not a silent UI default. Require both ages/DOBs; do not invent a three-year partner age gap. Fixed eligible partner, both initially alive, unit partner benefit, no remarriage/eligibility changes are explicit scope assumptions.
4. Accept an injected discount-factor dependency with curve provenance. Product default remains reporting-date basic EUR EIOPA without VA, with explicit VA option. Missing curve blocks discounted factors, but a survival trace can still be inspected. Synthetic flat-rate test curves are clearly labelled fixtures.
5. Use a factor-result node referencing immutable payment-trace rows/blocks, mortality source, discount source and assumptions. Trace each payment date, sex pair/weight, survival, contingency probability, benefit, discount factor and PV contribution. Keep #4's paginated pattern rather than embedding every term in L1.
6. Reject freezing age last birthday on 1 January for arbitrary DOBs while claiming exact ages. Use a documented attained-age/calendar-year extension, splitting at birthdays and calendar-year boundaries. Constant force within those cells is an implementation convention for arbitrary DOBs, not uniquely prescribed by the official reference-life definition. Specify actual-day year fractions, leap-day birthday policy and demonstrate Jan-1, mid-year and leap-year examples before acceptance. The official definition describes a life born on 1 January: [AG2024 Appendix A](https://www.actuarieelgenootschap.nl/download/projections-life-table-ag2024).

Mandatory formula and test corrections:

- Generate actual calendar payment dates. Primo means the first day of the calendar month/year; ultimo means the last day. `t=k/m` from 30 June would produce 30 July and 30 June annual dates and does not meet the founder's instruction. Default reporting-date cutoff is after that day's payments; future payments are strictly later, with any alternative same-day convention explicit. Separate benefit commencement from valuation; state first-period benefit rules.
- Quote the default factor per 1 unit of annual benefit: payments are 1 for yearly and 1/12 for monthly. If offering a per-instalment factor, label it separately. Show finite-horizon endpoint inclusion so primo and ultimo use the intended number of payments.
- Remove the draft's frequency ordering. For a decreasing discounted survival function on an aligned common horizon with equal annual benefit, the useful synthetic inequality is annual-primo >= monthly-primo >= monthly-ultimo >= annual-ultimo. It is not universal under negative rates/indexation or for increasing reversionary probabilities. Test specific conditions, not an unconditional product rule.
- The primo-minus-ultimo endpoint identity applies to shifted grids with identical intervals and benefit function; it is not universal for calendar schedules with different cutoffs.
- Independent calculations reproduce the draft's synthetic examples: annual male 2.819527104960, female 2.832315809756, mixture 2.825921457358; monthly per-instalment mixture 11.842812103818 (annual-benefit-normalized 0.986901008651); partner 0.095948830798. These validate only those synthetic, truncated grids, not the proposed general date engine or AG factors.
- Keep indexation zero for the initial workflow. If implemented, constant g requires finite g > -1; the proposed -5%/+10% limits are arbitrary and must not reject otherwise valid inputs without a product reason. Any warning band is a review aid, not a mathematical domain.
- Put workbook ingestion in `mortality.py` (#9), factor arithmetic in `annuity.py`, calendar schedule logic behind a separately testable function. Do not put I/O in the factor engine. One-case formula-workbook validation remains a release requirement.

## #9 — decisions and required revisions

- Question (a): do not infer that downloading a file licenses additional storage or redistribution. No legal permission is granted by this review or by founder preference. Keep synthetic-only development unblocked; actual AG caching and AG-containing exports remain a documented source-rights release gate pending applicable permission/terms. In-memory use is not asserted to solve that question. [AG disclaimer](https://www.actuarieelgenootschap.nl/disclaimer) still reserves copying, storage and publication rights in the retrieved search extract on this review date.
- Question (b): strictly synthetic public numerical examples and fixtures. Source titles, URLs, schema descriptions and reference hashes/byte sizes may be retained as identification metadata under this technical inventory policy; they do not establish rights to the data itself.
- Question (c): defer automatic official-source download; user-supplied workbook ingestion remains the planned adapter.
- Preserve q120 exactly and expose supplied age/year bounds. Terminal treatment belongs in factor-run assumptions, never in the raw imported grid.
- Separate immutable import provenance from run-specific reporting date, as-known/scenario role and fractional survival assumptions. Constant force is not a field read from the workbook. Capture import time; do not invent source retrieval time for user files. Allow deduplication by bytes while retaining separate import events and edition assertions.
- Resolve the contradictory qx rules: mathematically accept finite 0 <= q <= 1 in the generic mortality contract, including synthetic zero/one boundaries. Reject bools, NaN/infinity, text and duplicates. Edition-specific expectations may add controls. Never convert blanks to zero. The complete official-workbook adapter must reject a missing required grid cell; a separately typed partial custom table may report unavailable lookups.
- Hash mismatch is not proof of corruption, but structural validity is not official-source authenticity. Store it as an unverified user variant; require explicit variant acknowledgement before calculation. Never label it verified AG merely because worksheet names match.
- Parse uploaded XLSX as inert data: size/decompression bounds, no macros or external fetches, and explicit rejection of formula/error cells in the qx data grid unless a separately reviewed cached-value policy exists. Handle unexpected dimensions and extra sheets deliberately.
- A test against two hashes/byte sizes does not prove fixtures are synthetic. Generate fixture values from test code with an explicit seed/formula; inspect the eventual staged inventory. Preserve AG2024/AG2026 reporting-date selection and publication-date provenance with actual source evidence.

## First-commit inventory verdict

Conditional approval of the proposed categories, with amendments below. This is not a claim that a commit or public push has happened. Use an exact file manifest and review the staged diff; do not rely on the now-stale count of 63 proposed files.

- A: approve source, tests, configuration, methodology, agent guidance and authored build scripts subject to ordinary staged-content/secret review. Distinguish incomplete prototype claims in README and docs. Do not claim all tests or integrations were rerun by this review.
- B: approve exclusions. Fixed `.gitignore` to use `node_modules` (also ignores symlinks), and added `.scratch/`, `.env`, `.env.*` with `.env.example` exception, and SQLite main/WAL/SHM exclusions. Verify the existing path and representative nested paths with `git check-ignore` before staging.
- C demo data: approved. In-memory regeneration from the repository's default simulator exactly matched `claims.parquet`, `coverage.csv` and the intentionally invalid CSV as tables on 27 September. No raw records were printed. This is stronger evidence than an identifier-pattern scan.
- C workbook: retain as a curated educational artifact. README links it, and the authoring script depends on `@oai/artifact-tool`; regeneration is not yet a portable public-clone workflow. ZIP integrity passed and no VBA, external-link or connections parts were found. Formula correctness and absence of sensitive cell content still require the documented content review before publication; no blanket XLSX ignore.
- C benchmark: keep as dated evidence with environment/command context; never describe it as a current performance guarantee.
- C project memory: retain reviewed, non-sensitive decisions, lessons and feedback. Prepare a portable public handover: remove unnecessary machine paths/session IDs/usernames and distinguish attribution from personal information before public push. Keep the Wave 1 drafts clearly marked superseded by this review.
- Existing `.openai/hosting.json`: contains project_id/static keys; a secret-pattern scan is not a deployment-ownership review. Leave existing tracked history unchanged. Review whether the old hosting binding belongs in the public project before push; do not rewrite history as a routine cleanup.
- Untracked files are not backed up merely because they exist. The PM may prepare an exact local staging/commit proposal and verify the manifest. This wave does not authorize pushing the unreviewed inventory.

## Founder questions and Wave 2 assignments

1. Slack: continue Herdr notifications plus repository reports now. An absent Slack connector does not block work. Do not invent webhook credentials or treat the draft's mention as a configured integration.
2. GitHub: previously authorized issue-based development covers concise reviewed technical status/decision comments. No repeated founder permission is needed for those comments. Do not post private material, raw chat, machine paths or the unreviewed inventory. Keep tickets open until revised acceptance evidence is reviewed.
3. Actuarial choices: factor-space mixing, unisex per-life weights and explicit finite-horizon treatment above are the lead's development decisions. Whole-life closure remains a technical/release question requiring evidence; it need not stop other work.
4. Reference grain: quarterly Q2 2026 accepted as above.
5. Partial exports: allow labelled incomplete local review exports as above.

PM assignment: create a concise revised contract package answering every required correction; retain the original draft as history. In parallel, prepare #7 discounting-convention research and #5 a synthetic Evidence Graph interaction prototype against the revised interface. These may start now; dependent final architecture (#10) must not be called settled before interfaces are reviewed. Avoid competing edits by assigning disjoint files. #8's replacement and #9's synthetic importer design can proceed independently. No real AG data, final selections, release claims or private runtime data are required.

Deliverables for the next report: revised contracts with a correction checklist, a inspectable #5 prototype with run instructions and visual evidence, #7 sources/conventions, and an exact first-commit manifest. Notify the lead and founder after each bounded package; ask the lead first on routine blockers. Use non-waiting completion notifications so PM and lead cannot deadlock waiting for each other's turns. Do not create a ping-pong of empty status prompts. Review remains required before merging numerical changes or closing tickets.

## Verification scope of this review

Inspected actual source contracts and drafts; recalculated the synthetic annuity examples; compared all three demo datasets to in-memory generation; inspected workbook ZIP structure; checked Git state and the live Herdr inventory. Browser health was unavailable at 127.0.0.1:8765. The 33-pass suite is prior delegation evidence, not a fresh numerical certification here. No calculation code changed. Git-ignore verification is recorded in the lead's tool output. Visual prototype, model reliability, real-AG rights and public release remain unverified.
