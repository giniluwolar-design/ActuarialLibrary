# EIOPA discount curves for 2026 Q2

Researched 25 September 2026. Scope: source evidence for discounting reserving cash flows at 30 June 2026. This report does not select the product's currency, volatility-adjustment policy, payment timing, or interpolation convention.

## Applicable release

EIOPA lists **June 2026**, published **3 July 2026**, in its monthly RFR releases. The reporting date is **2026-06-30**, distinct from publication or retrieval dates. EIOPA warns that technical information can be amended or republished. The separately listed financial-stability shifted curves serve duration reporting and should not be confused with the monthly base-curve release. [EIOPA RFR publication page](https://www.eiopa.europa.eu/tools-and-data/risk-free-interest-rate-term-structures_en)

The official [June 2026 archive](https://www.eiopa.europa.eu/document/download/ea4bf17e-aab3-431e-bc59-71cbdea9dd1a_en?filename=EIOPA_RFR_20260630.zip) was downloaded and its ZIP and workbook XML inspected read-only. It contains:

- `EIOPA_RFR_20260630_Term_Structures.xlsx`
- `EIOPA_RFR_20260630_PD_CoD.xlsx`
- `EIOPA_RFR_20260630_Qb_SW.xlsx`
- `EIOPA_RFR_20260630_VA_portfolios.xlsx`

Archive SHA-256: `80d5c4af0f4dd8f025103be4f746ae86d62f99a3c313c3024f4700a8965972fb`.

Term-structures workbook SHA-256: `1d7c280201255b22f8bcb12064ec421f8259c226f65ba892d1838ab07d3248f6`.

## Verified EUR identifiers and units

The term-structures workbook's column C is Euro. Its `C3` identifier is `EUR_30_06_2026_SWP_LLP_20_EXT_40_UFR_3.30` in both sheets below. Hence the identifier alone does **not** distinguish VA variants. [Official archive, term-structures workbook](https://www.eiopa.europa.eu/document/download/ea4bf17e-aab3-431e-bc59-71cbdea9dd1a_en?filename=EIOPA_RFR_20260630.zip)

| Property | `RFR_spot_no_VA` | `RFR_spot_with_VA` |
| --- | --- | --- |
| LLP, `C5` | 20 years | 20 years |
| Convergence period, `C6` | 40 years | 40 years |
| UFR, `C7` | 3.30 percent | 3.30 percent |
| Alpha, `C8` | 0.073103 | 0.05 |
| CRA, `C9` | 10 basis points | 10 basis points |
| VA, `C10` | blank | 14 basis points |
| Annual maturities | `B11:B160`, 1–150 years | same |
| Spot-rate values | `C11:C160` | same |
| One-year rate, `C11` | 0.02592 = 2.592% | 0.02732 = 2.732% |

Rates use decimal fractions and Excel format `0.000%`; UFR uses percentage units. Do not apply a single scaling rule to all numeric fields. Production-notes cell `E8` contains the stale date `2021-11-15`; it is unsuitable as the curve-date source. [Official archive, cells cited above](https://www.eiopa.europa.eu/document/download/ea4bf17e-aab3-431e-bc59-71cbdea9dd1a_en?filename=EIOPA_RFR_20260630.zip)

## Methodology and applicability

EIOPA's December 2025 technical documentation describes Smith–Wilson interpolation/extrapolation, integer maturities 1–150, EUR LLP 20, and convergence at `max(LLP + 40, 60)` years. Annual zero-coupon rates correspond to discount factors `D(t) = (1 + r(t))^(-t)`. Its continuous intensities are a separate representation. See sections 9.1–9.5 and Annex D. The VA is added to annualized basic zero-coupon rates through the LLP, then extrapolation is performed again; simply adding 14 basis points to every published maturity does not reproduce the adjusted curve. See section 15.1.2. [EIOPA-BoS-25-599 technical documentation](https://www.eiopa.europa.eu/document/download/f7fca58f-4d24-4441-ac60-de562bf26d77_en?filename=EIOPA-BoS-25-599+-+RFR+Technical+Documentation.pdf)

The applicable EUR UFR for 2026 is **3.30%**, although the calculated rate before the change limitation is 3.20%. The UFR is an extrapolation parameter, not a flat discount rate. [EIOPA UFR report for 2026, pages 3 and 6](https://www.eiopa.europa.eu/document/download/16f852f9-919d-49fe-a691-b9eb9e3285bd_en?filename=EIOPA-BoS-25-114-Report+on+the+Calculation+of+the+UFR+for+2026.pdf)

The updated documentation published in May 2026 applies **from 30 January 2027**. Publication before the reporting date does not make that future methodology applicable to this run. [EIOPA announcement, 26 May 2026](https://www.eiopa.europa.eu/eiopa-publishes-rfr-technical-documentation-become-applicable-30-january-2027-2026-05-26_en)

## Reproducibility implications

The following are engineering inferences from the distinctions above, not additional EIOPA requirements or product decisions. A saved discounting run needs:

- Valuation date, exact curve date, publication/revision date, retrieval timestamp, source URL and archive/workbook hashes.
- Currency, country column where relevant, sheet/variant, source curve identifier, and whether VA or any other adjustment applies.
- Original maturity/rate pairs and normalized units, compounding convention, LLP, UFR, alpha, convergence period, CRA and VA metadata.
- Payment dates or timing assumptions, year-fraction convention, interpolation method, sub-one-year treatment, and treatment beyond the supplied horizon.
- Calculation-library and parser versions, transformation record, and original source reference retained with the saved result.

The reporting date and currency do not by themselves answer whether the no-VA or with-VA curve is appropriate. A currency-wide curve and a country curve also need explicit identification. Cash-flow frequency is independent of curve frequency: monthly payments require a defined fractional-maturity method even though EIOPA publishes annual nodes. This report leaves those choices open. Published base and VA spot curves already include the relevant construction adjustments; downstream cash-flow valuation must not apply them a second time.

## Reuse and redistribution

EIOPA's current legal notice authorizes reproduction with source acknowledgement. Transformed and republished material requires an origin statement and non-endorsement/liability disclaimer. Sold documents must tell buyers the original is freely obtainable. Special tools and third-party material can have separate terms; logo use is separately restricted. This is not evidence that underlying vendor market data share the same permissions, nor that EIOPA material can be relicensed under this repository's software license. [EIOPA legal notice, copyright section](https://www.eiopa.europa.eu/legal-notice_en)

Source attribution: EIOPA — European Insurance and Occupational Pensions Authority, [official website](https://www.eiopa.europa.eu/).

This report was prepared using material downloaded from EIOPA's website. EIOPA does not endorse this publication and bears no liability for copyright or other intellectual-property infringement, or damages to third parties caused by this publication. Before public redistribution, reproduce the exact required disclaimer wording from the linked legal notice in the distribution's third-party notices.

## Verification boundary

Verified: official links, publication timing, archive hash/member list, workbook identifier, EUR cells, stored units and 150 nodes. No workbook was changed or recalculated, no curve was installed in the library, and no full market-data reconstruction or production numerical validation was performed. The temporary downloaded archive is not a committed project artifact. The parent task owns product decisions and handover updates.
