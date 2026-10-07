# Local browser workspace

The visual workspace (`web/`) calls a loopback FastAPI service (`server.py`). The existing Python library owns calculations; Ollama chooses from typed tools and explains their evidence. Start with `python scripts/run_workspace.py` after installing `.[web,test]`. No frontend build or cloud account is needed.

## Implemented increment — 18 September 2026

The browser now loads the bundled synthetic claim snapshots, exposes paid/incurred/count factor and cumulative triangles, observation membership and weights, method estimates for every accident period, and explained exclusion/window/tail scenarios. Scenarios branch from the baseline. Creating a scenario never changes final selection. Markdown reports and CSV/JSON ZIP packages download from the active workspace; the report metadata includes the workspace ID.

A local SQLite store checkpoints the source triangle and claim snapshots, exact calculated baseline and scenario results, assumptions, model messages, user transcript, tool evidence, artifacts and job status. It uses JSON and base64 Parquet/bytes, not executable Python object serialization. Restoring saved results retains their original execution metadata. A fresh calculation still uses the current installed code; a saved baseline remains its recorded historical output.

Chat runs in a background thread so HTTP requests can poll progress. One model task runs at a time. Each completed tool and assistant answer checkpoints the session. Cancellation is cooperative: an in-flight local model request may take up to its 180-second HTTP timeout to return, but its subsequent tools do not run after cancellation. Six rounds and at most four tool calls per round bound a task. A restart marks unfinished jobs interrupted; completed evidence/files persist. A new follow-up continues the saved conversation. This is not automatic replay or a general durable task scheduler.

## Routes

| Route | Purpose |
|---|---|
| `GET /api/health` | App health and available local models; works when Ollama is offline |
| `POST /api/workspaces` | Open a new synthetic portfolio/valuation workspace |
| `GET /api/workspaces/{id}` | Restore saved triangle, analysis, transcript, evidence and files |
| `GET /api/workspaces/{id}/observations` | Inspect fitting evidence for a basis/development age |
| `POST /api/workspaces/{id}/tools` | Execute a typed investigation, scenario or artifact tool |
| `POST /api/workspaces/{id}/chat` | Start a model job and return its ID immediately |
| `GET /api/jobs/{id}` | Progress, completion, interruption or failure |
| `POST /api/jobs/{id}/cancel` | Request cooperative cancellation |
| `GET /api/workspaces/{id}/files/{file_id}` | Download a saved agent/report artifact |
| `GET /api/workspaces/{id}/export?scenario=…` | Download baseline or explicitly named scenario results |

These workspace routes replace the earlier stateless browser scaffold endpoints. The Streamlit app and Python library remain available.

## Operating boundary and remaining work

Run **one process and one worker**, bound to `127.0.0.1`. The service rejects foreign origins and unrecognised Host headers. The model adapter is restricted to loopback Ollama, rejects remote-backed models and redirects, and never executes generated code. There is no silent hosted fallback. [Ollama's FAQ](https://docs.ollama.com/faq) additionally describes `OLLAMA_NO_CLOUD=1` for operators who want to disable Ollama cloud features globally; this application does not change global Ollama settings.

`local_runs/workspace.sqlite3` is an unencrypted local database, excluded from Git. `ACTUARIAL_WORKSPACE_DB` can select another path. OS account/filesystem protections apply. Do not expose this service to a network: shared authentication, tenant isolation, retention controls, encryption and multi-worker coordination are not implemented.

Browser claim uploads, final selections, comprehensive agent evaluations, automated replay, Word/PowerPoint exports and per-analysis formula workbooks remain future work. Claim upload and final selections remain in Streamlit. The separate `dist/` cash-flow prototype and its Sites configuration are preserved.

## Verification

`tests/test_workspace.py` exercises the browser API boundary: opening a portfolio, inspecting an actual fitting observation, comparing an exclusion, retaining baseline results, generating and downloading a report, rebuilding sessions from SQLite, exporting a scenario with matching metadata, asynchronous tool evidence and transcript checkpoints, restart interruption, offline health, validation and cross-origin rejection. The calculation test suite independently covers numerical methods. These API checks are not browser interaction or visual acceptance tests.
