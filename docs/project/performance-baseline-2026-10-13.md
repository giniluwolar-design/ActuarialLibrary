# Proposed synthetic annuity performance baseline — 13 October 2026

## Decided / scope

New branch `codex/synthetic-annuity-performance-baseline` from exact reviewed engine head `6598174d6e4ca7dd9f131ad81f98660abcd59789`. Only new `scripts/benchmark_synthetic_annuity.py`, this document and handover entry. No arithmetic/source-engine, UI/server, infrastructure, dependency, security or production optimization changes. Synthetic fixtures only. This harness is a reproducible measurement proposal, not a completed performance baseline or a large-portfolio claim.

## Pinned engine evidence supplied by lead

Lead verified full installed-package pytest at exact `6598174`: **179 passed, 123 dependency warnings, 57 subtests passed**; changed-file Ruff clean. Lead read both repair diffs. Separate strong checker reported no arithmetic counterexample across 80 seeded daily/45-digit reference cases at initial `7e87068`; numerical code was unchanged by subsequent repairs. Lead separately checked Q2 zero-mortality/unit-discount factors: monthly primo/ultimo 0.5, annual primo 0 and annual ultimo 1, with no unspecified-partner assertions in regular traces. These are pinned lead reports, not fresh execution by this cloud shell, integration acceptance or release certification.

## Implemented workloads and methodology

Named workloads: `synthetic-{regular|partner}-{annual|monthly}-{1|10|100}`. All use actual calendar ultimo schedules, valuation 30 June 2026, commencement 1 July 2026, horizon 30 June 2029. A shared immutable source has **248 invented sex/age/year qx cells**, ages 50–80 and years 2026–2029. Mortality changes by sex, age and year; all cells are explicitly synthetic, not AG. Deterministic DOBs vary birthdays and include leap-day partners. Participant weights are 40/60 and fixed-partner weights 60/40. The injected synthetic 2% annual-effective curve uses ACT/365F dated discount factors. Source construction includes cases and materialized discount evidence; no hidden original data or inferred partner gap.

Default requests three fresh-process repeats for all 12 workloads under a **20-second total child execution deadline**. Parent checks remaining total wall budget before each child; subprocess timeout kills the current child at expiry. Other requested measurements are explicitly omitted. Metadata/JSON output and process cleanup add small unbounded-by-subprocess overhead; this is not a hard operating-system limit on the parent. Budget is configurable only up to 60 seconds, repeats 1–5. Missing normal package dependencies block the first workload; subsequent measurements are omitted without repeated import attempts. No import bypass, silent fallback or extended timeout.

Each successful repeat reports:

- Normal package import time separately, outside allocation instrumentation.
- Source/case/discount construction, calculation and export times separately using `perf_counter`; all three are instrumented with `tracemalloc`, so instrumentation overhead is included.
- Phase Python allocation start/current/peak and peak-growth bytes. These exclude native allocations and are not total RAM.
- Fresh child process high-water RSS in bytes via `resource`: Linux converts KiB, macOS already reports bytes, unsupported platforms yield null. RSS includes imports/native allocations and is not attributable to one phase. It is distinct from traced Python allocations.
- Complete result-to-JSON serialization plus temporary-file write bytes/time. Results remain retained through export. No fsync guarantee, browser download or spreadsheet export is implied. Temporary synthetic exports are cleaned up.
- Python/OS/guest-visible CPU model, logical CPUs/affinity, package versions, Git checkout identity and SHA256 of harness/engine files. Guest identity is not a claim about host capacity or dedicated CPU resources.

Repeats use fresh Python children, not warm in-process engines. OS caches may remain warm. Workloads run sequentially. Raw repeat measurements remain inspectable; no invented aggregate or extrapolated portfolio throughput is emitted. A baseline reviewer can compute per-phase median/range only from completed repeats, retaining omitted runs and environment identity. Do not compare timings across different instrumentation/environment/workload definitions as if equivalent.

## Actual cloud attempt / verification

Ran `python scripts/benchmark_synthetic_annuity.py --budget-seconds 5 --repeats 1 --output work/performance-attempt.json`. Parent completed in about **0.115 seconds**, reflecting early rejection, not annuity speed. First workload `synthetic-regular-annual-1` was **blocked**: normal package import raised `ModuleNotFoundError: No module named 'polars'`. All other 11 workloads were explicitly **omitted** for that dependency block. No construction/calculation/export or peak-memory measurements were obtained. Import-failure diagnostic timing is not a successful import or engine benchmark.

Observed environment: Python 3.12.14 (Clang 22.1.3), Linux 6.18.44 x86_64/glibc 2.41, guest-reported AMD EPYC 9V74 80-Core Processor, three visible logical CPUs/affinity CPUs. NumPy 2.3.5, Pydantic 2.13.4; Polars and installed actuarial-library distribution absent. Parent uses checkout source through normal package initialization; missing dependencies remain a real block. No installation/network/security changes attempted.

Syntax compilation and diff-whitespace checks pass. CLI help and invalid-budget rejection are exercised; existing output is preserved. Full successful-workload execution and new-file Ruff await an installed environment. No timings or memory fabricated; historical engine tests do not test this new harness.

## Reproduction / next

Published via supported GitHub connector at `6aa2d04e3aaf1b96a060c151ea1c2d8bdaef4f85`, tree `927c35ed2f2074d08097df10a74867e6a8c7c8ce`, parent exact `6598174`; local/remote tree hashes and remote ref/commit parent independently verified. [Draft PR #17](https://github.com/giniluwolar-design/ActuarialLibrary/pull/17) created after verification, against the separate engine branch. Publication-note follow-up also makes missing caller-selected output directories; existing-file exclusive creation remains enforced. No shell Git push claimed.

In the installed public project, run once with the short default budget:

```bash
.venv/bin/python scripts/benchmark_synthetic_annuity.py --budget-seconds 20 --repeats 3 --output work/synthetic-annuity-baseline.json
.venv/bin/python -m ruff check --no-cache scripts/benchmark_synthetic_annuity.py
```

Output is also printed as JSON. Choose a new output filename; existing files are never overwritten. If the installed environment cannot finish requested runs within budget, review those completed and leave others omitted; agree a separate bounded run before increasing scope. This assignment does not authorize longer profiling or production optimizations.

Lead reviews fixture/date coverage, JSON export and measurement definitions, then executes the bounded harness and records exact output/software/hardware identity. Only after actual results decide whether another workload size or optimization is justified. One-case formula-workbook and real UI integration remain subsequent lead gates. No merge, deployment, issue closure, production/audit/performance certification, unlimited running or phone-push guarantee.

Founder visual choice A/B/C is pending (lead recommends A): [read-only gallery](https://github.com/giniluwolar-design/ActuarialLibrary/blob/codex/actuarial-library-vision/web/vision-prototype/README.md), draft PR #15. Marriage interpretation remains pending: age-based eligibility probabilities versus dynamic marriage/divorce/remarriage. Neither answer is inferred; this harness uses the already accepted fixed known partner only.
