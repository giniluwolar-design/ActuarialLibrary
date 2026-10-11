from datetime import date

import numpy as np
import polars as pl
import pytest

from actuarial_library.models import (
    AnalysisConfig,
    DevelopmentConfig,
    ExternalOriginPattern,
    ProjectionComponent,
    ProjectionConfig,
    Triangle,
)
from actuarial_library.projection import (
    project_payments,
)
from actuarial_library.reserving import run_reserving


def annual_triangle(*, paid=None, metadata=None):
    paid = paid or [[100, 200, 240], [120, 240, np.nan], [150, np.nan, np.nan]]
    return Triangle(
        origins=["2023", "2024", "2025"],
        origin_years=[2023, 2024, 2025],
        grain="Y",
        valuation=date(2025, 12, 31),
        paid=np.array(paid, dtype=float),
        incurred=np.array(paid, dtype=float) + np.where(np.isfinite(paid), 10, 0),
        count=np.array([[2, 3, 3], [2, 3, np.nan], [1, np.nan, np.nan]], dtype=float),
        states=np.array(
            [["observed", "observed", "observed"], ["observed", "observed", "future"], ["observed", "future", "future"]]
        ),
        metadata={
            "portfolio": "Motor",
            "currency": "EUR",
            "amount_basis": "after_deductible",
            "claims_hash": "snapshot-abc",
            "coverage_hash": "coverage-def",
            "grain": "Y",
            "valuation": "2025-12-31",
            **(metadata or {}),
        },
    )


def run(triangle, config=None):
    return run_reserving(
        triangle,
        config
        or AnalysisConfig(
            paid=DevelopmentConfig(tail=1.25, rationale="Worked example tail."),
            selections={origin: "paid_cl" for origin in triangle.origins},
        ),
    )


def test_projection_calendar_mapping_reconciles_and_to_dict_has_contract_fields():
    triangle = annual_triangle()
    result = run(triangle)
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(
            tail_timing="selected_next_development_period",
            tail_rationale="Place the tail in the next development period.",
        ),
    )
    periods = {row["period"]: row["amount"] for row in projected.calendar_totals}
    assert periods == pytest.approx({"2026": 258, "2027": 132, "2028": 90})
    assert projected.full_total == pytest.approx(480)
    assert all(row["status"] == "ok" for row in projected.origin_reconciliation)
    assert projected.selection_complete
    assert {
        "rows",
        "origin_reconciliation",
        "calendar_totals",
        "included_origins",
        "excluded_origins",
        "selection_complete",
        "full_total",
        "config",
        "metadata",
        "warnings",
    } <= projected.to_dict().keys()
    assert all(row["source"] and row["rationale"] for row in projected.rows)
    assert all(row["coverage_origins"] == [row["origin"]] and row["coverage_ages"] for row in projected.rows)


def test_projection_bf_uses_selected_outstanding_base():
    triangle = annual_triangle()
    config = AnalysisConfig(
        paid=DevelopmentConfig(tail=1.25, rationale="Worked example tail."),
        priors={"2024": 300},
        selections={"2023": "paid_cl", "2024": "paid_bf", "2025": "paid_cl"},
    )
    result = run(triangle, config)
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    actual = [row["amount"] for row in projected.rows if row["origin"] == "2024"]
    assert actual == pytest.approx([40, 60])
    assert projected.origin_reconciliation[1]["selected_outstanding"] == pytest.approx(100)


def test_signed_factor_below_one_retains_negative_minus12_plus57():
    triangle = annual_triangle()
    config = AnalysisConfig(
        paid=DevelopmentConfig(overrides={2: 0.95}, tail=1.25, rationale="Approved signed development example."),
        selections={origin: "paid_cl" for origin in triangle.origins},
    )
    result = run(triangle, config)
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    row = [r for r in projected.rows if r["origin"] == "2024"]
    assert [r["amount"] for r in row] == pytest.approx([-12, 57])
    assert row[0]["diagnosis"] == "negative implied payment: paid factor below one at age m"
    assert projected.origin_reconciliation[1]["status"] == "ok"


def test_default_tail_is_pending_and_suppresses_full_total():
    triangle = annual_triangle()
    projected = project_payments(triangle, run(triangle))
    assert any(row["payment_date"] is None and row["is_tail"] for row in projected.rows)
    assert projected.full_total is None
    assert not projected.selection_complete
    assert {item["reason_code"] for item in projected.excluded_origins} == {"tail_timing_pending"}


def test_only_explicitly_selected_rows_are_projected_and_partial_total_suppressed():
    triangle = annual_triangle()
    result = run(triangle, AnalysisConfig(selections={"2023": "paid_cl", "2024": "paid_cl"}))
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    assert projected.included_origins == ["2023", "2024"]
    assert projected.excluded_origins == [
        {"origin": "2025", "reason_code": "selection_missing", "reason": "No explicit result selection exists for this origin."}
    ]
    assert projected.full_total is None


def test_projection_keeps_origin_with_complete_age_cdf_when_other_ages_missing():
    triangle = annual_triangle(paid=[[0, 200, 240], [0, 240, np.nan], [150, np.nan, np.nan]])
    result = run_reserving(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(tail=1.25, rationale="Partial CDF fixture."),
            selections={"2023": "paid_cl", "2025": "manual"},
            manual_ultimates={"2025": 450},
            selection_notes={"2025": "Explicitly selected manual ultimate."},
        ),
    )

    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(
            tail_timing="selected_next_development_period",
            tail_rationale="Next period for the selected origin.",
        ),
    )

    assert len(projected.rows) == 1
    assert projected.rows[0]["origin"] == "2023"
    assert projected.rows[0]["payment_date"] == "2026-12-31"
    assert projected.rows[0]["amount"] == pytest.approx(60)
    assert projected.included_origins == ["2023"]
    assert {
        (item["origin"], item["reason_code"])
        for item in projected.excluded_origins
    } == {("2024", "selection_missing"), ("2025", "paid_cdf_unavailable")}
    assert projected.full_total is None


@pytest.mark.parametrize(
    ("value_type", "weight_semantics", "values", "expected_amounts"),
    [
        ("amount", None, [100, 200], [100, 200]),
        ("weight", "future_conditional", [0.25, 0.75], [75, 225]),
    ],
)
def test_external_amount_and_future_weights_do_not_require_paid_cdf(
    value_type, weight_semantics, values, expected_amounts
):
    triangle = annual_triangle(paid=[[0, 200, 240], [0, 240, np.nan], [150, np.nan, np.nan]])
    result = run_reserving(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(tail=1.25, rationale="External schedule fixture."),
            selections={"2025": "manual"},
            manual_ultimates={"2025": 450},
            selection_notes={"2025": "Independent selected ultimate."},
        ),
    )
    pattern = ExternalOriginPattern(
        value_type=value_type,
        weight_semantics=weight_semantics,
        components=[
            ProjectionComponent(payment_date=date(2026, 3, 31), value=values[0]),
            ProjectionComponent(payment_date=date(2026, 9, 30), value=values[1]),
        ],
        coverage_ages=[2, 3, 4],
        source="External schedule",
        rationale="Explicitly dated future pattern.",
    )
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(output_grain="Q", external_patterns={"2025": pattern}),
    )
    assert [row["amount"] for row in projected.rows] == pytest.approx(expected_amounts)
    assert projected.excluded_origins == [
        {"origin": "2023", "reason_code": "selection_missing", "reason": "No explicit result selection exists for this origin."},
        {"origin": "2024", "reason_code": "selection_missing", "reason": "No explicit result selection exists for this origin."},
    ]


def test_cumulative_external_pattern_only_requires_current_age_cdf():
    triangle = annual_triangle(paid=[[0, 200, 240], [0, 240, np.nan], [150, np.nan, np.nan]])
    result = run_reserving(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(tail=1.25, rationale="Cumulative external fixture."),
            selections={"2025": "manual"},
            manual_ultimates={"2025": 450},
            selection_notes={"2025": "Independent selected ultimate."},
        ),
    )
    pattern = ExternalOriginPattern(
        value_type="weight",
        weight_semantics="cumulative_development",
        components=[
            ProjectionComponent(payment_date=date(2026, 3, 31), value=0.6),
            ProjectionComponent(payment_date=date(2027, 3, 31), value=1.0),
        ],
        coverage_ages=[2, 3, 4],
        source="Cumulative schedule",
        rationale="Cumulative proportions use the valuation age CDF.",
    )
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(external_patterns={"2025": pattern}),
    )
    assert not projected.rows
    assert any(
        item["origin"] == "2025" and item["reason_code"] == "paid_cdf_unavailable"
        for item in projected.excluded_origins
    )


def test_annual_triangle_does_not_invent_quarterly_split():
    triangle = annual_triangle()
    projected = project_payments(
        triangle,
        run(triangle),
        ProjectionConfig(output_grain="Q", tail_timing="selected_next_development_period", tail_rationale="Quarterly requested."),
    )
    assert not projected.rows
    assert {item["reason_code"] for item in projected.excluded_origins} == {"missing_quarterly_pattern"}
    assert projected.full_total is None


def test_quarterly_triangle_projects_to_quarter_period_ends():
    triangle = Triangle(
        origins=["2025Q3", "2025Q4"],
        origin_years=[2025, 2025],
        grain="Q",
        valuation=date(2025, 12, 31),
        paid=np.array([[10.0, 20.0], [15.0, np.nan]]),
        incurred=np.array([[12.0, 22.0], [17.0, np.nan]]),
        count=np.array([[1.0, 2.0], [1.0, np.nan]]),
        states=np.array([["observed", "observed"], ["observed", "future"]]),
        metadata={
            "portfolio": "Motor",
            "currency": "EUR",
            "amount_basis": "after_deductible",
            "claims_hash": "quarterly-snapshot",
            "grain": "Q",
            "valuation": "2025-12-31",
        },
    )
    result = run_reserving(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(tail=1.25, rationale="Quarterly tail."),
            selections={origin: "paid_cl" for origin in triangle.origins},
        ),
    )
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next quarter."),
    )
    assert {row["period"] for row in projected.calendar_totals} == {"2026Q1", "2026Q2"}
    assert all(row["payment_date"].endswith(("03-31", "06-30")) for row in projected.rows)


def test_explicit_external_quarterly_amounts_with_irregular_dates_reconcile():
    triangle = annual_triangle()
    result = run(triangle)
    patterns = {
        "2025": ExternalOriginPattern(
            value_type="amount",
            components=[
                ProjectionComponent(payment_date=date(2026, 2, 17), value=90),
                ProjectionComponent(payment_date=date(2026, 8, 2), value=210),
            ],
            coverage_ages=[2, 3, 4],
            source="Actuarial pattern v1",
            rationale="Explicit dated schedule for annual origin.",
        )
    }
    # The other origins need explicit patterns as well for a complete output-grain change.
    for origin in ("2023", "2024"):
        patterns[origin] = ExternalOriginPattern(
            value_type="weight",
            weight_semantics="future_conditional",
            components=[
                ProjectionComponent(payment_date=date(2026, 1, 31), value=0.4),
                ProjectionComponent(payment_date=date(2027, 6, 30), value=0.6),
            ],
            coverage_ages=[2, 3, 4],
            source="Actuarial pattern v1",
            rationale="Explicit future-conditional weights.",
        )
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(output_grain="Q", external_patterns=patterns),
    )
    assert projected.selection_complete
    assert projected.full_total == pytest.approx(480)
    assert any(row["payment_date"] == "2026-02-17" and row["period"] == "2026Q1" for row in projected.rows)
    assert all(row["payment_date"] for row in projected.rows)


def test_signed_external_plus100_minus100_schedule_reconciles_zero():
    triangle = annual_triangle()
    result = run(triangle, AnalysisConfig(selections={o: "paid_cl" for o in triangle.origins}))
    # A test result with an explicitly selected zero outstanding preserves a signed recovery schedule.
    results = result.results.with_columns(
        pl.when(pl.col("origin") == "2025").then(0.0).otherwise(pl.col("outstanding")).alias("outstanding")
    )
    result = result.__class__(results, result.factors, result.history, result.warnings, result.config, result.metadata)
    pattern = ExternalOriginPattern(
        value_type="amount",
        components=[
            ProjectionComponent(payment_date=date(2026, 3, 31), value=100),
            ProjectionComponent(payment_date=date(2027, 3, 31), value=-100),
        ],
        coverage_ages=[2, 3, 4],
        source="Signed recovery scenario",
        rationale="Independently evidenced offsetting recoveries.",
    )
    projected = project_payments(triangle, result, ProjectionConfig(external_patterns={"2025": pattern}))
    payments = [row["amount"] for row in projected.rows if row["origin"] == "2025"]
    assert payments == [100, -100]
    assert projected.origin_reconciliation[2]["status"] == "ok"


def test_external_cumulative_proportions_are_conditioned_at_valuation():
    triangle = annual_triangle()
    result = run(triangle)
    pattern = ExternalOriginPattern(
        value_type="weight",
        weight_semantics="cumulative_development",
        components=[
            ProjectionComponent(payment_date=date(2026, 3, 31), value=0.6, age=2),
            ProjectionComponent(payment_date=date(2027, 3, 31), value=0.8, age=3),
            ProjectionComponent(payment_date=date(2028, 3, 31), value=1.0, age=4),
        ],
        coverage_ages=[2, 3, 4],
        source="Cumulative development study",
        rationale="Cumulative proportions conditioned at valuation.",
    )
    projected = project_payments(triangle, result, ProjectionConfig(external_patterns={"2025": pattern}))
    amounts = [row["amount"] for row in projected.rows if row["origin"] == "2025"]
    assert amounts == pytest.approx([120, 90, 90])


def test_negative_outstanding_and_subcent_values_are_preserved():
    triangle = annual_triangle()
    negative = run(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(overrides={1: 0.5, 2: 1}, tail=1, rationale="Negative outstanding fixture."),
            selections={origin: "paid_cl" for origin in triangle.origins},
        ),
    )
    negative_projection = project_payments(
        triangle,
        negative,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    negative_rows = [row for row in negative_projection.rows if row["origin"] == "2025"]
    assert sum(row["amount"] for row in negative_rows) == pytest.approx(-75)
    assert all(row["amount"] < 0 for row in negative_rows)
    assert all("negative" in row["diagnosis"] for row in negative_rows)

    manual = AnalysisConfig(
        paid=DevelopmentConfig(tail=1.25, rationale="Worked example tail."),
        selections={"2023": "paid_cl", "2024": "paid_cl", "2025": "manual"},
        manual_ultimates={"2025": 150.000001},
        selection_notes={"2025": "Preserve a subcent outstanding amount."},
    )
    subcent = project_payments(
        triangle,
        run(triangle, manual),
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    rows = [row for row in subcent.rows if row["origin"] == "2025"]
    assert sum(row["amount"] for row in rows) == pytest.approx(0.000001)
    assert any(row["amount"] != 0 for row in rows)


def test_conditioning_guard_blocks_extreme_signed_cancellation():
    triangle = annual_triangle()
    result = run(triangle)
    factors = result.factors.with_columns(
        pl.when((pl.col("basis") == "paid") & (pl.col("development") == 1))
        .then(2.0)
        .when((pl.col("basis") == "paid") & (pl.col("development") == 2))
        .then(1e-6)
        .when((pl.col("basis") == "paid") & (pl.col("development") == 3))
        .then(2.0)
        .otherwise(pl.col("cdf"))
        .alias("cdf")
    )
    # The factor table's CDF field is the public source used by the projection calculation.
    result = result.__class__(result.results, factors, result.history, result.warnings, result.config, result.metadata)
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    assert any(
        item["origin"] == "2025" and item["reason_code"] == "UNSTABLE_PATTERN_NORMALIZATION"
        for item in projected.excluded_origins
    )


def test_non_eur_reconciliation_requires_explicit_minor_unit():
    triangle = annual_triangle(metadata={"currency": "USD"})
    result = run(triangle)
    blocked = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    assert {item["reason_code"] for item in blocked.excluded_origins} == {"currency_tolerance_missing"}
    allowed = project_payments(
        triangle,
        result,
        ProjectionConfig(
            tail_timing="selected_next_development_period",
            tail_rationale="Next period.",
            currency_minor_unit=2,
        ),
    )
    assert allowed.selection_complete


def test_zero_remaining_share_with_cancelling_factor_increments_is_blocked():
    triangle = annual_triangle()
    # 2025 has age 1; use a CDF of one at all ages so the reserve has zero remaining share.
    result = run(
        triangle,
        AnalysisConfig(
            paid=DevelopmentConfig(overrides={1: 2, 2: 0.5}, tail=1, rationale="Cancellation fixture."),
            selections={origin: "paid_cl" for origin in triangle.origins},
        ),
    )
    # Replace the selected latest-origin reserve with zero while retaining a nonzero signed future pattern.
    results = result.results.with_columns(
        pl.when(pl.col("origin") == "2025").then(0.0).otherwise(pl.col("outstanding")).alias("outstanding")
    )
    result = result.__class__(results, result.factors, result.history, result.warnings, result.config, result.metadata)
    projected = project_payments(
        triangle,
        result,
        ProjectionConfig(tail_timing="selected_next_development_period", tail_rationale="Next period."),
    )
    assert any(item["origin"] == "2025" and item["reason_code"] == "zero_remaining_share" for item in projected.excluded_origins)


@pytest.mark.parametrize("field,value", [("valuation", "2024-12-31"), ("currency", "USD"), ("amount_basis", "before_deductible"), ("claims_hash", "other-snapshot")])
def test_projection_rejects_mismatched_result_metadata(field, value):
    triangle = annual_triangle()
    result = run(triangle)
    metadata = {**result.metadata, field: value}
    mismatch = result.__class__(result.results, result.factors, result.history, result.warnings, result.config, metadata)
    with pytest.raises(ValueError, match="matching|same non-empty"):
        project_payments(triangle, mismatch)
