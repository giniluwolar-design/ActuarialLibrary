# Actuarial domain contract

## Data and methods

- Input: full claim snapshots with portfolio, unique claim number, loss/report/valuation dates, open/closed status, cumulative paid, outstanding case reserve, deductible, currency, and explicit amount basis. Closed previously reported claims remain in snapshots. Coverage records distinguish a complete zero-loss observation from unavailable history.
- Incurred = cumulative paid + case reserve. An additional supplied incurred field is for reconciliation, not an extra reserve component.
- Deductible is metadata only: do not subtract it automatically. Analyze different currencies and amount bases separately.
- Support annual origin × annual development and quarterly origin × quarterly development. Use completed calendar periods. Annual aggregation uses appropriate quarter-end snapshots, not sums of cumulative quarter balances.
- Keep zero, missing, and future cells distinct. Historical analyses must not access future observations or latent simulation outcomes.
- Paid/incurred Chain Ladder; paid/incurred Bornhuetter–Ferguson; frequency × severity. Default development factors are volume-weighted over available eligible pairs. Support unweighted estimates, historical windows, individual exclusions, explained overrides, and an explicit tail. A tail of 1 assumes no further development after the final age.
- Chain Ladder ultimate = latest observed basis × selected cumulative development factor (CDF).
- BF ultimate = observed basis + independently selected expected ultimate × (1 − 1/CDF). Invalid remaining shares block the BF calculation pending a valid pattern. The prior must not depend circularly on final method selection.
- Frequency × severity uses the ten preceding origin years by default, count-weighted or equally weighted annual average severities, and an explicit annual severity trend (default zero). Historical losses/counts develop to ultimate, by default incurred/count CL, with explained manual alternatives. Count assumptions may be developed, manual, or exposure × frequency. Using reported count alone explicitly assumes no further reporting. Quarterly targets calibrate severity using complete origin years.
- Missing history, factors, or priors yield explained unavailable results, never an invented zero. No hidden final method mix: users select a method or an explained manual ultimate per origin.

## Terminology and controls

Ultimate is total expected loss. Outstanding = ultimate − paid. Case reserve = incurred − paid. Additional reserve / IBNR + IBNER = ultimate − incurred. Outstanding from paid development includes case reserves.

Check duplicate keys, impossible dates, completeness, amount basis, reconciliations, and closed claims with case reserves. Show negative paid/reserve movements, factors below one, and negative reserve results; do not automatically remove them. Invalid denominators do not produce factors. Outlier flags invite investigation, not deletion. Show fitting membership, observation weights, and the effect of exclusions.

An assumption sensitivity is not a reserve movement between valuation dates. A true movement analysis requires the prior valuation data and assumptions. Distinguish measured change from a hypothesis about business causes.

## Verification and exports

The accepted foundation is Friedland's CAS reserving text, independent hand calculations, and pinned `chainladder` comparisons. Public reference triangles require source and license checks. Synthetic Motor/Liability examples cover fast/slow settlement, partial payments, late reports, reopenings, reserve changes, zeros, and large claims; latent future truth is separate test material.

Verify exclusions, tails, missing priors, zero versus missing, valuation boundaries, annual/quarter-end consistency, and historical information boundaries. Measure import, triangle construction, calculation, and memory separately before claiming speed improvements.

The worked Excel is a standalone, visible-formula educational example, with both portfolios and no macros, external connections, or hidden Python. It is not a workbook for arbitrary uploaded data. Reconcile it to the library within €0.01, observed counts exactly; check changed assumptions and visual output. Distinguish formula-engine checks from testing in native Excel.

Saved analyses should carry source hashes, valuation, filters, assumptions, selections, software version, and result identifiers. Reproducibility metadata is not an immutable audit log or formal approval system. Reports and supporting schedules should reference the same run. A download is complete only when an actual valid file exists; verify content and accessibility, not just a model's claim.

Initial exclusions: Mack, bootstrap, discounting, reinsurance, automatic deductible allocation, formal multi-user approval. Bootstrap needs a separately implemented and validated statistical method (residual treatment, negative increments, process/parameter uncertainty, tails, seed, convergence), never a language-model estimate.

## Roadmap and source pointers

Stabilize the reserving workflow first; then add EIOPA curves and specific DNB datasets as separate adapters with official sources, series definitions, units, revisions, retrieval timestamps and hashes. MCP can later expose the same validated functions. Revisit a faster spreadsheet-style modelling environment after learning from these modules. Do not discard the library merely to change the front end.

Repository references: `docs/methodology.md`, `docs/data_dictionary.md`, `docs/research.md`, `docs/verification.md`, `docs/roadmap.md`, and `THIRD_PARTY.md`.

- [Friedland, CAS](https://www.casact.org/abstract/estimating-unpaid-claims-using-basic-techniques)
- [chainladder methods](https://chainladder-python.readthedocs.io/stable/user_guide/methods.html)
- [chainladder development](https://chainladder-python.readthedocs.io/stable/user_guide/development.html)
