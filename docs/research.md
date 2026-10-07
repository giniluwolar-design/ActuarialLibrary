# Research basis for an explainable reserving library

## Findings and design implications

The requested tool is feasible with established reserving methods and standard local software. Its main contribution is not a new estimator: it makes the input contract, exclusions, expectations and explanations travel together. The first release deliberately concentrates on point estimates and inspectable arithmetic. The research identifies three areas where interface convenience must not obscure actuarial meaning: historical information availability, expected ultimate assumptions and the definition of reserve outputs.

This note is a technical design review for a demonstration library, not an assessment of any particular insurer's reserves. The source literature is relevant to the mathematical techniques. It does not establish that a specific method is suitable for an unexamined portfolio or that this release meets a particular jurisdiction's reporting requirements.

## Sources and evidence

Friedland's CAS text brings the basic reserving techniques into a common terminology and provides comparable examples. Chapters 5–7 cover triangles and development, chapter 9 covers Bornhuetter–Ferguson, and chapter 11 covers frequency–severity approaches. The discussion supports treating expected counts and average cost as explicit assumptions, particularly for young years, while considering trends and a consistent claim population. It also describes how changes in reporting, settlement and reserve strength can disturb historical patterns. [1]

The maintained `chainladder` documentation exposes factor averaging, historical-period selection and exclusions. Its method guide defines paid and incurred estimators and explicitly notes that the package's `ibnr_` attribute on paid triangles includes case reserves unless the caller separates them. This motivates explicit output labels in this project. Its sample data and executable estimators make a useful independent implementation comparison; they are not proof of suitability for the fictitious portfolios or client portfolios. [2–4]

The CAS provides a claim-level loss simulator covering transaction fitting and claim-level reserving. This demonstrates that synthetic data can be organised around claim lifecycles rather than generating only aggregate triangles. The current demo follows that conceptual distinction but does not copy, fit or validate itself against the CAS simulator's code or parameters. [5]

Polars documents a lazy execution API and query optimisations. Streamlit documents editable tabular controls. These capabilities support the proposed local architecture, but neither provides an actuarial correctness guarantee or a measured speed advantage for this application. [6–7]

## Historical data is part of the model

A current claims extract alone cannot reconstruct case reserve estimates at earlier valuation dates. Reconstructing past incurred from today's reserve would leak later information and change the implied development pattern. A robust input therefore needs historical snapshots or a sufficiently complete transaction/reserve-event ledger. This implementation chooses snapshots to make the first public contract inspectable.

Full snapshots introduce an easily overlooked obligation: closed claims must remain represented. Otherwise a disappearance might be interpreted as a reduction in cumulative paid or reported count. The tool compares persistence across complete snapshots and rejects contradictions. This is a consistency check, not proof that the first snapshot contained the entire population.

Coverage is a separate source assertion. A complete empty group can mean zero; the absence of a file does not. Keeping these concepts separate also makes genuine outages visible in a triangle. The quarterly-to-annual operation takes year-end balances. Adding four quarterly cumulative balances would count the same payment multiple times.

## Method comparisons are conditional comparisons

Comparing paid CL with incurred CL is useful because the methods respond to different observed quantities. Agreement is not an independent validation when both share the same data weaknesses. A sudden case-reserve strengthening may change incurred patterns even when settlement cash flows do not change. A settlement acceleration may change paid patterns without changing lifetime claim cost.

The app therefore exposes the selected factors and contributing observations. It does not automatically select the estimate closest to another method. Outlier exclusions require explanation and remain in the exported configuration. A factor override changes the model assumption; the record should preserve that decision instead of making the new factor look mechanically estimated.

Bornhuetter–Ferguson is implemented with an explicit prior and a remaining-development share. Calling it simply a fixed midpoint between methods would misdescribe the calculation. The relative role of observed and expected amounts changes with development. This project separates prior construction from the final selection to prevent circular justification.

## Ten years of severity: useful convention, not universal truth

The requested ten-year average is made a selectable calibration window. It is not hardcoded as a universal optimum. Older experience may add credibility but may reflect a different business mix, policy limit, claim definition or price level. Recent immature years need explicit development assumptions before being compared as ultimate costs.

A claim-weighted severity answers a pooled-claim question; equal weighting of annual severities gives each year's experience the same influence. They differ when annual claim counts vary. The user can inspect both. Trend is an explicit annual assumption, with the target year's price level clearly identified. Defaulting to zero is a transparent baseline, not a statement that actual claims inflation is zero.

Expected target count is also a model input. Reported count is not automatically ultimate count. The tool requires confirmation before treating it as complete, and offers developed counts, manual expected counts or exposure multiplied by frequency. Counting reopened claims again would distort the denominator, so identifiers remain stable.

## Interpretation of the synthetic examples

Motor and Liability are illustrative labels for different settlement speeds. They are not calibrated country, product or company benchmarks. Lognormal severity, selected large claims, reporting delays and temporary closures make the workflow realistic enough to exercise the controls. They do not reproduce all dependencies, calendar effects or catastrophic clustering in real portfolios.

Latent outcomes are stored separately in memory for tests and are not exported as claims input. Knowing a synthetic ultimate makes it possible to evaluate an experiment, but using that ultimate in an earlier fitting dataset would defeat the experiment. The standard demonstration has no access to that separate truth table.

The data's finite simulated development horizon should not be interpreted as empirical support for a unit tail in real long-tail business. A tail of one is exposed as an assumption, and a different tail requires a note. Uncertainty about tails remains outside deterministic point estimates.

## Verification strategy and its limits

Hand examples establish arithmetic identities. The RAA comparison checks the implementation against a separately maintained package with aligned settings. Snapshot tests exercise the data contract and prevent common balance-aggregation mistakes. UI tests verify that changed assumptions do not silently retain exportable old results. Excel checks establish an independently inspectable formula path from the example inputs.

These checks are complementary. Matching another implementation does not establish the adequacy of input data, the appropriateness of a prior, or the stability of an actual portfolio. Passing a synthetic example cannot establish predictive performance on future company experience. This release therefore reports checks performed and limitations separately from business conclusions.

Before applying the library to a client dataset, map its exact amount and count definitions to the contract and reconcile with source-system totals. Later development should add genuine historical holdout exercises, without changing fitted assumptions after observing the holdout and calling that an independent test.

## Architecture assessment

The highest-volume work is reading, validating and grouping claim history; the fitted triangle itself is usually much smaller. Separating these stages permits useful benchmarks and cached UI exploration. Replacing the full application with a low-level language before profiling would not necessarily improve the workflow.

The proposed Python interface keeps the numerical operations modular and makes it possible to replace slow internal operations later. JSON configuration and typed results also provide a natural boundary for a future MCP server. The chat interface should call deterministic library operations and cite their output, rather than perform a second undocumented version of actuarial calculations.

The worked Excel is a teaching and review artifact. Its fixed source ranges and selected annual example are intentional. General-purpose spreadsheet authoring, arbitrary workbook compatibility and formula export for every possible future method would be a much broader project.

## Source inventory

1. Jacqueline Friedland, Casualty Actuarial Society. *Estimating Unpaid Claims Using Basic Techniques* (2009; syllabus listing 2010). Chapters 5–7, 9, 11. [Publication](https://www.casact.org/abstract/estimating-unpaid-claims-using-basic-techniques), [full text](https://www.casact.org/sites/default/files/database/studynotes_friedland_estimating.pdf). Historical mathematical reference; not current jurisdictional guidance.
2. Chainladder Python. *Development*, stable documentation, accessed 14 September 2026. [Link](https://chainladder-python.readthedocs.io/stable/user_guide/development.html). Factor averages and selection controls.
3. Chainladder Python. *IBNR Models*, stable documentation, accessed 14 September 2026. [Link](https://chainladder-python.readthedocs.io/stable/user_guide/methods.html). Estimator definitions and paid reserve terminology.
4. Chainladder Python. *Working with Triangles* and source repository, accessed 14 September 2026. [Tutorial](https://chainladder-python.readthedocs.io/stable/getting_started/tutorials/triangle-tutorial.html), [repository](https://github.com/casact/chainladder-python). RAA sample and MPL-2.0 package; executable benchmark pinned to 0.8.26.
5. Casualty Actuarial Society. *Loss Simulation Model and Documentation*, accessed 14 September 2026. [Link](https://www.casact.org/publications-research/research/loss-simulation-model-and-documentation). Claim-level simulation reference.
6. Polars. *Lazy API*, accessed 14 September 2026. [Link](https://docs.pola.rs/user-guide/concepts/lazy-api/). Execution architecture reference.
7. Streamlit. *st.data_editor*, accessed 14 September 2026. [Link](https://docs.streamlit.io/develop/api-reference/data/st.data_editor). Editable UI controls.

No real client data was supplied. Sample portfolios and application design decisions are original demonstrations. Website documentation is mutable; the executable environment is separately recorded in constraints and the verification report.
