"""Manual integration check: sends only synthetic aggregates to local Ollama."""

import json
from datetime import date
from pathlib import Path

import polars as pl

from actuarial_library import AnalysisConfig, build_triangles
from actuarial_library.agent import AnalystSession

triangle = build_triangles(
    pl.read_parquet("data/demo/claims.parquet"),
    pl.read_csv("data/demo/coverage.csv", try_parse_dates=True),
    valuation=date(2025, 12, 31),
    portfolio="Motor",
)
agent = AnalystSession(triangle, AnalysisConfig())
answer = agent.ask(
    "Test a paid tail factor of 1.05 as a sensitivity. Report the latest origin paid Chain Ladder ultimate change versus current assumptions. Cite the tool evidence.",
    "gemma4:latest",
    progress=lambda text: print(text, flush=True),
)
print(answer, flush=True)
Path("local_runs").mkdir(exist_ok=True)
Path("local_runs/agent-smoke.json").write_text(json.dumps(agent.record(), indent=2, default=str))
assert agent.scenarios, "No scenario tool called"
assert any(e["tool"] == "compare_scenario" for e in agent.evidence)

assert not answer.startswith("Analysis paused:"), "Model did not complete the explanation"
