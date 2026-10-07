# Wave 2 contract review — 27 September 2026

Lead verdict: accepted for bounded implementation after direct corrections to all five documents. No ticket is closed and no new engine is certified. These corrections supersede the corresponding Wave 1 open questions and v2 draft contradictions.

| Document | Review finding and disposition |
| --- | --- |
| `docs/contracts/evidence-graph-contract-v2.md` | Fixed composite IDs masquerading as opaque IDs, deterministic tool output misclassified as model explanation, explicitly permitted result-to-narrative dependency, non-unique pagination cursors and lossy hash wording. Implement the corrected contract. |
| `docs/contracts/cashflow-projection-spec-v2.md` | Separated dimensionless conditioning from money tolerance, removed sub-cent erasure, distinguished unscaled zero-net cancellation from explicit signed schedules, fixed BF tail label and quarterly exception. Implement with new tests. |
| `docs/contracts/annuity-factors-spec-v2.md` | Specified commencement, cutoff, horizon endpoints, ACT/ACT-calendar survival fractions and leap-day examples. Removed unsupported universal-convention claim. Synthetic finite-horizon engine may now be implemented; whole-life/real-AG release remains gated. |
| `docs/contracts/ag-ingestion-spec-v2.md` | Removed run assumptions from import provenance, reconciled q=0/1 validation/test contradictions, made terminal qx factual rather than hardcoded, removed synthetic-origin claim based only on hashes. Synthetic adapter implementation may proceed. |
| `docs/research/discounting-conventions-eiopa.md` | Corrected false single-factor PV reconciliation and workbook hash; selected ACT/365F and labelled log-linear discount-factor interpolation within 0–150y, no beyond-horizon extrapolation. Implement a pure discount module with new numerical tests. |

Source checks: lead re-downloaded the public EIOPA June archive in memory; archive digest `80d5c4af0f4dd8f025103be4f746ae86d62f99a3c313c3024f4700a8965972fb`, workbook digest `1d7c280201255b22f8bcb12064ec421f8259c226f65ba892d1838ab07d3248f6`. The source PDF section 9.10 provides the Smith–Wilson pricing function; workbench interpolation is explicitly an approximation, not an equivalent reconstruction.

Verification distinction: 33 existing tests passing is reported by workers and supports unchanged baseline behavior. The new contract tests do not yet exist merely because they are listed in documents. No fresh numerical, browser, model or export certification is implied by accepting a specification.

Next PM assignment: stop broad contract redrafting. Assign disjoint source/test ownership for graph, projection, discounting and synthetic mortality/factors; keep API/UI integration with one owner. First deliverable remains the inspectable Evidence Graph prototype and then one integrated result-to-evidence path. Give the lead its URL/run instructions now that the prototype worker reports done. Subsequent numerical code must include independent reference tests and the required trace. Routine correction of these documents does not need founder approval. Final model selections, real-AG rights and publication boundaries remain unchanged.
