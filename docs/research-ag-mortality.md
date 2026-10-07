# AG mortality tables: verified source research

Research date: 25 September 2026. Scope: official Koninklijk Actuarieel Genootschap (AG) sources only; no product decisions or calculation implementation. The research skill was used. Public workbooks were inspected in memory; no source workbook was added to the repository.

## Availability and reporting-date timing

Both requested editions exist. **Prognosetafel AG2024 / Projections Life Table AG2024** was published on 12 September 2024. Its official page publicly links the English PDF, a parameters/best-estimate mortality XLSX, and a separate calibration dataset XLSX. [AG2024 publication](https://www.actuarieelgenootschap.nl/kennisbank/projections-life-table-ag2024-1)

**Prognosetafel AG2026 / Projections Life Table AG2026** was published on 8 September 2026. Its official page publicly links Dutch and English PDFs, a parameters/best-estimate mortality XLSX, and a separate calibration dataset XLSX. [AG2026 publication](https://www.actuarieelgenootschap.nl/kennisbank/prognosetafel-ag2026)

Timing inference: a Q2 2026 reporting date means 30 June 2026, preceding AG2026's publication. Availability today and availability at the reporting date are different facts. AG2026 can be studied retrospectively, but must not be described as a table published by 30 June. This research does not decide the accounting treatment or whether a later assumption is appropriate.

## Exact workbook schema observed

The following are direct observations of the official parameter/best-estimate downloads retrieved on the research date, not assumptions based on the edition name.

| Edition | Mortality sheets | Ages | Calendar-year columns | Numeric mortality grid per sex |
| --- | --- | --- | --- | --- |
| AG2024 | `qx mannen 2024`, `qx vrouwen 2024` | 0–120 | 2022–2200 | 121 × 179, `B2:FX122` |
| AG2026 | `qx mannen 2026`, `qx vrouwen 2026` | 0–120 | 2024–2200 | 121 × 177, `B2:FV122` |

Both have `Voorblad` and edition-specific `Parameterwaarden` sheets. Row 1 contains calendar years; column A contains age. `mannen` and `vrouwen` are the male/female source dimensions. No unisex table was present in these downloads. Workbook used ranges extend to row 126 because of non-data cells; that does not add mortality ages. AG2026's published PDF definition includes 2022 onwards, but its delivered mortality workbook starts in 2024: import from actual headers. [AG2024 XLSX](https://www.actuarieelgenootschap.nl/download/parameters-en-best-estimate-sterftekansen-van-prognosetafel-ag2024-excel), [AG2026 XLSX](https://www.actuarieelgenootschap.nl/download/parameters-en-best-estimate-sterftekansen-van-prognosetafel-ag2026-excel), [AG2026 Appendix A, p.39](https://www.actuarieelgenootschap.nl/download/projections-life-table-ag2026)

Source identity (retrieved bytes):

- AG2024: 706,033 bytes; SHA-256 `e118780f911054a0d3410884c75375380ac99aa1ba0f32e16177cdf66bfefb6e`.
- AG2026: 648,972 bytes; SHA-256 `8880c47fce1803e97c64635cbc83edffc4cbc42a2c81dd8020c84e4e573f37fd`.

These hashes identify inspected files, not a promise that the download URLs are immutable. No separately numbered patch version was established.

The inspected male age-120 values are below one. Consequently, exhausting the supplied ages is not evidence that all remaining lives have died. A whole-life implementation needs an explicit, validated terminal-age treatment. [AG2024 XLSX](https://www.actuarieelgenootschap.nl/download/parameters-en-best-estimate-sterftekansen-van-prognosetafel-ag2024-excel), [AG2026 XLSX](https://www.actuarieelgenootschap.nl/download/parameters-en-best-estimate-sterftekansen-van-prognosetafel-ag2026-excel)

## Meaning and methodology

The sources provide annual mortality probabilities indexed by age, sex and calendar year. The formal reference life has a 1 January birthday and is alive on 1 January of the year. Cohort survival follows increasing age **and** increasing calendar year, rather than holding one period column fixed. AG2024 models a European pre-COVID Li–Lee trend, a Dutch deviation, and excess mortality. Best-estimate paths set future time-series shocks to zero. Its force of mortality is constant within each age/calendar-year cell and gives `q = 1 − exp(−mu)`. [AG2024 Appendix A, pp.29–31](https://www.actuarieelgenootschap.nl/download/projections-life-table-ag2024)

AG2026 retains the broad pre-COVID-plus-excess-mortality framework but updates pre-2020 European data, changes the projection starting point, incorporates Dutch observations through 2025, and extends excess mortality to younger ages. Its excess-mortality assumption retains 25% permanently and reduces the fading rate of the remainder to 5% annually; AG2024 assumed eventual disappearance at a 25% annual fading rate. These are substantive assumption/model changes, not interchangeable labels. [AG2026 publication](https://www.actuarieelgenootschap.nl/kennisbank/prognosetafel-ag2026)

Calculation inference from the source structure: an annual table lookup requires edition, source sex category, attained age and calendar year. A dated monthly valuation additionally requires date of birth or an explicit age convention, valuation date, payment dates and a fractional-year convention. Under the documented constant-force assumption, survival over fraction `u` of one cell is `(1 − q)^u`; a path crossing birthdays or year boundaries must split at the boundaries. Annual mortality probabilities alone do not define primo/ultimo cash-flow dates or day-count rules. [AG2024 Appendix A, p.29](https://www.actuarieelgenootschap.nl/download/projections-life-table-ag2024)

## Regular and partner factors: limits of the mortality source

AG distinguishes old-age pension, deferred partner pension and partner pension already in payment. Its examples introduce separate participant/partner ages, interest, partner frequency and partnership assumptions. The example's opposite-sex partner, three-year age difference and payment convention are illustrative assumptions, not inherent mortality-table fields. [AG2026 Appendix B, pp.50–52](https://www.actuarieelgenootschap.nl/download/projections-life-table-ag2026)

Actuarial inference, not a product decision:

- A regular single-life factor needs benefit commencement, duration, annual benefit normalization, frequency, payment timing, indexation and discount factors as well as survival.
- A partner benefit already in payment may be valued on the surviving partner's life, subject to its contract.
- A contingent partner benefit needs the death trigger, partner eligibility, partner age/sex or a specified distribution, benefit proportion, commencement/cessation rules, and treatment of joint survival/dependence. The two marginal mortality tables do not determine partnership probabilities or joint mortality.
- Under an explicitly independent, fixed-partner model with both lives initially alive, the probability of partner alive and participant dead at payment time is `S_partner(t) × [1 − S_participant(t)]`. This is a consequence of that extra independence assumption; it is not supplied by AG.

Thus “partner” cannot safely be resolved to either an in-payment single-life pension or a contingent survivor pension from the table name alone.

## Rights and unresolved evidence

The AG website disclaimer reserves rights and states that reproduction, storage or publication requires prior express written permission. Public download access therefore does **not** establish an open license to bundle or redistribute the reports, workbooks or derived datasets. No table-specific permissive redistribution license was established in this research. This is a source-rights finding, not legal advice or an assertion about statutory exceptions. [AG disclaimer](https://www.actuarieelgenootschap.nl/disclaimer)

Redistribution permission, any specific table-use terms, and third-party rights in the calibration datasets remain unverified. No AG contact was made. Numerical reproduction of the projection model, complete cell validation and actuarial-factor validation were outside this source investigation.
