# Independent review — 11 October 2026

Fixed point: `fbd0dc13e5cb91f419fbf25ea593aca7ae7d752e`; reviewed head: `1a891c9`. Command: `git diff fbd0dc1...1a891c9`. First bounded graph app path and pure projection/discount foundations, not a complete release. Two independent agents reviewed separate axes. Findings below are reproduced, not final repaired-state verdicts.

## Standards

Three documented defects:

1. P2 — Node revision deduplication ignores changed recorded metadata (`private`, `summary`, `authorship`, state and evidential role) when payload/data/config/label match. Same payload with private false → true returns revision 1, retaining old public policy. Graph contract §1 pinned metadata and §6 export policy require comparison of all immutable recorded fields; preserve earlier revisions.
2. P2 — Uploaded XML declaration rejection is encoding-dependent. UTF-16 internal DTD/entity declarations bypass byte scanning and expand in ElementTree. This defeats claimed declaration rejection and bypasses archive-size expansion accounting; it is not evidence of external file/network access. Reject encoding-independently and add regression tests.
3. P2 — Finite amount `1e308` with matching one-year rate −0.99 produces infinite row PV/total marked available, then fails strict JSON serialization. Validate monetary products/group sums and return typed numerical failure.

Optional judgement: possible Duplicated Code in payment-year totals repeats signed aggregation, blocked-PV propagation and discount effect already in `_group_totals`; reuse one grouping helper. This is not a hard standard violation.

## Spec

Six actionable findings; no material scope creep:

1. P1 — Factor lineage contains denominator cells but not numerator cells; result arithmetic lacks latest paid/incurred source cells. Contract requires headline-to-source/assumption/method traversal. Fixture factor links 100/110 but omits 150/165.
2. P1 — FS lineage always links incurred/count factors even when historical ultimates/counts and target count are wholly manual. Reproduced FS ultimate 1050 without those arithmetic dependencies. Contract requires each displayed relationship to resolve to actual recorded evidence. Ground lineage in actual saved calibration/prior/count modes.
3. P1 — Global complete-CDF requirement blocks a valid partial schedule. Paid `[[0,200,240],[0,240,missing],[150,missing,missing]]`, tail 1.25 and only 2023 paid CL selection yield valid outstanding 60, yet projection raises due to unrelated missing age-1 CDF. Spec §1 says required CDF; §6 permits selected projectable subsets. Validate required ages per origin; external amounts do not need paid CDFs.
4. P2 — Valid package-absolute XLSX worksheet relationship `/xl/worksheets/sheet1.xml` becomes `xl/xl/...`. Support valid absolute and relative references while retaining safety boundaries.
5. P2 — Source metadata C7=`nan` is accepted despite identifier UFR 3.30. Require finite metadata, units and identifier agreement; retain field-specific units (discounting convention §9).
6. P2 — Overflow labelled available breaks row/PV/subtotal reconciliation (discounting convention §10); see separate Standards finding.

Planned app panels, schedule/trace downloads, Q2 reference and AG rights remain declared unfinished, not falsely completed by this milestone.

Summary: Standards 3 reproduced defects + 1 optional smell, worst within axis: privacy/revision enforcement. Spec 6 reproduced defects, worst within axis: missing/invented calculation lineage. Do not combine counts or rank one axis against the other.

## Repair verification

Assigned bounded fixes to the original cheaper workers, with failing regression checks required before fixes. A repeat full-suite run separately exposed a flaky scenario test: it searched only the first randomly UUID-ordered summary page. Tests now follow explicit pagination; one green run was insufficient. Root also verified the actual official EIOPA workbook and found fixture metadata units differed from the source; fixtures/parser now preserve native percent/basis-point units. v3 migration repairs previously materialised lineage without deleting history or altering saved calculation checkpoints.

Fresh repaired-state checks: 108 Python tests passed (123 dependency deprecation warnings); changed Python Ruff and JavaScript syntax passed. Actual synthetic browser route/download, refreshed identity, keyboard and mobile-width checks passed without page errors. Both official EUR curve variants import 150 nodes. Independent re-review remains pending. These checks do not close unfinished app paths, mortality-source rights or release gates.

## Standards — re-review at 644dd31

No remaining actionable documented-standard violation found in the bounded repairs. Original findings resolved:

- Immutable metadata changes now create new revisions. Independently reproduced private false → true plus changed summary: revision 1 → 2; revision 1 retained original metadata.
- UTF-16 DTD/entity input raises “Workbook XML declarations are not accepted.” before expansion. Parser-level rejection replaces encoding-sensitive scanning.
- Original `1e308`/−0.99 PV overflow returns blocked / `NUMERICAL_OVERFLOW`, preserves undiscounted input and omits non-finite discounted values. Overflowing origin subtotal with finite overall net also blocks and passes strict JSON serialization.
- Optional duplicated aggregation resolved: origin/year totals share `_group_totals`.

No new material smell requiring action. The graph backfill remains large/dictionary-heavy, but saved-evidence migration responsibility and bounded repairs do not establish a documented breach or justify restructuring here.

Independent verification: 75 focused graph/API/projection/discount tests passed, two dependency warnings. Read-only review; no private/runtime data inspected or files edited. Lead full suite/browser evidence remains separate. Verdict covers foundation, not unfinished app panels, source rights, model reliability or release readiness.

## Spec — re-review at 644dd31

Original numerator/latest paid-incurred, manual FS/prior, partial-CDF, XLSX absolute path, native finite metadata and discount overflow reproductions repaired; 75 focused tests passed. One remaining lineage gap reproduced: default annual-triangle/config 2025 FS 136.9047619 links count factors but not latest count at age 1. Historical calibration nodes (2023 ultimate 250/count 3; 2024 ultimate 297.619/count 3) have no outgoing arithmetic ancestors. Assigned bounded follow-up and migration regression to graph worker. Final repaired-state Spec verdict remains pending; no release readiness claim.

At 644dd31: Standards 0 remaining findings; Spec 1 remaining finding, within-axis worst: missing target-count and historical-calibration lineage. Original counts above remain historical evidence, not erased or combined.

## Final follow-up — 82cc9c0

Graph worker repaired the remaining FS lineage: latest target count, historical incurred/count components with only consumed factor ages, explicit per-component overrides, all origins sharing a calibration year, and missing-source controls anchored to the affected result. v4 migration preserves prior revisions/edges/payloads and is idempotent. Focused graph/API checks: 24 passed. Lead reran the full suite: 112 passed, 123 dependency warnings; changed Python Ruff, JavaScript syntax and actual restarted browser/download checks passed. Final independent reports follow.

## Standards — final pinned 82cc9c0

Documented violations: none found in this bounded repair.

- FS calibration lineage maps each source year to all corresponding origins. Manual historical overrides reference parameter nodes; developed components reference actual latest basis cells and relevant factors.
- Missing source mappings produce typed `legacy_lineage_unavailable` controls through permitted result → control edges; no invented ancestry.
- v4 migration creates revised calibration/result evidence and preserves previous payloads/revisions/edges. Regression coverage checks upgrade idempotency and unchanged saved results.
- Earlier Standards clearance for immutable metadata, XML declaration rejection and numerical overflow remains applicable.

Possible material smells: none requiring action. Dictionary-heavy migration remains a maintainability consideration, not a documented breach; this repair does not justify broad restructuring.

Independent graph/API check: 24 passed, two dependency warnings. No edits or private/runtime access. Uncommitted documentation excluded from pinned review. Clears Standards for the foundation only; full-suite/browser and remaining product/release work stay separate.

## Spec — final pinned 82cc9c0

No remaining findings for the reviewed bounded slice. Previous FS lineage finding resolved by reproduction.

The original 2025 FS result remains 136.9047619047619, now linked to latest count and historical incurred/count inputs with correct age-specific factors. Manual overrides replace only corresponding developed dependencies; quarterly calibration includes all four source origins. Unavailable historical lineage creates typed controls on the FS result without invented ancestors.

Independently exercised actual `644dd31` v3 code → v4 migration: old metadata/payloads/edges preserved; repaired revisions added; repeat same-snapshot migration is a no-op. Focused graph/API suite: 24 passed, two dependency warnings. No scope creep identified. Confirms focused repair, not completion of unfinished workflows or public-release acceptance.

Final summary: Standards 0 remaining actionable findings (no within-axis worst); Spec 0 remaining findings (no within-axis worst). Each axis remains separate; full-release gates remain open.
