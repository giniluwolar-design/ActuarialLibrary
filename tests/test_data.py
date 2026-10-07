from datetime import date

import numpy as np
import polars as pl
import pytest

from actuarial_library import build_triangles, run_reserving, validate_claims
from actuarial_library.demo import generate_demo


@pytest.fixture(scope="module")
def dataset():
    return generate_demo(100)


def test_demo_is_valid_and_deductible_is_metadata(dataset):
    d, c, _ = dataset
    assert validate_claims(d, c).valid
    t = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Motor")
    changed = d.with_columns((pl.col("deductible") + 1000).alias("deductible"))
    u = build_triangles(changed, c, valuation=date(2025, 12, 31), portfolio="Motor")
    np.testing.assert_allclose(t.paid, u.paid, equal_nan=True)


def test_year_quarter_balance_reconciliation(dataset):
    d, c, _ = dataset
    y = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Liability")
    q = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Liability", grain="Q")
    for i in range(20):
        for j in range(20 - i):
            for basis in ("paid", "incurred", "count"):
                total = sum(getattr(q, basis)[i * 4 + k, j * 4 + 3 - k] for k in range(4))
                assert total == pytest.approx(getattr(y, basis)[i, j])


def test_past_run_ignores_future(dataset):
    d, c, _ = dataset
    cutoff = date(2015, 12, 31)
    t = build_triangles(d, c, valuation=cutoff, portfolio="Motor")
    d2 = d.filter(pl.col("valuation_date") <= cutoff)
    c2 = c.filter(pl.col("valuation_date") <= cutoff)
    other = build_triangles(d2, c2, valuation=cutoff, portfolio="Motor")
    np.testing.assert_allclose(t.incurred, other.incurred, equal_nan=True)
    assert run_reserving(t).results.equals(run_reserving(other).results)


def test_missing_period_not_zero_or_carried_forward(dataset):
    d, c, _ = dataset
    cutoff = date(2024, 12, 31)
    c = c.with_columns(
        pl.when(pl.col("valuation_date") == cutoff)
        .then(False)
        .otherwise(pl.col("complete"))
        .alias("complete")
    )
    t = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Motor")
    assert t.states[0, 18] == "missing"
    assert np.isnan(t.paid[0, 18])
    assert t.states[19, 19] == "future"


def test_missing_closed_claim_detected(dataset):
    d, c, _ = dataset
    row = d.filter((pl.col("status") == "closed") & (pl.col("valuation_date") == date(2025, 12, 31))).row(
        0, named=True
    )
    d = d.filter(
        ~((pl.col("claim_id") == row["claim_id"]) & (pl.col("valuation_date") == row["valuation_date"]))
    )
    v = validate_claims(d, c)
    assert "missing_claims" in v.issues["code"].to_list()


def test_bad_dates_duplicates_closed_reserves(dataset):
    d, c, _ = dataset
    dup = pl.concat([d, d.head(1)])
    assert not validate_claims(dup, c).valid
    bad = d.with_columns(pl.lit("closed").alias("status"))
    assert "closed_reserve" in validate_claims(bad, c).issues["code"].to_list()
    with pytest.raises(ValueError, match="end"):
        build_triangles(d, c, valuation=date(2025, 11, 30), portfolio="Motor")


def test_drilldown_and_quarter_frequency_severity(dataset):
    d, c, _ = dataset
    t = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Motor", grain="Q")
    trace = t.trace("2025Q1", 4)
    assert trace["paid"].sum() == pytest.approx(t.paid[-4, 3])
    r = run_reserving(t)
    assert set(r.history.filter(pl.col("target") == "2025Q1")["year"].to_list()).issubset(
        set(range(2015, 2025))
    )
