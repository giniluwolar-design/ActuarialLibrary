# EIOPA Discounting Conventions — Ticket #7 Research

**Status: LEAD REVIEWED 27 SEP 2026 — source research accepted with corrections below; product conventions selected for bounded implementation, not regulatory certification**
**Researched: 2026-09-27**
**Scope: discounting conventions for 30 June 2026 EUR EIOPA risk-free curve in reserving cash-flow valuation**
**Privacy: no local_runs/, data/private/, .env, credentials, or raw claims data accessed**

---

## 1. Curve identity — 30 June 2026 basic EUR EIOPA risk-free curve

| Field | Value | Source |
| --- | --- | --- |
| Reporting date | 2026-06-30 | EIOPA RFR monthly release, June 2026 |
| Currency | EUR (column C, term-structures workbook) | Verified from archive |
| Identifier (no-VA) | `EUR_30_06_2026_SWP_LLP_20_EXT_40_UFR_3.30` | Term-structures workbook, cell C3 |
| Identifier (with-VA) | `EUR_30_06_2026_SWP_LLP_20_EXT_40_UFR_3.30` (same cell C3; VA distinguishes variants) | Term-structures workbook, cell C3 |
| LLP | 20 years | Cell C5 |
| Convergence period | 40 years | Cell C6 |
| UFR | 3.30% | Cell C7 |
| Alpha (no-VA) | 0.073103 | Cell C8 |
| Alpha (with-VA) | 0.05 | Cell C8 |
| CRA | 10 bp | Cell C9 |
| VA | blank (no-VA) / 14 bp (with-VA) | Cell C10 |
| Maturities | Annual, 1–150 years, `B11:B160` | Verified |
| Spot-rate values | Decimal fractions, `C11:C160`, Excel format `0.000%` | Verified |
| One-year rate (no-VA) | 0.02592 = 2.592% | Cell C11 |
| One-year rate (with-VA) | 0.02732 = 2.732% | Cell C11 |

**No-VA default:** product discounting uses the no-VA curve. This is the decision in HANDOVER.md and review-2026-09-27-wave1-verdict.md #6-4.

**VA explicit option:** the VA curve is available as an explicit alternative; its source and adjustment are recorded in section 3.

**Sources:**
- EIOPA RFR publication page: <https://www.eiopa.europa.eu/tools-and-data/risk-free-interest-rate-term-structures_en>
- June 2026 archive: <https://www.eiopa.europa.eu/document/download/ea4bf17e-aab3-431e-bc59-71cbdea9dd1a_en?filename=EIOPA_RFR_20260630.zip>
- Archive SHA-256: `80d5c4af0f4dd8f025103be4f746ae86d62f99a3c313c3024f4700a8965972fb`
- Term-structures workbook SHA-256: `1d7c280201255b22f8bcb12064ec421f8259c226f65ba892d1838ab07d3248f6`
- Lead independently re-downloaded the official archive on 27 September; both hashes above matched. The prior workbook digest contained a transcription error.

---

## 2. VA variant — exact source and adjustment

The VA variant is the separate `RFR_spot_with_VA` sheet in the same workbook; the basic curve uses `RFR_spot_no_VA`. Both use EUR column C. Consume the chosen published curve directly, without adding VA or CRA again. The recorded adjustment is 14 bp in C10. Curve identity must include the sheet/variant, not just C3.

**Adjustment recorded:** VA = 14 bp added to annualized basic zero-coupon rates through LLP (20 years), then Smith-Wilson extrapolation re-performed with VA-adjusted rates. Source: EIOPA-BoS-25-599, section 15.1.2.

---

## 3. Day-count convention

**UNVERIFIED from primary EIOPA source.** The term-structures workbook publishes annual spot rates at integer maturities. The day-count convention for fractional maturities between published nodes is not stated in the verified archive or workbook cells.

**Correction:** a one-year rate is not a published sub-one-year rate, and cannot identify a date day-count convention by itself. 30 June to 30 September is 92 actual days, not exactly 0.25 under ACT/365F. No official fractional-date reference value has been established here.

**Lead product decision:** use ACT/365F for discount times, `t=(payment_date-valuation_date).days/365`. Record `ACT_365F` in each run. Payment frequency does not change this conversion. This is a transparent implementation convention, not an EIOPA-prescribed accounting rule. Mortality survival uses its separately recorded convention.

---

## 4. Interpolation convention — basic EUR curve

**Primary source citation:** EIOPA-BoS-25-599 RFR Technical Documentation, sections 9.1–9.5 and Annex D describe Smith–Wilson interpolation/extrapolation with integer maturities 1–150, EUR LLP 20, convergence at `max(LLP + 40, 60)` years.

**Lead verification:** the primary PDF is available; section 9.10.1 (page 51) gives the Smith–Wilson present-value function and sections 9.7–9.12 define its components. Reconstructing and validating that method from calibration data is separate from consuming the annual spot nodes. Absence of a verbatim quote does not make a mathematical method unverified; implementation equivalence requires numerical evidence.

**Fixture to confirm:** extract the Smith–Wilson calibration vector and Q-matrix from the workbook (if present) or reconstruct spot rates at non-published fractional maturities using the documented formula and compare against a reference implementation. The June 2026 archive's `EIOPA_RFR_20260630_Qb_SW.xlsx` sheet may contain the SW parameters.

**Published nodes:** EIOPA publishes annual nodes only (maturities 1, 2, …, 150 years). Fractional maturities require interpolation between these nodes. The workbench must define its fractional-maturity method as a product assumption; EIOPA does not publish fractional-node spot rates.

**Selected v1 product method:** log-linear discount-factor interpolation, labelled `log_linear_discount_factor_v1`; not a claim to reproduce EIOPA's continuous Smith–Wilson curve. At supplied integer node n, `D_n=exp(-n*log1p(r_n))`; anchor `D_0=1`. For t between adjacent n and n+1, `log D(t)=(1-w)log D_n+w log D_(n+1)`, `w=t-n`. This covers 0<t<1 using nodes 0 and 1. Do not linearly interpolate spot rates as an unrecorded alternative. Preserve every integer-node value. Reassess fractional approximation error before any regulatory-use claim.

---

## 5. Compounding basis and discounting

**As published:** annual effective rates. Spot rate `r(t)` at maturity `t` years corresponds to discount factor `D(t) = (1 + r(t))^(-t)` per EIOPA-BoS-25-599 sections 9.1–9.5.

**Use for payment dates:** derive T using section 3, obtain D(T) using section 4, then multiply each signed payment by D(T). Require finite source rates r>-1 and finite positive discount factors; negative rates are valid and D may exceed one. D(0)=1; negative maturities are rejected by the future-cash-flow API.

---

## 6. Extrapolation — Smith-Wilson to UFR

The published curve embeds the EIOPA Smith-Wilson extrapolation to the ultimate forward rate (UFR = 3.30% for EUR 2026). The convergence period is 40 years; the UFR is an extrapolation parameter, not a flat discount rate. The calculated rate before the UFR change limitation was 3.20%; the applicable EUR UFR for 2026 is 3.30%. Source: EIOPA UFR report for 2026, pages 3 and 6.

**Workbench consumption:** consume published nodes, which already incorporate EIOPA's extrapolation beyond the LLP. Interpolate within the published horizon using section 4. For t>150 return `OUTSIDE_CURVE_HORIZON`; no implicit UFR tail, flat-rate tail or Smith–Wilson reconstruction. The convergence region is not an extra node beyond 150.

**UNVERIFIED:** the exact SW extrapolation behaviour at maturities beyond 150 years (the published horizon endpoint) from the primary document text. The technical documentation describes the method; the specific numerical behaviour at extreme maturities needs verification against the documented formula.

---

## 7. Payment timing scenarios — explicit product assumptions

Payment timing is **not** a fact supplied by EIOPA. It is an explicit product assumption. Per review-2026-09-27-wave1-verdict.md #6-4:

- **Period-end dates:** used for the initial reserving schedule. This is the default timing assumption.
- **Mid-period (or other) timing:** available as an explicit optional scenario. Must be labelled as a product assumption, not attributed to EIOPA.
- **Primo vs ultimo:** primo = first day of calendar month/year; ultimo = last day. These are product definitions, not EIOPA conventions.

The exact timing scenarios (period-end, mid-period, primo, ultimo) and their mapping to discount dates are product assumptions recorded in the product specification, not EIOPA curve facts.

---

## 8. Unavailable nodes — F006 block rule

Per F006: unavailable nodes block discounting with a typed reason. No invented values are permitted.

- If a required discount factor cannot be computed from published nodes (missing curve, missing node, interpolation failure), discounting is blocked.
- The block reason is typed (e.g., `MISSING_CURVE`, `MISSING_NODE`, `INTERPOLATION_FAILURE`).
- An available curve may use the approved interpolation convention; a missing curve cannot be invented.
- The undiscounted schedule can still be produced independently of curve availability.

---

## 9. Source versioning fields

Each saved discounting run records:

| Field | Description |
| --- | --- |
| Publication reference | EIOPA RFR monthly release, June 2026 |
| Retrieval timestamp | Date/time the source was downloaded |
| Content hash | Archive SHA-256, workbook SHA-256 |
| Units | Decimal fractions, Excel format `0.000%`; UFR in percentage |
| Currency | EUR |
| Variant | `no-VA` or `with-VA` |
| Effective / valuation date | 2026-06-30 (reporting date), distinct from publication or retrieval date |
| Source URL | EIOPA RFR archive URL |

---

## 10. Discounted-to-undiscounted reconciliation check

**Lead correction:** `PV=sum(C_i*D(t_i))`; do not replace different payment dates with a single reference discount factor. The earlier proposed check is mathematically false in general.

- Undiscounted sum reconciles to the selected projectable reserve subset (#6).
- PV reconciles independently to the sum of row contributions and to origin/calendar subtotals, on identical included rows. Report the discount effect `undiscounted-PV` as a bridge, not an error.
- Under an all-zero curve, PV equals undiscounted cash flow. Mixed signs and negative rates mean PV need not be below the undiscounted value.
- For EUR use `max(0.01, 1e-12*sum(abs(contributions)))` as the amount reconciliation tolerance; synthetic unit discount-factor assertions use tight numeric tolerances (e.g. 1e-12). These are product engineering tolerances, not EIOPA requirements.
- Counterexample: 100 at t=1 and 100 at t=2 under a synthetic 10% flat curve gives PV=173.553719008264, versus undiscounted 200. No discount factor at the valuation date can reconcile them as equal.

Required new tests: exact source-node recovery; zero curve; signed flows; valid negative rates; 92/365 date conversion; leap-day date conversion; sub-one-year and interior log-DF interpolation; D(0); t>150; missing required node; missing/mismatched curve date/currency/variant; row and grouped totals; actual export trace with source and convention metadata. A missing node must not be silently bridged across a wider gap. Existing reserving tests do not validate this new engine.

---

## 11. Summary table of conventions and sources

| Convention | Value / Rule | Source | Verified? |
| --- | --- | --- | --- |
| Default curve | Basic EUR EIOPA no-VA, 30 June 2026 | HANDOVER.md, review #6-4 | Yes (product decision) |
| VA option | With-VA curve, 14 bp VA adjustment | HANDOVER.md, review #6-4 | Yes (product decision) |
| Curve identifier | `EUR_30_06_2026_SWP_LLP_20_EXT_40_UFR_3.30` | Workbook cell C3 | Yes |
| LLP / UFR / Alpha / CRA | 20y / 3.30% / 0.073103 (no-VA) / 10bp | Workbook cells C5–C9 | Yes |
| VA value | 14 bp (with-VA), blank (no-VA) | Workbook cell C10 | Yes |
| Maturities | Annual 1–150 years | Workbook B11:B160 | Yes |
| Rate format | Decimal fractions, `0.000%` | Workbook | Yes |
| Compounding | Annual effective, `D(t)=(1+r)^(-t)` | EIOPA-BoS-25-599 §9.1–9.5 | Yes |
| Interpolation | EIOPA construction: Smith–Wilson; workbench v1: log-linear DF | Primary PDF §9.10; lead decision §4 | Product approximation explicitly distinguished |
| Extrapolation | SW to UFR 3.30%, convergence 40y | EIOPA UFR report 2026; EIOPA-BoS-25-599 | Yes |
| Day-count | ACT/365F for workbench discount times | Lead product decision §3 | Not attributed to EIOPA |
| Payment timing | Period-end default; mid-period option | Product assumption (review #6-4) | Yes (product decision) |
| Primo/ultimo | Product definitions | Product specification | Product decision |
| Missing nodes | Block discounting, typed reason (F006) | F006 requirement | Yes (requirement) |
| Source versioning | Publication ref, retrieval timestamp, hash, units, currency, variant, valuation date | This research | Yes |
| Reconciliation check | Independent cash-flow and PV sums, discount-effect bridge | Lead correction §10 | Algebraic identity; new tests required |
| VA adjustment method | Added through LLP, then SW re-extrapolation | EIOPA-BoS-25-599 §15.1.2 | Yes |
| UFR applicability | 3.30% for 2026 | EIOPA UFR report for 2026 | Yes |
| May 2026 methodology update | Applicable from 30 Jan 2027 | EIOPA announcement 2026-05-26 | Yes |

---

## 12. UNVERIFIED items and confirmation fixtures

| UNVERIFIED item | What would confirm it |
| --- | --- |
| Fractional approximation error against Smith–Wilson | Independent comparison using published calibration data; required before regulatory-equivalence claims |
| Dates beyond supplied horizon | Unsupported in v1; separate specification and validation needed if later requested |
| Numerical and integration acceptance | Implement the new tests in §10; source research alone is insufficient |

---

## 13. References

1. EIOPA RFR publication page: <https://www.eiopa.europa.eu/tools-and-data/risk-free-interest-rate-term-structures_en>
2. EIOPA June 2026 archive: <https://www.eiopa.europa.eu/document/download/ea4bf17e-aab3-431e-bc59-71cbdea9dd1a_en?filename=EIOPA_RFR_20260630.zip>
3. EIOPA-BoS-25-599 RFR Technical Documentation: <https://www.eiopa.europa.eu/document/download/f7fca58f-4d24-4441-ac60-de562bf26d77_en?filename=EIOPA-BoS-25-599+-+RFR+Technical+Documentation.pdf>
4. EIOPA UFR report for 2026: <https://www.eiopa.europa.eu/document/download/16f852f9-919d-49fe-a691-b9eb9e3285bd_en?filename=EIOPA-BoS-25-114-Report+on+the+Calculation+of+the+UFR+for+2026.pdf>
5. EIOPA announcement, 26 May 2026: <https://www.eiopa.europa.eu/eiopa-publishes-rfr-technical-documentation-become-applicable-30-january-2027-2026-05-26_en>
6. EIOPA legal notice: <https://www.eiopa.europa.eu/legal-notice_en>
7. Project HANDOVER.md: `docs/project/HANDOVER.md`
8. Project review: `docs/project/review-2026-09-27-wave1-verdict.md`
9. Existing curve research: `docs/research-eiopa-rfr-2026q2.md`

---

*Reviewed source research plus explicit lead product decisions. No discounting code was implemented or certified by this document.*
