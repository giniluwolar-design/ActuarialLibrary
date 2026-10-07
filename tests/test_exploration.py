import io
import zipfile
from datetime import date

import numpy as np
import polars as pl
import pytest
from test_reserving import small

from actuarial_library import AnalysisConfig, validate_claims
from actuarial_library.agent import AnalystSession
from actuarial_library.exploration import claim_diagnostics, factor_triangle


def test_factor_triangle_preserves_zero_invalid_and_missing():
    t = small()
    factors = factor_triangle(t, "paid")
    assert factors[0].tolist() == pytest.approx([1.5, 1.2])
    assert np.isnan(factors[1, 1])
    t.paid[0, 0] = 0
    t.paid[1, 1] = 0
    factors = factor_triangle(t, "paid")
    assert np.isnan(factors[0, 0])
    assert factors[1, 0] == 0


def test_claim_diagnostics_uses_one_snapshot_and_flags_without_dropping():
    valuation = date(2025, 12, 31)
    values = list(range(100, 140)) + [10000000]
    current = pl.DataFrame(
        {"valuation_date": [valuation] * len(values), "paid": values, "case_reserve": [0] * len(values)}
    )
    older = current.with_columns(pl.lit(date(2024, 12, 31)).alias("valuation_date"))
    rows, rule = claim_diagnostics(pl.concat([older, current]), valuation)
    assert rows.height == 41
    assert rows["review_flag"].sum() == 1
    assert rule["threshold"] > 140
    short, rule = claim_diagnostics(current.head(5), valuation)
    assert rule["threshold"] is None
    assert not short["review_flag"].any()


def test_agent_creates_real_report_and_reloadable_synthetic_test_package():
    session = AnalystSession(small(), AnalysisConfig())
    report = session.execute("create_artifact", {"artifact": "report"})
    body = session.artifacts[report["file_id"]]["content"].decode()
    assert "288.00" in body  # independently known paid CL ultimate
    assert "Bornhuetter–Ferguson" in body
    with pytest.raises(ValueError):
        session.execute("create_artifact", {"scenario_id": "does_not_exist"})
    output = session.execute("create_artifact", {"artifact": "test_data"})
    archive = zipfile.ZipFile(io.BytesIO(session.artifacts[output["file_id"]]["content"]))
    claims = pl.read_csv(io.BytesIO(archive.read("claims.csv")), try_parse_dates=True)
    coverage = pl.read_csv(io.BytesIO(archive.read("coverage.csv")), try_parse_dates=True)
    assert validate_claims(claims, coverage).valid
    assert len(archive.namelist()) == 3
    assert "ultimate" not in claims.columns
