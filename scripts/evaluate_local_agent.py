"""Small local-only capability checks. Passing is a smoke test, not actuarial certification."""

import argparse
import inspect
import json
import sys
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import polars as pl
from actuarial_library import AnalysisConfig, build_triangles, run_reserving
from actuarial_library.agent import AnalystSession


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()
    triangle = build_triangles(
        pl.read_parquet(ROOT / "data/demo/claims.parquet"),
        pl.read_csv(ROOT / "data/demo/coverage.csv", try_parse_dates=True),
        valuation=date(2025, 12, 31),
        portfolio="Motor",
    )
    cases = [
        (
            "documentation",
            "Use explain_library with topic run_reserving. State its exact signature and outputs. Cite evidence. Keep under 100 words.",
            "explain_library",
        ),
        (
            "scenario",
            "Compare a paid tail of 1.05 against baseline, reason: investigate late settlement sensitivity. Report the latest origin paid Chain Ladder ultimate change, citing evidence. Keep under 80 words.",
            "compare_scenario",
        ),
        (
            "report",
            "Create a Markdown review report for this baseline. Use create_artifact. Confirm the actual filename in one sentence.",
            "create_artifact",
        ),
    ]
    outcomes = []
    for name, prompt, expected in cases:
        session = AnalystSession(triangle, AnalysisConfig())
        start = time.monotonic()
        answer = session.ask(prompt, args.model, progress=lambda msg: print(f"{name}: {msg}", flush=True))
        tools = [
            e["tool"]
            for e in session.evidence
            if not isinstance(e["result"], dict) or "error" not in e["result"]
        ]
        passed = expected in tools and not answer.startswith("Analysis paused:")
        if name == "documentation":
            passed = passed and "triangle" in answer and "AnalysisResult" in answer and "[T" in answer
        if name == "scenario":
            passed = passed and bool(session.scenarios) and session.config.paid.tail == 1 and "[T" in answer
        if name == "report":
            passed = passed and bool(session.artifacts) and "reserving-review.md" in answer
        result = {
            "case": name,
            "passed_smoke_checks": bool(passed),
            "seconds": round(time.monotonic() - start, 2),
            "answer": answer,
            "evidence": session.evidence,
            "timings": session.model_info.get("timings", []),
        }
        outcomes.append(result)
        print(json.dumps({k: v for k, v in result.items() if k not in {"evidence", "timings"}}), flush=True)
    output = ROOT / "local_runs/local-model-evaluation.json"
    output.write_text(
        json.dumps(
            {
                "model": args.model,
                "api_signature": str(inspect.signature(run_reserving)),
                "cases": outcomes,
                "limitation": "Human narrative/numeric review still required.",
            },
            indent=2,
        )
    )
    print(f"Saved {output}")
    raise SystemExit(0 if all(x["passed_smoke_checks"] for x in outcomes) else 1)


if __name__ == "__main__":
    main()
