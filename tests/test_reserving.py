import io
import json
import zipfile
from datetime import date

import numpy as np
import polars as pl
import pytest

from actuarial_library import (
    AnalysisConfig,
    export_google_sheets_package,
    export_results,
    load_triangle,
    run_reserving,
)
from actuarial_library.models import DevelopmentConfig, FrequencySeverityConfig, Triangle
from actuarial_library.reserving import development


def small():
    p = np.array([[100.0, 150.0, 180.0], [120.0, 180.0, np.nan], [160.0, np.nan, np.nan]])
    c = np.array([[2.0, 3.0, 3.0], [3.0, 3.0, np.nan], [2.0, np.nan, np.nan]])
    return Triangle(
        ["2023", "2024", "2025"],
        [2023, 2024, 2025],
        "Y",
        date(2025, 12, 31),
        p,
        p * 1.1,
        c,
        np.where(np.isfinite(p), "observed", "future"),
    )


def test_hand_chainladder_bf_and_reserve_definitions():
    t = small()
    r = run_reserving(t, AnalysisConfig(priors={"2023": 200, "2024": 240, "2025": 300}))
    paid = r.results.filter(pl.col("method") == "paid_cl")
    assert paid["ultimate"].to_list() == pytest.approx([180, 216, 288])
    bf = r.results.filter((pl.col("method") == "paid_bf") & (pl.col("origin") == "2025")).row(0, named=True)
    assert bf["ultimate"] == pytest.approx(160 + 300 * (1 - 1 / 1.8))
    assert bf["outstanding"] == pytest.approx(bf["ultimate"] - 160)
    assert bf["additional_reserve"] == pytest.approx(bf["ultimate"] - 176)
    assert bf["case_reserve"] == pytest.approx(16)
    assert not r.results["selected"].any()


def test_google_sheets_package_contains_values_tables_and_instructions():
    r = run_reserving(small())
    with zipfile.ZipFile(io.BytesIO(export_google_sheets_package(r))) as archive:
        names = set(archive.namelist())
        assert {
            "results.csv",
            "development_factors.csv",
            "historical_calibration.csv",
            "analysis.json",
            "README.txt",
        } <= names
        assert "origin,method" in archive.read("results.csv").decode()
        assert "Google Sheets" in archive.read("README.txt").decode()


def test_averages_window_exclusion_and_tail():
    t = small()
    t.paid[1, 1] = 240
    _, _, f, _ = development(t, "paid", DevelopmentConfig())
    assert f[0]["selected"] == pytest.approx(390 / 220)
    _, _, f, _ = development(t, "paid", DevelopmentConfig(average="simple"))
    assert f[0]["selected"] == 1.75
    _, _, f, _ = development(t, "paid", DevelopmentConfig(window=1))
    assert f[0]["selected"] == 2
    _, _, f, _ = development(t, "paid", DevelopmentConfig(excluded=[("2024", 1)], rationale="Test"))
    assert f[0]["selected"] == 1.5
    u, _, _, _ = development(small(), "paid", DevelopmentConfig(tail=1.1, rationale="External tail"))
    assert u == pytest.approx([198, 237.6, 316.8])


def test_frequency_severity_no_feedback():
    t = small()
    fs = FrequencySeverityConfig(count_mode="manual", expected_counts={"2025": 5})
    base = run_reserving(t, AnalysisConfig(frequency_severity=fs))
    # Prior-year incurred ultimates: 198 and 237.6; count ultimates: 3 and 3.
    expected = (198 + 237.6) / 6 * 5
    actual = base.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "frequency_severity"))[
        "ultimate"
    ][0]
    assert actual == pytest.approx(expected)
    changed = run_reserving(
        t,
        AnalysisConfig(
            frequency_severity=fs,
            selections={"2023": "manual"},
            manual_ultimates={"2023": 9999},
            selection_notes={"2023": "Independent judgement"},
        ),
    )
    assert changed.history.equals(base.history)


def test_frequency_severity_weighting_trend_and_exposure():
    fs = FrequencySeverityConfig(
        average="simple",
        trend=0.1,
        count_mode="exposure",
        exposures={"2025": 100},
        frequencies={"2025": 0.05},
        historical_counts={"2023": 2, "2024": 4},
        rationale="Test",
    )
    r = run_reserving(small(), AnalysisConfig(frequency_severity=fs))
    out = r.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "frequency_severity"))[
        "ultimate"
    ][0]
    assert out == pytest.approx(((198 / 2 * 1.1**2) + (237.6 / 4 * 1.1)) / 2 * 5)


def test_zero_and_missing_and_invalid_bf():
    t = small()
    t.paid[0, 0] = 0
    _, _, f, _ = development(t, "paid", DevelopmentConfig())
    assert f[0]["pairs"] == 1
    t.paid[2, 0] = np.nan
    assert (
        run_reserving(t).results.filter((pl.col("origin") == "2025") & (pl.col("method") == "paid_cl"))[
            "ultimate"
        ][0]
        is None
    )
    t = small()
    cfg = AnalysisConfig(
        paid=DevelopmentConfig(overrides={1: 0.5, 2: 1}, rationale="Release"), priors={"2025": 300}
    )
    r = run_reserving(t, cfg)
    assert (
        r.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "paid_bf"))["ultimate"][0]
        is None
    )
    assert (
        r.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "paid_cl"))["outstanding"][0] < 0
    )


def test_explicit_reporting_confirmation_and_zero_prior():
    with pytest.raises(ValueError):
        FrequencySeverityConfig(count_mode="reported")
    r = run_reserving(small(), AnalysisConfig(priors={"2025": 0}))
    assert (
        r.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "paid_bf"))["ultimate"][0] == 160
    )
    with pytest.raises(ValueError):
        DevelopmentConfig(overrides={1: 2})


def test_export_roundtrip():
    r = run_reserving(small())
    with zipfile.ZipFile(io.BytesIO(export_results(r))) as z:
        data = json.loads(z.read("analysis.json"))
        assert data["config"] == r.config.model_dump(mode="json")
        assert len(data["results"]) == 15


def test_raa_independent_chainladder_and_bf():
    import chainladder as cl

    sample = cl.load_sample("raa")
    a = sample.values[0, 0]
    n = len(a)
    rows = [
        {
            "origin": str(1981 + i),
            "development": j + 1,
            "paid": float(a[i, j]) if i + j < n else None,
            "incurred": None,
            "count": None,
            "state": "observed" if i + j < n else "future",
        }
        for i in range(n)
        for j in range(n)
    ]
    t = load_triangle(pl.DataFrame(rows), valuation=date(1990, 12, 31))
    cfg = AnalysisConfig(priors={o: 28000 for o in t.origins})
    r = run_reserving(t, cfg)
    np.testing.assert_allclose(
        r.results.filter(pl.col("method") == "paid_cl")["ultimate"].to_numpy(),
        cl.Chainladder().fit(sample).ultimate_.values.flatten(),
        rtol=1e-10,
    )
    benchmark = cl.BornhuetterFerguson(apriori=0.7).fit(
        sample, sample_weight=sample.latest_diagonal * 0 + 40000
    )
    np.testing.assert_allclose(
        r.results.filter(pl.col("method") == "paid_bf")["ultimate"].to_numpy(),
        benchmark.ultimate_.values.flatten(),
        rtol=1e-10,
    )


def test_observation_review_matches_fit_and_retains_excluded_data():
    from actuarial_library.review import method_impact, observation_pairs

    t = small()
    original = t.paid.copy()
    cfg = DevelopmentConfig(excluded=[("2024", 1)], window=1, rationale="Unusual settlement")
    pairs = observation_pairs(t, "paid", cfg)
    age = pairs.filter(pl.col("development") == 1)
    assert age["status"].to_list() == ["Used", "Excluded"]
    assert age["volume_weight"].to_list() == [1.0, None]
    assert age["selected_factor"].to_list() == [1.5, 1.5]
    np.testing.assert_equal(t.paid, original)
    windowed = observation_pairs(t, "paid", DevelopmentConfig(window=1))
    assert windowed.filter(pl.col("development") == 1)["status"].to_list() == ["Outside window", "Used"]
    t.paid[0, 0] = 0
    assert observation_pairs(t, "paid", cfg)["status"][0] == "Invalid / missing"
    baseline = run_reserving(small())
    changed = run_reserving(small(), AnalysisConfig(paid=DevelopmentConfig(tail=1.1, rationale="Tail")))
    delta = method_impact(baseline, changed).filter(pl.col("method") == "paid_cl")
    assert delta["ultimate_change"].to_list() == pytest.approx([18, 21.6, 28.8])
