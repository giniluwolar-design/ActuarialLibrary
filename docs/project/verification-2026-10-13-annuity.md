# Independent synthetic annuity verification — 13 October 2026

Source: [draft PR #16](https://github.com/giniluwolar-design/ActuarialLibrary/pull/16), reviewed foundation `414ef6a`, initial engine head `7e8706865fe8567832d0b60caa4ec37877903299`. This record does not integrate the engine or close #8.

## Fresh installed-package check

Lead fetched the actual published source into an isolated managed checkout. First pytest collection failed because sandbox prevented creation of the test runtime directory; this was an execution setup failure, not a numerical counterexample. Re-run used a new synthetic database under `/private/tmp/annuity-verify.gl5YuT`, cache disabled, and the installed project interpreter:

```sh
ACTUARIAL_WORKSPACE_DB=/private/tmp/annuity-verify.gl5YuT/workspace.sqlite3 PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 /Users/tanikahuurman/Documents/FinancialAnalysis/.venv/bin/python -m pytest -q -p no:cacheprovider
```

At `7e87068`: **176 passed**, 123 dependency warnings, 47 subtests passed. No original workspace database or private claims were used.

## Independent numerical checks

A separate strong checker used daily enumeration and 45-digit Decimal survival references for 80 seeded calendar/factor cases: regular/fixed-partner factors; annual/monthly primo/ultimo dates; arbitrary commencement; birthdays/leap years; q=0/1; unequal/zero weights; negative-rate discount fixtures. Maximum PV difference: `2.22e-16`. No arithmetic counterexample found in this bounded check.

Additional checks: incomplete/missing/mismatched discount evidence retains undiscounted traces while blocking discounted factor; unsupported positive-weight mortality branches reject even subnormal weights; zero-weight branches need no coverage; coverage boundary is accepted without querying the next cell; non-leap century 2100 and `date.max` cases agree with independent references. Unequal partner weights yield 0.16443; regular factor 0.861 with injected DF 1.05.

## Findings and repair state

- Lead Ruff found 11 issues in the new modules/tests. Cloud owner repaired them at published `843099a2dc1157d994aac9e83d8ca1779806771f`. Lead read the repair diff and repeated changed-file Ruff: **all checks passed**. Numerical behavior unchanged; invalid-type exceptions now explicitly checked as TypeError, and intentionally rejected naive-datetime fixture retains a narrow documented lint suppression. Full suite at this repair: **178 passed**, 123 warnings, 47 subtests passed.
- Independent checker confirmed an explainability defect: regular results emitted fixed-partner eligibility/composition/lifetime/reversionary assumptions despite no partner input. Cloud owner repaired conditional actual-factor assumptions and added a matching regression at published `6598174d6e4ca7dd9f131ad81f98660abcd59789`. Lead read the repair diff and repeated changed-file Ruff: **all checks passed**. Full installed-package suite at this final engine head: **179 passed**, 123 warnings, 57 subtests passed. Lead also independently verified 30 June 2026 zero-mortality/unit-discount fixtures: monthly primo/ultimo each 0.5, annual primo 0 and annual ultimo 1; regular traces contain no partner assertions. Partner regression retains eligibility/composition/independence/contingency assumptions. No arithmetic code changed in the trace repair.

## Gates still open

One-case formula workbook, real AG source rights/data, whole-life closure, marriage-frequency/dynamic household semantics, API/UI integration, actual downloads and portfolio benchmarks remain unverified. No production/audit approval. The visual study in PR #15 uses authored fixtures, not these live modules. Founder visual preference remains pending.
