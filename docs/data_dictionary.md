# Data dictionary

## Claims snapshots

One row represents one reported claim at one historical valuation date. Snapshots are full inventories, not changes since the preceding extract. Closed claims remain in later snapshots. Unreported claims do not appear until their report date.

| Field | Type | Meaning |
|---|---|---|
| portfolio | text | Stable, homogeneous analysis segment |
| claim_id | text | Stable identifier, unique inside portfolio |
| accident_date | ISO date | Date of loss, determines origin period |
| report_date | ISO date | First report date; not a reopening date |
| valuation_date | ISO date | Date on which all row values were known |
| status | text | `open` or `closed` at this valuation |
| paid | number | Cumulative paid on the declared amount basis |
| case_reserve | number | Remaining reported-claim reserve, not total incurred |
| deductible | number | Metadata only; never automatically subtracted |
| currency | text | One currency per fit, for example EUR |
| amount_basis | text | `before_deductible` or `after_deductible` |
| incurred | optional number | Must reconcile with paid + case_reserve |

Dates use `YYYY-MM-DD`. Amounts are in whole currency units, with decimal fractions allowed. Monetary input is not expressed in thousands. Claim IDs must be read as text to preserve leading zeros. Required numeric fields must be finite and nonnegative. Negative changes between successive cumulative balances are allowed and reported; a negative cumulative balance is outside this contract.

Claim dates, currency, deductible and amount basis must remain stable through its history in v0.1. Historical restatements are supplied as a consistent replacement dataset and receive a new source hash. The tool does not invent version precedence between conflicting rows.

The deductible basis is independent of reinsurance basis. The tool does not model reinsurance. Do not mix direct, ceded and net-of-reinsurance amounts in a single analysis. Loss-adjustment expenses must be consistently included or excluded in every period; no separate expense model is present.

## Coverage

One row per `portfolio`, `currency`, `amount_basis`, `valuation_date`, with Boolean `complete`. CSV accepts true/false or 1/0.

An explicitly complete, empty origin-period bucket becomes a zero. A missing or incomplete snapshot stays missing. Future cells are structurally unavailable. Previously seen claims disappearing from a declared complete later extract are an error. A claim omitted from every extract cannot be discovered by this check: reconcile source-system control totals outside the tool.

Annual analysis uses December 31 balances. Quarterly analysis uses March 31, June 30, September 30 and December 31. All origins from the coverage start year to valuation are included. Start-year filtering controls displayed origins but does not aggregate older years into them.

## Aggregate triangle input

`load_triangle` accepts a full square with columns `origin`, `development`, `paid`, `incurred`, `count`, `state`. Origin labels are `2025` for annual or `2025Q1` for quarterly. Development is an integer starting at one. Origins are contiguous and end at valuation. Each cell appears exactly once.

States are `observed`, `missing` and `future`. Missing/future values must be null. An absent measure, such as incurred in a paid-only benchmark, may be null for all observed cells; methods needing that measure then remain unavailable. This adapter does not reconstruct claims and cannot provide claim drill-down.

## Synthetic portfolio

The seed is 20260914. The generator produces 2,000 latent claims for Motor and 2,000 for Liability across 2006–2025. The observed dataset may contain fewer distinct claims because some claims are not yet reported by the cutoff. It includes cumulative quarterly snapshots, after deductible, in EUR. Amounts are generated directly on that basis; the separate deductible field is not applied again.

The generator returns latent truth separately for tests. The command-line demo writer deliberately does not save it. These are designed examples, not calibrated Dutch market experience, and the late-development cutoff is a simulation choice rather than evidence for a real portfolio tail.
