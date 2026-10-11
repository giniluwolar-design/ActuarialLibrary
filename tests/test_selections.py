import copy
from datetime import date

import numpy as np
import polars as pl
import pytest

from actuarial_library.models import AnalysisConfig, DevelopmentConfig, Triangle
from actuarial_library.reserving import run_reserving
from actuarial_library.selections import select_reserve


def saved_result():
    paid = np.array([[100.0, 150.0, 180.0], [120.0, 180.0, np.nan], [160.0, np.nan, np.nan]])
    triangle = Triangle(
        ["2023", "2024", "2025"],
        [2023, 2024, 2025],
        "Y",
        date(2025, 12, 31),
        paid,
        paid + np.where(np.isfinite(paid), 10.0, 0.0),
        np.array([[2.0, 3.0, 3.0], [3.0, 3.0, np.nan], [2.0, np.nan, np.nan]]),
        np.where(np.isfinite(paid), "observed", "future"),
        metadata={"valuation": "2025-12-31", "currency": "EUR", "amount_basis": "after_deductible"},
    )
    config = AnalysisConfig(
        paid=DevelopmentConfig(tail=1.1, rationale="Saved paid tail."),
        priors={"2023": 210, "2024": 220, "2025": 300},
    )
    return run_reserving(triangle, config)


def test_select_reserve_changes_only_selection_on_saved_result():
    original = saved_result()
    original_results = original.results.clone()
    original_factors = original.factors.clone()
    original_history = original.history.clone()

    selected = select_reserve(original, "2024", "paid_bf", "Reviewed the selected prior.")

    chosen = selected.results.filter((pl.col("origin") == "2024") & pl.col("selected"))
    assert chosen.height == 1
    assert chosen["method"][0] == "paid_bf"
    assert chosen["selection_note"][0] == "Reviewed the selected prior."
    assert selected.config.selections["2024"] == "paid_bf"
    assert selected.config.selection_notes["2024"] == "Reviewed the selected prior."
    assert original.results.equals(original_results)
    assert original.factors.equals(original_factors)
    assert original.history.equals(original_history)
    assert selected.factors.equals(original.factors)
    assert selected.history.equals(original.history)
    assert selected.metadata == original.metadata
    assert selected.results.filter(pl.col("origin") == "2023").equals(
        original.results.filter(pl.col("origin") == "2023")
    )


def test_manual_selection_calculates_signed_reserves_without_flooring():
    original = saved_result()

    selected = select_reserve(original, "2025", "manual", "Independent negative ultimate.", -25.5)

    manual = selected.results.filter((pl.col("origin") == "2025") & (pl.col("method") == "manual"))
    assert manual.height == 1
    assert manual["selected"][0]
    assert manual["ultimate"][0] == pytest.approx(-25.5)
    assert manual["outstanding"][0] == pytest.approx(-185.5)
    assert manual["additional_reserve"][0] == pytest.approx(-195.5)
    assert selected.config.manual_ultimates["2025"] == pytest.approx(-25.5)
    assert selected.config.selections["2025"] == "manual"
    assert any("negative outstanding" in warning for warning in selected.warnings)
    assert any("negative additional" in warning for warning in selected.warnings)


@pytest.mark.parametrize("replacement", ["clear", "paid_cl"])
def test_replacing_negative_manual_selection_removes_only_its_current_warnings(replacement):
    result = saved_result()
    result.metadata["baseline_warning"] = "Preserve the original run warning."
    result.warnings.append("Preserve the original run warning.")
    first = select_reserve(result, "2025", "manual", "Signed manual amount.", -25.5)
    other = select_reserve(first, "2024", "manual", "Other origin remains signed.", -25.5)
    second = select_reserve(other, "2025", replacement, "Replace the first origin's choice.")

    assert first.warnings != second.warnings
    assert "Preserve the original run warning." in second.warnings
    assert any("2024 has negative outstanding" in warning for warning in second.warnings)
    assert not any("2025 has negative" in warning for warning in second.warnings)
    assert any("2025 has negative outstanding" in warning for warning in first.warnings)
    assert "Preserve the original run warning." in result.warnings


def test_manual_selection_rejects_overflowed_saved_arithmetic_without_mutating_result():
    result = saved_result()
    result.results = result.results.with_columns(
        pl.when(pl.col("origin") == "2025").then(pl.lit(-1e308)).otherwise(pl.col("paid")).alias("paid"),
        pl.when(pl.col("origin") == "2025").then(pl.lit(-1e308)).otherwise(pl.col("incurred")).alias("incurred"),
    )
    original_results = result.results.clone()
    with pytest.raises(ValueError, match="finite"):
        select_reserve(result, "2025", "manual", "Overflow guard.", 1e308)
    assert result.results.equals(original_results)


def test_selection_clone_isolates_saved_metadata_and_frames():
    result = saved_result()
    result.metadata["nested"] = {"labels": ["saved"]}
    before_metadata = copy.deepcopy(result.metadata)
    selected = select_reserve(result, "2024", "paid_cl", "Clone saved inputs.")
    selected.metadata["nested"]["labels"].append("changed")
    selected.factors = selected.factors.with_columns(pl.lit(-99.0).alias("selected_copy_only"))
    selected.history = selected.history.with_columns(pl.lit(-99.0).alias("selected_copy_only"))
    assert result.metadata == before_metadata
    assert "selected_copy_only" not in result.factors.columns
    assert "selected_copy_only" not in result.history.columns


def test_clear_and_reselect_preserves_other_origin_and_removes_stale_manual_row():
    original = select_reserve(saved_result(), "2023", "manual", "Manual first origin.", 200)
    selected = select_reserve(original, "2024", "paid_cl", "Select the second origin.")
    cleared = select_reserve(selected, "2023", "clear", "Clear the first origin.")

    assert not cleared.results.filter((pl.col("origin") == "2023") & pl.col("selected")).height
    assert not cleared.results.filter((pl.col("origin") == "2023") & (pl.col("method") == "manual")).height
    other = cleared.results.filter((pl.col("origin") == "2024") & pl.col("selected"))
    assert other.height == 1 and other["method"][0] == "paid_cl"
    assert "2023" not in cleared.config.selections
    assert "2023" not in cleared.config.manual_ultimates
    assert cleared.config.selections["2024"] == "paid_cl"


@pytest.mark.parametrize(
    ("origin", "method", "note", "manual_ultimate", "message"),
    [
        ("unknown", "paid_cl", "reason", None, "Unknown origin"),
        ("2023", "unknown_method", "reason", None, "Unknown selection method"),
        ("2023", "paid_cl", " ", None, "nonblank note"),
        ("2023", "paid_cl", "reason", 100.0, "only be supplied"),
        ("2023", "manual", "reason", None, "requires a finite manual ultimate"),
        ("2023", "manual", "reason", float("inf"), "requires a finite manual ultimate"),
        ("2023", "clear", "reason", 100.0, "only be supplied"),
    ],
)
def test_invalid_selection_inputs_are_rejected(origin, method, note, manual_ultimate, message):
    with pytest.raises(ValueError, match=message):
        select_reserve(saved_result(), origin, method, note, manual_ultimate)


def test_unavailable_saved_method_is_rejected_without_recalculation():
    result = saved_result()
    # The saved frequency/severity row is unavailable for this origin.
    with pytest.raises(ValueError, match="unavailable"):
        select_reserve(result, "2023", "frequency_severity", "Unavailable method.")
