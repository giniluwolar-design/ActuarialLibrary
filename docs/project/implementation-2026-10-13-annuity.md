# Synthetic calendar annuity milestone — 13 October 2026

## Decided

Independent bounded implementation from corrected `annuity-factors-spec-v2.md`. Reviewed base: `414ef6ae83be9c5e9c4f0d0b5b071bac2ae56041`; source tree `87ce51f6fce01b1a8ec33ad98ecb0fcf3411adfc`. Separate branch `codex/synthetic-annuity-calendar-v2`. A cheaper Codex worker implemented two modules; the coordinating agent read/reviewed them, authored independent regressions and directed corrections. Root lead retains acceptance/integration review.

The newer vision has reserving and annuity as two top-level tools, progressive evidence, human judgement and labelled scenarios. Large-data performance remains a measured future requirement. The lead's independent three-direction visual prototype is untouched. Marriage-frequency and marriage/divorce/remarriage semantics are pending; no transition model, rates, eligibility or age gap invented.

## Source provenance and preservation

Real shell initially found clean older `work` at `fbd0dc13e5cb91f419fbf25ea593aca7ae7d752e`. Two Git fetches failed because configured proxy port 8080 was unreachable. Original documentation-only blocker branch/notes remain in `/workspace/ActuarialLibrary`.

The already-connected GitHub connector supplied the public commit metadata and complete recursive tree (`truncated=false`, 132 entries). Of the 106 blobs, 78 existed locally with matching object IDs, including unchanged synthetic Parquet/workbook fixtures; 28 missing text blobs were retrieved by exact SHA and independently rehashed. Rebuilt Git tree matched the reviewed tree SHA. The unsigned commit's exact raw object was recovered from public metadata with its original timezone/message termination and accepted only when its cryptographic hash matched the full reviewed commit. A separate Git worktree was created from that exact object. Ancestor history beyond the retrieved base is not a complete fetch; no full-history backup claimed.

No proxy/control changes, original-machine runtime database, private claims, credentials or hosted analyst fallback/tracing. The old offline task and its unpublished source were neither accessed nor reconstructed.

## Implemented

- `mortality.py`: frozen synthetic cells/source, strict finite qx validation, exact DOB, conditional survival at valuation, interval splitting at birthdays and 1 January, ACT/ACT-calendar exponents, explicit 29-February → 1-March common-year birthday policy. Zero/one mortality and zero-duration intervals behave explicitly. Missing coverage rejects the horizon, including after certain death; covered endpoint needs no next unsupported cell. q120 remains unchanged.
- `annuity.py`: independently callable real-calendar schedule with annual/monthly primo/ultimo dates, `valuation < payment <= horizon` and `payment >= commencement`, including already commenced benefits. Full annual-normalized instalments (1 or 1/12), no off-grid/prorated payments and zero indexation.
- Regular and fixed known-partner factors mix sex-specific results with explicit per-life weights. Partner probabilities are `(1-S_participant)*S_partner`; composition and lifetime independence disclosed separately. Both DOBs required for partner factors. All positive-weight life/sex branches require coverage even when a pair product underflows to zero.
- Injected materialized dated discount factors carry valuation/source/label/day-count evidence; missing, mismatched or incomplete evidence blocks discounted factor while retaining mortality and undiscounted contingency traces. No curve invented or real EIOPA result claimed. Immutable output snapshots preserve used mortality cells, intervals, branch composition, payment weights/survivals/probabilities/benefits/DF/PV, residual survival and assumptions. Results explicitly labelled synthetic/truncated.
- No changes to existing public exports, server, models, web, graph, projection, discounting or reserving. No persistence/graph pagination adapter or browser workflow added.

Public seams: `MortalityCell`, `MortalitySource`, `attained_age_on`, `survival_trace`; `DiscountFactorEvidence`, `payment_dates`, `calculate_annuity`. Modules use standard library only. Source IDs are supplied provenance, not externally authenticated identities; immutable Python values are inspectable snapshots, not an audit store.

## Verified

36 focused unittest cases in `tests/test_synthetic_annuity_v2.py` pass under isolated loading of the two real modules. This bypasses unrelated reserving imports in package `__init__` without mocking calculation functions; it is numerical/module-seam verification, not a successful installed-package integration check.

- Independent 50-digit Decimal arithmetic reproduces all six published grid literals within 1e-12: annual male 2.819527104960; female 2.832315809756; 50/50 2.825921457358; monthly per-instalment 11.842812103818; annual-normalized 0.986901008651; partner 0.095948830798. The old monthly-primo literal includes t=0 on an equal-offset grid; it is deliberately not substituted for a real-calendar result after valuation. Calendar-aligned annual cases separately exercise the engine against the regular/partner literals.
- Independent daily reference exercises different birthdays, year transitions and leap year through monthly partner payments with a synthetic negative-rate discount fixture. Separate literal payment-date/exposure checks protect annual-benefit normalization, per-life mixture and PV reconciliation.
- Edge cases: Jan-1/midyear DOB, leap/nonleap leap-day birth, 181/184-day split, 365/366 denominator, conditional valuation, q0/q1, q120/residual survival, unsupported horizon even without payments, zero/nonzero/subnormal weights, fixed-partner DOB/coverage, same-day cutoff, historical commencement, off-grid horizon, date.max, duplicate cells/discount dates, immutable input snapshots, unavailable/mismatched discount evidence, nonfinite/oversized numeric rejection and factor overflow.
- Review reproduced string-q acceptance, an uncontracted historical-commencement rejection and subnormal pair-weight coverage bypass; implementation repaired, focused regressions now green. Syntax compilation and `git diff --check` pass.

To reproduce module checks in this dependency-limited runtime:

```bash
python - <<'PY'
import importlib.machinery, importlib.util, sys, unittest
from pathlib import Path
spec = importlib.machinery.ModuleSpec('actuarial_library', loader=None, is_package=True)
spec.submodule_search_locations = [str(Path('src/actuarial_library').resolve())]
sys.modules['actuarial_library'] = importlib.util.module_from_spec(spec)
suite = unittest.defaultTestLoader.discover('tests', pattern='test_synthetic_annuity_v2.py')
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(0 if result.wasSuccessful() else 1)
PY
python -m py_compile src/actuarial_library/mortality.py src/actuarial_library/annuity.py tests/test_synthetic_annuity_v2.py
git diff --check
```

## Blocked / next

Normal `PYTHONPATH=src python -m unittest discover -s tests -p test_synthetic_annuity_v2.py` currently fails importing existing package initialization because Polars is absent. Pytest and Ruff also absent; dependency installation via unavailable shell proxy was not attempted. Lead must rerun focused and full suite plus changed-file Ruff in an installed environment before integration. Existing historical 140-test report is not fresh evidence for these changes.

One-case formula workbook, API/download, graph persistence/pagination, visual acceptance and model reliability remain unverified/outside this ownership. No whole-life or real-AG result, performance benchmark, production/audit certification, unlimited execution or phone push claim. Source-rights and marriage semantics remain later lead gates.

Next delivery step is supported GitHub API publication with exact tree/ref read-back, then draft PR for source/actuarial review against the reviewed foundation. Shell Git push remains blocked. Do not merge, deploy or close issues.
