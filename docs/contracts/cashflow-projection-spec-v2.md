# REVISED CONTRACT v2 — ACCEPTED WITH LEAD CORRECTIONS 27 SEP 2026
## Reserving Cash-Flow Projection Spec (issue #6)

**From:** `contracts_reserving`, 27 September 2026
**Supersedes:** `docs/project/review-2026-09-25-wave1.md` §2 draft
**Status:** Accepted for bounded implementation with the corrections below; new calculation and export tests are required before ticket closure.
**Privacy:** no private runtime data, no raw claims, no credentials

---

## Correction checklist — #6 Reserving cash flows

| # | Verdict correction (27 Sep verdict) | Contract section |
|---|---|---|
| 1 | Explicit dated tail timing as a selectable assumption, never a silent default | §3 Tail timing |
| 2 | Valuation-relative external quarterly schedules with dates, coverage and weight semantics; no automatic Q4 alignment | §4 External quarterly patterns |
| 3 | Labelled incomplete partial exports; suppressed full-portfolio totals | §6 Partial exports |
| 4 | Period-end payment dates | §2 Payment dates |
| 5 | Documented currency-aware reconciliation tolerance replacing 1e-6 cutoff | §7 Reconciliation |
| 6 | Zero-net cancellation case with regression test | §8 Zero-net case |
| 7 | Signed development coefficients, not probabilities | §9 Signed coefficients |
| 8 | Corrected wording on curve interpolation | §10 Curve interpolation |
| 9 | Reproduce worked examples 258/132/90, BF 40/60, signed -12/57 with explicit tail timing | §11 Worked examples |
| 10 | Add quarterly, irregular external-date, partial-selection, mismatched-run tests | §12 Tests |

---

## 0. Scope and placement

New deterministic module `src/actuarial_library/projection.py`: `project_payments(triangle, result, config) -> ProjectionResult`. Consumes an existing `AnalysisResult` (models.py:141). No I/O, no RNG; values clock-independent. `ProjectionConfig` added to `models.py`. Surfaced as a web panel + export; `dist/` untouched.

Grain note: 30 June 2026 is a valid valuation only for quarterly grain (data.py:197 requires year-end for "Y"), so the reference case is the quarterly path. Annual acceptance case: 31 Dec 2025.

## 1. Pattern and allocation formula

Paid CDFs from `development()` (reserving.py:61-68; `cdf[n-1] = tail ≥ 1`) define cumulative paid proportions, 1-based age `a`:

- `p_a = 1 / cdf_a` (share of ultimate paid by end of age `a`), `p_∞ = 1`
- Future step increments `d_m = p_m − p_{m−1}` for `m = a+1 … n`, and `d_tail = 1 − p_n`
- Per origin `i` with valuation age `a_i = n − i`: remaining share `R_i = 1 − p_{a_i}`
- **Renormalized weight** `w_{i,m} = d_m / R_i` (sums to 1 over the origin's steps)
- **Payment** `= outstanding_i × w_{i,m}`, where `outstanding_i` is the *selected* row's outstanding (reserving.py:211), regardless of method.

Renormalization to the selected outstanding is mandatory — it makes BF/incurred/FS/manual selections schedule correctly and guarantees reconciliation. For paid CL the identity `outstanding_i / R_i = ultimate_i` holds exactly, so payments ≡ ultimate×d_m, the classic CL allocation; the outstanding base is the spec because it generalizes.

**Rounding:** float64 throughout, no intermediate rounding; exports display cents; documented tolerance applies to unrounded sums (§7).

**Guards:** missing/non-finite required CDF → blocked. Any nonzero outstanding with a zero remaining share needs an external schedule; do not discard sub-cent reserves. Signed remaining shares are permitted subject to conditioning controls (§7). Missing selection, unavailable pattern, missing timing and unstable normalization can each make a projection partial. Validate matching input version, valuation, origin set, currency and amount basis between triangle and result. `a_i=n-i` applies only to the supported complete square geometry; reject unsupported geometry.

## 2. Payment dates

Payment at step `m` (increment between ages `m−1` and `m`) lands in calendar period index `o_i + m − 1`, where `o_i` is the origin's period index (data.py:31-32); label via `label()` (data.py:35-36), payment date via `period_end()` (data.py:39-41). **Period-end dates** are used for the initial reserving schedule. Day count, fractional maturities and optional timing scenarios are documented in #7. Payment timing is an assumption, not a fact supplied by EIOPA.

## 3. Tail timing (answers correction #1)

- **Explicit dated timing is a selectable assumption**, never a silent default. Tail=1 has zero tail increment and creates no tail payment.
- **Option A — "next period" (selectable, labelled):** the tail increment `d_tail` lands wholly in the single period `o_i + n`. The assumption and its rationale are recorded on the projection config.
- **Option B — explicit dated schedule:** optional fractions over future periods (sum 1, source + rationale required) spreading `d_tail`; validated sum-to-1 within 1e-9. Each tail component carries its own date and weight.
- **Undated tail amounts** are shown as pending; a complete dated/discounted schedule is unavailable until they are assigned.
- Every applicable row carries `tail_timing = "selected_next_development_period" | "external:<name>" | "undated_pending"`. Option A means after the final modelled development age, not necessarily immediately after valuation.

## 4. External quarterly patterns (answers correction #2)

- **Reject aligning every annual origin automatically to Q4.** External quarterly schedules must specify: payment dates or quarter offsets measured from the valuation; coverage of each origin/age (which origins/ages the pattern covers); whether weights are future-conditional or cumulative development proportions.
- An annual triangle at year-end plus an explicit future quarterly pattern is valid; it cannot manufacture a 30 June observed balance from December data.
- Quarterly → annual roll-up is pure aggregation (allowed, offered as display/export); detail retained.
- Each component carries source, rationale and coverage. Future-conditional weights must sum to one (signed coefficients allowed explicitly); cumulative patterns must first be conditioned at valuation. Explicit amount schedules are not silently renormalized and must reconcile to the selected reserve. Every future payment date must be strictly after valuation.

## 5. Negative implied payments (answers correction #7 partially)

Arise when (a) some `d_m < 0` because a selected factor < 1, or (b) the selected outstanding itself is negative. Both retained, never floored, never removed. Each affected row carries `diagnosis = "negative implied payment: paid factor below one at age m"` / `"negative outstanding base retained"`. Calendar-period aggregates are net sums with a warning whenever any component is negative; per-origin detail always stays visible.

## 6. Partial exports (answers correction #3)

Local partial exports are permitted with an unmistakable incomplete label: included/excluded origin list, reasons for exclusion, reconciliation to the selected, projectable subset. **Full-portfolio totals are suppressed** when selections or required patterns are missing. No repeated confirmation dialog is needed. The export manifest states `selection_complete = false` and lists every excluded origin with its reason.

## 7. Reconciliation tolerance (answers correction #5)

- **Per origin:** Σ undiscounted payments = selected outstanding, |diff| ≤ documented tolerance → status `ok`; otherwise `error`.
- **Amount reconciliation:** initial EUR tolerance is `max(0.01, 1e-12 * max(abs(outstanding), sum(abs(payments))))` in EUR. Other currencies need explicit minor-unit metadata. Amount tolerance never determines whether a reserve is treated as zero.
- **Dimensionless conditioning:** separate from amount tolerance. For nonzero remaining share, calculate `kappa=max(1, sum(abs(d_m))/abs(R_i))`, including tail components. Block with `UNSTABLE_PATTERN_NORMALIZATION` if `kappa * numpy.finfo(float).eps > 1e-10`, or if any coefficient/payment is non-finite. Record the threshold as a versioned engineering convention and test cancellation near the boundary; do not compare a dimensionless share to a money tolerance. Check the implied incremental sum against `R_i` before division.
- **Calendar totals cross-check:** Σ over calendar periods = Σ over origins.
- Display rounding is separate from the unrounded reconciliation check.

## 8. Zero-net cancellation case (answers correction #6)

A zero net reserve and zero remaining share do not prove all future cash flows are zero: positive and negative increments can cancel. **Return an empty/zero schedule only when remaining increments are all zero and the reserve is zero.** Otherwise require explicit signed cash-flow amounts or another independently justified scale.

Required new tests: zero reserve/zero remaining share with nonzero offsetting increments and no independent scale is blocked; an explicitly supplied +100/-100 future schedule is retained and reconciles to zero. These are planned tests, not evidence that `tests/test_projection.py` exists.

## 9. Signed development coefficients (answers correction #7)

Negative remaining share and negative increments are retained as **signed development coefficients**; they are never described as probabilities. A coefficient of −0.15 is a signed development weight, not a negative probability. Warn on negative components and scale-sign reversals; do not clip or silently rescale away recoveries. The sign of each coefficient is preserved in the output and in the evidence trace.

## 10. Curve interpolation wording (answers correction #8)

Corrected: **"Undiscounted schedule always produced"** — valid projectable rows can be produced independently of curve availability. Missing factors, selection or timing still block affected rows. An available curve may use the approved interpolation convention; a missing curve cannot be invented. The previous blanket "never interpolated" wording is replaced by this precise statement: curve interpolation is permitted only when curve evidence exists and the convention is documented; missing curve evidence blocks the discounted view with an F006 warning — never interpolated — while the undiscounted schedule stands. Both columns shown when evidence exists.

## 11. Worked examples with explicit tail timing (answers correction #9)

All examples use **Option A tail timing** ("next period", explicitly selected, rationale: deterministic, no invented decay). Valuation date 31 Dec 2025 for annual examples.

### Example A — Annual 3×3, volume-weighted

Paid triangle: 2023: 100, 200, 240 · 2024: 120, 240, — · 2025: 150, —, —.
Volume-weighted: f₁ = 440/220 = **2.0**; f₂ = 240/200 = **1.2**; tail = **1.25**.
CDFs: age1 **3.0**, age2 **1.5**, age3 **1.25** → p = 1/3, 2/3, 4/5, 1 → d = **1/3, 2/15, 1/5**.

| origin | a | paid | ultimate | outstanding | R = 1−p_a | tail weight | payments |
|---|---|---|---|---|---|---|---|
| 2023 | 3 | 240 | 300 | 60 | 1/5 | 1 | **60** (2026, tail) |
| 2024 | 2 | 240 | 360 | 120 | 1/3 | 3/5 | **48** (2026), **72** (2027, tail) |
| 2025 | 1 | 150 | 450 | 300 | 2/3 | 3/10 | **150** (2026), **60** (2027), **90** (2028, tail) |

Calendar: 2026 = 60+48+150 = **258**; 2027 = 72+60 = **132**; 2028 = **90**; total **480** = Σ outstanding (60+120+300) ✓.

### Example B — BF base on 2024

2024 selects paid_bf: ultimate 340 → outstanding 100 → **40** (2026, development), **60** (2027, tail). Paid shape, selected base ✓.

### Example C — Signed coefficients

Override f₂ = 0.95 (tail 1.25): CDF₂ = 19/16, p₂ = 16/19, d₃ = 4/5 − 16/19 = **−4/95** < 0.
2024: ultimate 240×19/16 = 285, outstanding 45, R = 3/19; weights −4/15 and 19/15 → payments **−12.00** (2026, labelled negative implied payment) and **+57.00** (2027); Σ = 45 ✓. Retained, unfloored, signed coefficients preserved.

## 12. Tests (answers correction #10)

New `tests/test_projection.py`:

| Test | What it pins |
|---|---|
| `test_projection_reconciles_to_selected_outstanding` | Per-origin Σ payments = outstanding, tolerance §7 |
| `test_projection_paid_cl_identity_with_ultimate_increment` | Paid CL: payments ≡ ultimate × d_m |
| `test_projection_calendar_mapping_and_tail_default` | 258/132/90; tail-in-2026 for 2023; explicit tail timing |
| `test_projection_bf_uses_selected_outstanding_base` | 40/60 BF case |
| `test_projection_negative_implied_payments_retained_and_labelled` | −12/57 signed coefficients, unfloored |
| `test_projection_negative_outstanding_projects_negative_schedule` | Negative outstanding → signed schedule |
| `test_projection_blocked_when_pattern_closed_but_outstanding_nonzero` | Blocked guard |
| `test_projection_quarterly_gate_rejects_invented_quarterly_split` | Annual triangle alone cannot create quarterly payments; an explicit future quarterly pattern is allowed |
| `test_projection_quarterly_triangle_maps_quarter_labels` | Q-grain triangle → quarter labels |
| `test_projection_external_pattern_requires_source_and_rationale` | External pattern must specify dates, coverage, weights |
| `test_projection_partial_selection_annotates_missing_origins` | Incomplete label, excluded origins with reasons, suppressed full total |
| `test_projection_export_roundtrip` | Actual download verified |
| `test_projection_evidence_columns_present` | Provenance columns on every row |
| `test_projection_irregular_external_dates` | External pattern with irregular payment dates, not quarter-aligned |
| `test_projection_mismatched_run` | Triangle from run A with result from run B → blocked/mismatched-run control |
| `test_projection_zero_net_recovery` | Unscaled cancellation blocks; explicit +100/-100 payments are retained |
| `test_projection_currency_aware_tolerance` | Different currency → different tolerance, never mixed |
