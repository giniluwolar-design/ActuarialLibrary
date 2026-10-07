"""Prepare source records and independent expected results for the annual worked example."""

import json
from datetime import date
from pathlib import Path

import polars as pl

from actuarial_library import AnalysisConfig, build_triangles, run_reserving
from actuarial_library.models import DevelopmentConfig, FrequencySeverityConfig

root = Path(__file__).resolve().parents[1]
claims = pl.read_parquet(root / "data/demo/claims.parquet")
coverage = pl.read_csv(root / "data/demo/coverage.csv", try_parse_dates=True)
annual = claims.filter(pl.col("valuation_date").dt.month() == 12).with_columns(
    pl.col("accident_date").dt.year().alias("origin_year"),
    pl.col("valuation_date").dt.year().alias("valuation_year"),
)
annual = annual.sort(["portfolio", "origin_year", "valuation_year", "claim_id"])
cols = [
    "portfolio",
    "claim_id",
    "accident_date",
    "report_date",
    "valuation_date",
    "status",
    "paid",
    "case_reserve",
    "deductible",
    "currency",
    "amount_basis",
    "origin_year",
    "valuation_year",
]
expected = {}
for portfolio in ("Motor", "Liability"):
    t = build_triangles(claims, coverage, valuation=date(2025, 12, 31), portfolio=portfolio)
    cases = {
        "base": AnalysisConfig(),
        "trend": AnalysisConfig(frequency_severity=FrequencySeverityConfig(trend=0.03)),
        "simple": AnalysisConfig(frequency_severity=FrequencySeverityConfig(average="simple")),
        "factors": AnalysisConfig(
            paid=DevelopmentConfig(average="simple", window=3, tail=1.02, rationale="Verification")
        ),
        "zero_prior": AnalysisConfig(priors={"2025": 0}),
    }
    expected[portfolio] = {key: run_reserving(t, cfg).results.to_dicts() for key, cfg in cases.items()}
payload = {
    "columns": cols,
    "rows": annual.select(cols).rows(),
    "expected": expected,
    "claims_count": claims.select(["portfolio", "claim_id"]).unique().height,
}
(root / "artifacts").mkdir(exist_ok=True)
(root / "artifacts/workbook_payload.json").write_text(json.dumps(payload, default=str))
print(f"Prepared {annual.height:,} annual snapshots and expected scenario results.")
