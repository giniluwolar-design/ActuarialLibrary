# Browser workspace verification — 18 September 2026

- Existing numerical/data/agent/Streamlit suite: 24 passed.
- New API checks: baseline-preserving scenarios, exact result/session restoration, valid report/ZIP downloads, offline model health, origin/host rejection, asynchronous evidence checkpoints, interruption recovery and cooperative cancellation (see tests/test_workspace.py).
- Frontend JavaScript parsed as an ES module; local route and assets served successfully. Preview opened in Chrome and showed populated synthetic Liability data and local-model availability. Interactive browser and visual acceptance tests were not performed.
- Live Gemma task through the HTTP job API: installed `gemma4:latest` called `explain_library` with `topic=run_reserving`; returned the actual signature and documented result fields with `[T1]`. Elapsed time: 125.4 seconds. Transcript and tool evidence were checkpointed. This is one smoke test, not a comprehensive model evaluation.
- Library tests emit upstream NumPy/chainladder deprecation warnings. API test dependencies emit Starlette/httpx deprecation warnings; no failed assertions.

The local database is under local_runs and is not checked into Git. Browser uploads, final selections and shared deployment remain outside this increment.
