"""Apply an explicit human selection to an already-saved reserving analysis."""

import math
from copy import deepcopy

import polars as pl

from .models import AnalysisResult

METHODS = {"paid_cl", "incurred_cl", "paid_bf", "incurred_bf", "frequency_severity"}


def _finite(value):
    if value is None:
        return False
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def select_reserve(
    saved: AnalysisResult,
    origin: str,
    method: str,
    note: str,
    manual_ultimate: float | None = None,
) -> AnalysisResult:
    """Return a copy of a saved analysis with one origin's human selection changed.

    No reserving engine is called. Method choices use the saved method row; manual
    selections calculate outstanding and additional reserve from the saved latest
    paid and incurred amounts.
    """
    if not isinstance(note, str) or not note.strip():
        raise ValueError("A nonblank note is required for every selection action.")
    note = note.strip()
    if method not in METHODS | {"manual", "clear"}:
        raise ValueError(f"Unknown selection method: {method}.")
    if method == "manual":
        if isinstance(manual_ultimate, bool) or not _finite(manual_ultimate):
            raise ValueError("Manual selection requires a finite manual ultimate.")
        manual_ultimate = float(manual_ultimate)
    elif manual_ultimate is not None:
        raise ValueError("Manual ultimate can only be supplied for a manual selection.")

    origin_rows = saved.results.filter(pl.col("origin") == origin)
    if origin_rows.is_empty():
        raise ValueError(f"Unknown origin: {origin}.")

    result_rows = saved.results.filter(
        ~((pl.col("origin") == origin) & (pl.col("method") == "manual"))
    )
    is_target = pl.col("origin") == origin
    if method == "clear":
        results = result_rows.with_columns(
            pl.when(is_target).then(pl.lit(False)).otherwise(pl.col("selected")).alias("selected"),
            pl.when(is_target).then(pl.lit("")).otherwise(pl.col("selection_note")).alias("selection_note"),
        )
    elif method in METHODS:
        target = origin_rows.filter(pl.col("method") == method)
        if target.is_empty() or not _finite(target["ultimate"][0]) or not _finite(target["outstanding"][0]):
            raise ValueError(f"Selected method {method} is unavailable for {origin}.")
        results = result_rows.with_columns(
            pl.when(is_target)
            .then(pl.col("method") == method)
            .otherwise(pl.col("selected"))
            .alias("selected"),
            pl.when(is_target & (pl.col("method") == method))
            .then(pl.lit(note))
            .when(is_target)
            .then(pl.lit(""))
            .otherwise(pl.col("selection_note"))
            .alias("selection_note"),
        )
    else:
        source = next(
            (
                row
                for row in origin_rows.iter_rows(named=True)
                if _finite(row.get("paid")) and _finite(row.get("incurred"))
            ),
            None,
        )
        if source is None:
            raise ValueError(f"Saved paid and incurred amounts are unavailable for {origin}.")
        ultimate = manual_ultimate
        outstanding = ultimate - float(source["paid"])
        additional_reserve = ultimate - float(source["incurred"])
        if not _finite(outstanding) or not _finite(additional_reserve):
            raise ValueError("Manual selection arithmetic must remain finite.")
        manual_row = {
            **source,
            "method": "manual",
            "ultimate": ultimate,
            "outstanding": outstanding,
            "additional_reserve": additional_reserve,
            "reason": "",
            "selected": True,
            "selection_note": note,
        }
        results = result_rows.with_columns(
            pl.when(is_target).then(pl.lit(False)).otherwise(pl.col("selected")).alias("selected"),
            pl.when(is_target).then(pl.lit("")).otherwise(pl.col("selection_note")).alias("selection_note"),
        )
        results = pl.concat(
            [results, pl.DataFrame([manual_row], schema=saved.results.schema)],
            how="vertical",
        )

    config = saved.config.model_copy(deep=True)
    config.selections.pop(origin, None)
    config.manual_ultimates.pop(origin, None)
    config.selection_notes.pop(origin, None)
    if method != "clear":
        config.selections[origin] = method
        config.selection_notes[origin] = note
        if method == "manual":
            config.manual_ultimates[origin] = manual_ultimate

    manual_warning_prefix = f"Manual selection for {origin} has negative "
    warnings = [warning for warning in saved.warnings if not warning.startswith(manual_warning_prefix)]
    if method == "manual" and outstanding < 0:
        warnings.append(f"Manual selection for {origin} has negative outstanding reserve ({outstanding:g}).")
    if method == "manual" and additional_reserve < 0:
        warnings.append(f"Manual selection for {origin} has negative additional reserve ({additional_reserve:g}).")

    return AnalysisResult(
        results=results,
        factors=saved.factors.clone(),
        history=saved.history.clone(),
        warnings=warnings,
        config=config,
        metadata=deepcopy(saved.metadata),
    )
