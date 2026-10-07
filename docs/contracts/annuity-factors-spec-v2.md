# Annuity Factors Specification v2 — LEAD CORRECTED 27 SEP 2026

**Ticket:** #8 Annuity factors — REJECTED current spec, retained product direction
**Supersedes:** `docs/project/review-2026-09-25-wave1.md` section 3 draft (conflicting recommendations superseded by the 27 September 2026 verdict)
**Status:** Approved for a synthetic finite-horizon implementation and independent reference tests under the lead corrections below. Whole-life and real-AG release remain unapproved; new feature evidence is required.
**Privacy:** synthetic values only; no real AG mortality tables anywhere

---

## 1. Contract position

This replacement specification permits bounded synthetic implementation. It does not certify implementation or close ticket #8. The calendar and survival examples below must become independently checked tests before integrating factors into the workbench.

---

## 2. Definitions and scope

- **Regular factor:** payments while the participant is alive.
- **Partner factor (reversionary):** payments to a known partner starting after participant death while the partner lives. Payment at time t requires partner alive at t AND participant dead at t.
- **Unisex:** source mortality stays sex-specific; unisex factors are mixed explicitly with adjustable weights, default 50/50 per life, recorded in provenance.
- **Basis:** AG2024 is the as-known-at-30-June-2026 table; AG2026 only as a labelled retrospective scenario (ingestion spec governs).
- **Scope assumptions:** both lives or dates of birth required; no invented partner age gap; fixed eligible partner; both initially alive; unit partner benefit; no remarriage/eligibility changes.

---

## 3. Decision A — factor-space mixing (adopted as product convention)

Compute sex-specific factors and weight them. Do not claim a universal pension convention without supporting evidence. Averaged qx and averaged survival are different constructions; neither is justified merely by calling one arithmetic and the other geometric.

- ä_unisex = w_m · ä_male + w_f · ä_female, w_m + w_f = 1
- Per-life weights: default 50/50 each life, independently adjustable
- Product of per-life weights w_a(s_a) · w_p(s_p) disclosed as a composition-independence assumption alongside the separate independent-lifetimes assumption
- Known-sex branches are calculation traces/tests, not a silent UI default

---

## 4. Decision B — explicit finite horizon, no artificial death

- Replacement draft must start with an explicitly finite horizon ending **no later than** the first unsupported age or year for either required life.
- Residual survival exposed at that horizon.
- Result labelled **truncated**, not whole-life.
- q120 retained unchanged (supplied qx value preserved; never forced to zero or one).
- Any whole-life closure/extension is a separate explicit actuarial assumption needing sensitivity evidence and later review.
- **No artificial participant death** that would create partner benefits.

---

## 5. Decision C — injected discount-factor dependency

- Discount curve is an injected dependency with curve provenance.
- Product default: reporting-date 30 June 2026 basic EUR EIOPA without VA; explicit VA option recorded with exact source.
- Missing curve blocks discounted factors; survival trace can still be inspected.
- Synthetic flat-rate test curves are clearly labelled fixtures, never presented as real curves.

---

## 6. Decision D — factor-result node and traceability

- Factor-result node references immutable payment-trace blocks, mortality source, discount source and assumptions.
- Trace each payment date, sex pair/weight, survival, contingency probability, benefit, discount factor and PV contribution.
- Keep #4's paginated pattern (L0 summary → L1 node adjacency → L2 trace blocks); do not embed every term in L1.

---

## 7. Calendar payment dates and reporting cutoff

### 7.1 Actual calendar dates

Payment dates are real calendar dates, not k/m offsets from an arbitrary origin.

- **Primo:** first calendar day of the payment period.
- **Ultimo:** last calendar day of the payment period.
- **Reporting-date cutoff:** after that day's payments are counted; future payments are strictly later. Any alternative same-day convention must be explicit.

### 7.2 Benefit commencement

Benefit commencement is a required input separate from valuation. V1 pays the full 1/m instalment on the first scheduled calendar date on or after commencement and strictly after valuation, contingent on survival/eligibility then. No off-grid payment or first-period proration. State this rule in the trace; contracts requiring pro-rata accrued payments need a separate later option.

### 7.3 Default factor normalisation

Default factor is quoted per 1 unit of annual benefit: payments are 1 for yearly, 1/12 for monthly instalments. If a per-instalment factor is offered, it is labelled separately as such (per-instalment amount, not annual equivalent).

### 7.4 Endpoint inclusion

Include scheduled dates satisfying `valuation < payment_date <= horizon` and `payment_date >= commencement`. No extra payment is inserted at an off-grid horizon. Horizon cannot exceed the earliest end of supplied age/year coverage for any required sex/life branch with nonzero weight. At that boundary survival uses the covered intervals up to the boundary; never query an unsupported next cell or force death.

---

## 8. Attained-age and calendar-year cohort extension

### 8.1 Splitting rule

Attained-age and calendar-year cohort extension splits at birthdays **and** calendar-year boundaries. Constant force within each (age, year) cell is an implementation convention for arbitrary DOBs, not uniquely prescribed by the official reference-life definition.

### 8.2 Actual-day year fractions

Survival over fraction u of a cell uses `(1-q)^u`. Split at birthdays and 1 January, then use `u=actual_segment_days / days_in_that_calendar_year` (365 or 366). This is the product's ACT/ACT-calendar survival convention, recorded separately from the discount day count. Handle q=0 and q=1 explicitly without log-domain errors; a positive-duration q=1 interval yields zero survival and a zero-duration interval contributes one. Survival is conditional on each life being alive at valuation.

### 8.3 Leap-day birthday policy

Product leap-day convention: a life born 29 February ages on 1 March in non-leap years. This is a selected product convention, not a claim of a universal actuarial standard.

### 8.4 Worked examples (synthetic)

Required before acceptance:

1. **1 January birth date** — anchor case where attained age and calendar year advance together on 1 January.
2. **Mid-year birth date** — actual-day fractions on either side of the birthday; not assumed half-cell exponents.
3. **Leap-year case** — 29 February birthday behaviour across leap/non-leap year boundaries.

Independent reference fixtures to implement:

- From 1 January 2027 to 1 January 2028 for a 1 January birthday and q=0.10: S=0.9.
- For a 1 July birthday, from 1 January 2027 to 1 January 2028 with q=0.10 before birthday and 0.20 after: S=0.9^(181/365) * 0.8^(184/365).
- From 28 February 2028 to 1 March 2028 for a 29 February birthday, q=0.10 before and 0.20 after: S=0.9^(1/366) * 0.8^(1/366). In 2027 the analogous interval ends at the 1 March birthday and uses 0.9^(1/365).
- Valuation 30 June 2026, commencement 1 July, horizon 31 December: monthly-primo dates 1 July through 1 December; monthly-ultimo dates 31 July through 31 December; each amount 1/12. Annual-primo has no date in that interval; annual-ultimo has 31 December with amount 1. No fabricated 30 July date.

Exact DOB is required for arbitrary-date calculations. Age-only demo input may construct an explicitly displayed synthetic 1 January DOB; do not imply an exact actual DOB from integer age.

---

## 9. Factor inequalities and endpoint identities

### 9.1 Rejected frequency ordering

The draft's universal frequency ordering is removed. On an aligned common horizon with equal annual benefit and a decreasing discounted survival function, the useful synthetic inequality is:

**annual-primo ≥ monthly-primo ≥ monthly-ultimo ≥ annual-ultimo**

This is not universal under negative rates/indexation or increasing reversionary probabilities. Tests must be specific condition tests, not an unconditional product rule.

### 9.2 Primo-minus-ultimo identity

The primo-minus-ultimo endpoint identity applies to **shifted grids with identical intervals and benefit function**; it is not universal for calendar schedules with different cutoffs.

---

## 10. Indexation and domain

- Indexation **zero** for the initial workflow.
- If implemented later, constant g requires finite g > −1. The proposed −5%/+10% limits are arbitrary and must not reject otherwise valid inputs without a product reason. Any warning band is a review aid, not a mathematical domain.

---

## 11. Module split and factor engine

- Workbook ingestion → `mortality.py` (ticket #9)
- Factor arithmetic → `annuity.py`
- Calendar schedule logic → separately testable function, no I/O in the factor engine
- One-case formula-workbook validation retained as a release requirement

---

## 12. Worked examples — independent verification required

All examples are synthetic, truncated grids, not general date engine or AG factors. Independent calculation required:

| Example | Value |
|---|---|
| Annual male | 2.819527104960 |
| Annual female | 2.832315809756 |
| Mixture (50/50) | 2.825921457358 |
| Monthly per-instalment mixture | 11.842812103818 |
| Monthly per-instalment, annual-normalised | 0.986901008651 |
| Partner (annual ultimo) | 0.095948830798 |

Verification method: independent read-only Python snippet using the synthetic qx values stated in the original draft (male 65–67: 0.0100/0.0120/0.0140; female 0.0080/0.0096/0.0112; participant male 68: 0.0160/0.0180/0.0200; i = 2%, g = 0, t0 = 1 Jan 2027, 3 terms). All five values reproduced exactly (diff < 1e-12).

---

## 13. Marking and review requirement

**LEAD CORRECTED — SYNTHETIC IMPLEMENTATION AUTHORIZED**

Integrate only after independent calendar, survival, factor and one-case workbook checks. This document supersedes conflicting recommendations in the 25 September draft; it does not certify implementation or close the ticket.
