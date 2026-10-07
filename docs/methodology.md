# Reserving methodology

## Definitions and calendar

For origin i and development age j, P is cumulative paid, R is remaining case reserve, and C = P + R is reported incurred. Age one is the end of the origin calendar year or quarter, not a fixed number of months from the individual accident date. No unfinished calendar periods are fitted.

The latest diagonal is the selected valuation date. If that observation is missing, the calculation does not fall back to an earlier balance. Differences of cumulative observations are incremental amounts; a difference spanning a missing observation is unavailable. Incurred increments include revisions of reserve estimates and are not cash flows.

## Chain Ladder

For each development transition, eligible origin pairs have both observations available and a strictly positive starting balance. User exclusions apply first. The optional window keeps the newest eligible pairs, not necessarily consecutive calendar origins.

- Volume factor: sum of subsequent balances / sum of starting balances, for the same eligible origins.
- Simple factor: arithmetic mean of the eligible individual subsequent/starting ratios.
- Selected factor: explicit positive override, otherwise the selected averaging method.
- CDF at age j: product of subsequent selected factors, including the explicit tail.
- Ultimate: latest observed balance × CDF at its age.

Factors and CDFs are not rounded before use. An invalid denominator, no eligible pairs, or a nonpositive factor produces an unavailable result unless an explicit valid override supplies the missing assumption. Factors below one are retained with diagnostics. The tail is at least one in v0.1 and defaults to one.

The package stores pair counts and included origins with each factor. Exclusions and manual factor/tail changes require an explanation. Changes in case-reserving practice particularly affect incurred development; changes in settlement timing affect paid development. A long history does not by itself establish a stable pattern. Method sources and implementation comparisons are listed in [research](research.md).

## Bornhuetter–Ferguson

Let E be an independently specified expected ultimate and F the CDF for the chosen paid or incurred basis. The remaining share is 1 − 1/F. BF ultimate is the observed balance plus E times that share. Paid and incurred use their own development patterns.

E may be a manual value per origin or the frequency–severity estimate described below. A literal zero is a valid manual prior; a blank requests the calculated prior. The final selected ultimate never feeds this calibration. BF requires F >= 1, finite observations and an available prior. An invalid remaining share is not clipped into a valid-looking proportion.

## Frequency × severity

Each target origin uses selected calendar years strictly before its own year, within the lookback window (ten years by default). Fewer early years may be available and their actual labels are displayed. No usable prior years means an unavailable result. A selected year with unavailable amounts or nonpositive ultimate counts invalidates the calibration; it is not silently dropped.

Historical ultimate incurred amounts and ultimate reported counts come from separate CL calculations, unless explicitly overridden with a rationale. For quarterly inputs, all four origins of a historical calendar year must be available before their ultimates and counts are summed. Historical yearly severity is ultimate amount / ultimate count.

Each yearly severity is trended by (1 + annual trend) raised to target year minus historical year. This is an accident-year price-level convention, not payment-date inflation modelling. The default trend is zero. Weighted severity uses ultimate claim counts as weights; simple severity weights calendar years equally.

Target ultimate count comes from count CL, a manual expected count, exposure × expected frequency, or observed reported count with explicit confirmation that no further reporting is assumed. Exposure and frequency must refer to the same population and period. Quarterly target counts are quarterly counts. No implicit annualisation is performed.

Ultimate = selected severity × target count. Reopened claims keep the same identifier and are not counted again. Zero-payment claims remain in the reported claim population; severity and expected count must use this same definition. Mixing paid-only counts with all-reported severity would be inconsistent.

## Final selection and reserves

The UI presents method indications without a preselected final answer. A user may choose a method per origin or enter a manual ultimate and explanation. A selected unavailable method is rejected. Partial selections are shown as incomplete; their sum is not labelled as a complete portfolio reserve.

For any ultimate U, outstanding = U − P, case reserves = C − P, and additional reserve = U − C. The latter combines IBNR and IBNER under this aggregate framework. It does not separately identify genuinely unreported claims and future changes on known claims. Negative additional reserves can represent expected releases and are shown with diagnostics, not silently floored.

## Reproducibility and limitations

Exports contain exact configuration, source hashes, valuation, filters, software version, execution time, factors, calibration and outputs. A source hash identifies the supplied file content; it neither proves source correctness nor creates a signed audit trail. Notes record judgements but do not implement reviewer permissions.

The methods are deterministic. There is no prediction interval, discount curve, risk adjustment, reinsurance engine, formal accounting conclusion or regulatory certification. Synthetic truth is never made available to historical fits. Backtesting should use earlier snapshots and compare with later outcomes without retrospectively tuning and relabelling the same test as independent.
