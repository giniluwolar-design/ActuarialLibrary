# Independent selection review — 11 October 2026

Fixed baseline: `a32ccd88e394c0266f83343741a92ec426640f3e`. Initial implementation: `263b3355afd4c974df516e08ad5ce136bc633c4a`. Repaired implementation: `6cf650759cd7eacef576962ec20a4157ada2b481`.

Diff commands: `git diff a32ccd8...263b335`, then `git diff a32ccd8...6cf6507`. Commit list: `263b335 Add explicit versioned human reserve selections (#6 #12)`; `6cf6507 Reject oversized manual integers and share saved analysis restoration`.

Independent read-only agents reviewed separate axes against repo instructions/domain/delivery standards and accepted #6/#12 contracts. Synthetic temporary storage only; no private runtime data. Uncommitted documentation was excluded from the pinned code reviews.

## Standards — initial report

One documented P2 breach: `selections._finite` caught type/value errors but not `OverflowError` from `float(10**400)`. The strict integer request therefore escaped the API's validation handler and returned 500. No checkpoint was published. This breached the finite manual-input/controlled-output contract. Add conversion-overflow rejection and library/API regressions.

One nonblocking judgement: possible Duplicated Code. Server saved-analysis reconstruction repeated the workspace decoder's frame inference, configuration validation, warnings and metadata restoration; a shared deserializer would avoid drift. This was not a documented hard violation.

Fresh focused checks: 26 tests passed but omitted the reproduced extreme integer. Human-only selection, immutable baseline/scenarios, persistence-before-publication and pinned exports otherwise respected.

## Spec — initial report

One actionable P2: oversized manual integer produces HTTP 500 instead of controlled validation rejection. The bounded selection requirement calls for a finite explained manual ultimate; projection spec requires float64 throughout. Reject unrepresentable values. Independent synthetic API reproduction confirmed 500 and no persisted selection.

26 focused tests passed; ordinary selection/history/export behaviour looked sound. No scope creep. Declared later scope was not counted as missing functionality against this prerequisite slice.

## Standards — final re-review

Documented breaches: none remaining. The overflowing integer produces the intended `ValueError`; independent isolated API reproduction returned 422 with finite-value explanation, unchanged baseline, no selection or history published. Public library/API regressions cover rejection and state preservation.

Previous possible duplication resolved: `workspace.decode_analysis` serves baseline/scenario restoration, selection continuation and export; duplicate server helper removed. No new material smell found in the repair.

Fresh independent checks: 33 tests passed (28 selection plus five workspace restore/export); two dependency warnings. Direct original-case reproductions passed. No edits or publishing.

## Spec — final re-review

No remaining actionable findings for the bounded selection slice; no scope creep. Original `10**400` API counterexample independently repeated: 422, baseline/current selection/history unchanged. Previous P2 resolved.

Shared saved-analysis restoration preserves selection/export semantics without recalculation. Focused selection plus workspace checks: 33 passed, two dependency warnings, temporary synthetic storage.

Scenario-source choices, graph judgement links, projection/discount panels and full #6/#12 acceptance remain deferred. This does not certify unfinished features or public-release readiness.

## Lead verification / verdict

Fresh repaired full suite: 140 passed, 123 dependency warnings; Ruff/JS syntax/diff checks passed. Restarted isolated synthetic app; both actual selection and evidence browser/download journeys passed, with desktop/mobile review. No new model-reliability trial.

Final remaining findings: Standards 0 (no remaining worst issue); Spec 0 (no remaining worst issue), for this bounded slice. Preserve draft status; no merge/deploy/issue closure.
