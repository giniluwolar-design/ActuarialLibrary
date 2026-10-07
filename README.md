# Actuarial Library

Explainable non-life reserving, from historical claim snapshots to selected ultimates.

This first release includes paid/incurred Chain Ladder, paid/incurred Bornhuetter–Ferguson and frequency × severity. A local visual app exposes the data, development selections, assumptions and results. No programming is needed to operate the app after installation.

## Start locally

Python 3.12 or newer is required. From the repository folder:

```bash
python -m venv .venv
# macOS / Linux
source .venv/bin/activate
# Windows PowerShell instead: .venv\Scripts\Activate.ps1
python -m pip install -c constraints.txt ".[app,test]"
python -m actuarial_library.demo
python -m streamlit run app.py
```

Open the local address printed by Streamlit. The app listens on 127.0.0.1; source data is not sent to a cloud service. Synthetic data generation is deterministic and requires no network. Public benchmark tests use the sample bundled with the installed `chainladder` package.

Choose Motor or Liability, then follow **Load data → Explore triangles → Calculate ultimate**. Data checks and advanced assumptions are collapsible. The AI analyst stays alongside the workspace. No final method is selected automatically. Changed assumptions invalidate the previous result and disable its export.

The worked example is [examples/reserving_worked_example.xlsx](examples/reserving_worked_example.xlsx). It contains editable formulas for the annual demo; exports from the app are result tables and a complete JSON run record, not new formula workbooks.

## Use as a library

```python
from datetime import date
import polars as pl
from actuarial_library import build_triangles, run_reserving, export_results

claims = pl.read_parquet("data/demo/claims.parquet")
coverage = pl.read_csv("data/demo/coverage.csv", try_parse_dates=True)
triangle = build_triangles(claims, coverage,
    valuation=date(2025, 12, 31), portfolio="Motor")
analysis = run_reserving(triangle)
export_results(analysis, "local_runs/motor.zip")
```

The public API also exposes `validate_claims`, `load_triangle`, `AnalysisConfig`, `DevelopmentConfig` and `FrequencySeverityConfig`. See [API examples](docs/api.md), [data dictionary](docs/data_dictionary.md), [methodology](docs/methodology.md) and [research](docs/research.md).

## Test and measure

```bash
python -m pytest -q
python examples/analyse_demo.py
python scripts/benchmark.py
```

The CI configuration runs installation and tests on Linux, Windows and macOS. A configured CI matrix is not evidence that remote jobs have already passed; the [verification report](docs/verification.md) identifies checks actually executed locally and remaining release checks.

## Scope

Amounts are undiscounted, in one currency and on one declared deductible basis per analysis. Deductible is retained as metadata and is not subtracted. `incurred = paid + case_reserve`. Outstanding is ultimate minus paid; additional reserve is ultimate minus incurred. Changes in incurred are not payment cash flows.

This release estimates deterministic reserves. It does not produce stochastic uncertainty, automatically select the most appropriate method, implement reinsurance, establish formal approvals or provide a tamper-proof audit trail. Source completeness declarations remain the responsibility of the data producer. Assumptions, deficiencies and negative reserve estimates stay visible.

## Structure and roadmap

- `src/actuarial_library`: reusable data, calculation and export modules.
- `app.py`: local user interface; no actuarial formulas are owned by the UI.
- `data/demo`: synthetic snapshots, coverage and intentional validation failures.
- `examples`: API example and worked Excel.
- `docs`: methodology, research, data contract and [roadmap](docs/roadmap.md).
- `tests`: hand calculations, independent benchmark and workflow tests.

The earlier cash-flow prototype in `dist/` is retained separately. EIOPA curves, DNB datasets and MCP chat access follow this module; see the roadmap. No public deployment or GitHub repository publication is performed by this release.

Own source code: MIT. Third-party software/data retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).

## Actuarial review workspace

Explore triangles defaults to an age-to-age development-factor triangle. Advanced assumptions compare all-history, three-pair and five-pair factor averages and let you exclude observations with an explanation. Live charts show the fitted pattern and exact observations used. Calculate ultimate compares your assumptions with the default run on identical data; it does not claim to explain valuation-to-valuation reserve movements.

Load data shows paid and remaining case reserves by accident year and a claim-size distribution. The optional large-claim review uses the upper 3-IQR fence on log(1 + incurred), only at the chosen valuation. Samples below 20 claims or with zero IQR are not flagged. Flags never remove records or imply that a claim is erroneous.

See [agent-assisted workflow](docs/agentic-workflow.md) for the proposed chat, numerical tools and reporting architecture, including what is and is not implemented.

## Explore with local Gemma

With Ollama running, use the **Your AI analyst** panel, click **Connect to local Gemma**, and try a starter question. The agent can explain the API, inspect data and link ratios, compare methods and run separate exclusion/window/tail scenarios using the calculation library. Ask it to make a report (a Markdown draft with computed results, assumptions and metadata), or test data (a ZIP with synthetic claims.csv and coverage.csv ready to upload). Actual files appear under **Files created**. See the [local agent guide](docs/agentic-workflow.md) for details. No cloud model or API key is used.

## Browser reserving workspace

The main browser workspace pairs an interactive reserving surface with a local Ollama analyst. Start it from this checkout:

```bash
python -m pip install -c constraints.txt -e ".[web,test]"
python scripts/run_workspace.py
```

Open **http://127.0.0.1:8765**. The launcher imports the checkout's calculation library and listens only on loopback. Run one server process/worker.

- Explore paid, incurred and count triangles. Click a development factor to inspect its ratio, fitting weight and membership.
- Compare all five method estimates by accident period. Missing results include their reason.
- Test explained exclusions, historical windows and tails as separate baseline-relative scenarios.
- Create a Markdown review or download a ZIP of values, assumptions and metadata. These are actual files from the active workspace.
- Open Ollama, select an installed local model and ask the analyst to inspect evidence, explain the API or run a scenario. No paid API key is required. No cloud-model fallback is configured.
- See task progress and stop a task at the next model boundary. Local inference may take minutes. Refreshing the page reconnects to the saved task.

The browser currently uses bundled **synthetic Motor and Liability data**; use the legacy Streamlit app for claim uploads and final method selections. The browser makes no final actuarial selection. Chat, source triangle/claims, baseline results, scenarios, evidence and files are checkpointed in `local_runs/workspace.sqlite3`. This database is local, unencrypted and excluded from Git. It is a single-user prototype, not a shared service or immutable audit system. Interrupted jobs remain visible; a follow-up can use saved evidence, but model calls are not automatically replayed.

Local model inference uses your hardware and electricity; free source code does not eliminate those costs. The installed Gemma model is selectable, not a guarantee of narrative accuracy or suitability. See [architecture and verification](docs/application-architecture.md) and [local agent guide](docs/agentic-workflow.md).
