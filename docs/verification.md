# Verification record

Implementation checks performed on macOS 15.7.4 (Apple Silicon), Python 3.12.4. Last local verification: 17 September 2026. This records observed checks, not a certification or actuarial approval.

## Library and application

- 17 automated tests passed. They cover independent hand calculations, RAA Chain Ladder and BF against `chainladder==0.8.26`, factor choices, tails, frequency–severity, missing priors, invalid BF patterns, reserve identities, missing versus zero observations, snapshot completeness, historical cutoffs, annual/quarterly reconciliation, drilldown, export and app invalidation after assumption changes.
- Ruff passed. Third-party NumPy/chainladder deprecation warnings remain; no test failed.
- Both synthetic portfolios completed the API example and produced ZIP exports.
- Source distribution and wheel built successfully. The wheel was installed into an empty target directory and both portfolio examples ran from that installation, using dependencies already installed in the local virtual environment. This is not an independent clean-machine dependency installation.
- The running local app was opened in a browser and the Liability annual analysis calculated successfully. Results are deliberately marked incomplete until a user selects final methods for every origin.
- The GitHub Actions configuration covers installation, tests and build on Windows, Linux and macOS. Those remote jobs have not been executed here. Independent README usability testing by another person is still pending.

## Worked Excel

The standalone workbook contains ten sheets and 47,415 visible formulas. All ten sheets were rendered and visually inspected during authoring. The saved XLSX contains no error cells or external links.

Ten recalculation comparisons passed: Motor and Liability, each with baseline assumptions, changed severity trend, simple severity averaging, changed factors/tail and a zero expected-ultimate prior. Workbook formula results were compared with library results to a monetary tolerance of EUR 0.01. Recalculation used the spreadsheet authoring engine; the workbook does not need that engine to be used in Excel.

A temporary copy opened in Microsoft Excel without a repair prompt. The installed Excel account permits viewing but not editing on this Mac. Consequently, assumption edits and full recalculation inside Microsoft Excel itself could not be independently verified. This acceptance check remains open and must not be inferred from the authoring-engine comparisons. The original deliverable was not changed during that check.

## Performance

See [measured values](benchmark.json). One run per size, warm filesystem caches possible; generation excluded. Peak memory is sampled total-process RSS, not an isolated estimate of triangle memory.

| Snapshot rows | Import | Validation + triangles | Reserving | Peak process RSS |
|---:|---:|---:|---:|---:|
| 159,176 | 0.0147 s | 0.2969 s | 0.0033 s | 317.7 MB |
| 795,538 | 0.0073 s | 0.8274 s | 0.0022 s | 964.9 MB |

These measurements do not establish a general speed advantage over Excel. The smaller reserving time at the larger size is consistent with reducing claims to the same annual triangle dimensions; import cache effects also matter.

## Remaining release checks

1. Run the checked-in CI matrix on all three operating systems.
2. Recalculate and change assumptions in an editable Microsoft Excel installation; confirm the saved results against the library.
3. Have another user install and operate the demo using only the README.

GitHub publication and a public web demo remain separate actions.

## Actuarial workspace update

18 September 2026: the simplified three-step workspace passed 23 automated tests, including missing/zero factor cells, valuation-specific outlier screening, report values and re-import of the generated synthetic test ZIP. A live browser session with local Gemma created a real Markdown report through `create_artifact` and displayed its download. The AI narrative still needs review: it may overstate report contents, so the UI separately lists the actual file contents. The factor triangle uses fixed colour bands, not statistical significance colouring. Data inspections and advanced assumptions are collapsible; the AI panel remains alongside the workflow.

The observation review was tested against fitting membership, exclusions, historical windows, invalid denominators and same-data assumption impacts. The redesigned app was browser-inspected and its calculation/invalidation test passed. It includes keyboard-friendly exclusion selection alongside the editable grid; this is not a claim of a full accessibility compliance audit. The local Gemma connector was exercised against `gemma4:latest` with synthetic data: Gemma called a scenario tool and returned an evidence-linked explanation. Bootstrap and new report formats were not added in this update.
