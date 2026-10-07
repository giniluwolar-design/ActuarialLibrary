"""Run from the repository root after installation and demo generation."""

from datetime import date
from pathlib import Path

import polars as pl

from actuarial_library import AnalysisConfig, build_triangles, export_results, run_reserving

root = Path(__file__).resolve().parents[1]
d = pl.read_parquet(root / "data/demo/claims.parquet")
c = pl.read_csv(root / "data/demo/coverage.csv", try_parse_dates=True)
for portfolio in ("Motor", "Liability"):
    triangle = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio=portfolio)
    result = run_reserving(triangle, AnalysisConfig())
    export_results(result, root / f"local_runs/{portfolio.lower()}.zip")
    print(portfolio, result.results.filter(pl.col("origin") == "2025"))
