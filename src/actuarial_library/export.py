"""Portable, local analysis packages; no executable object serialization."""

import io
import json
import zipfile
from pathlib import Path

from .models import AnalysisResult


def safe_csv(frame):
    # Prevent text identifiers/notes from becoming formulas when opened in a spreadsheet.
    import polars as pl

    expressions = [
        pl.col(c).map_elements(
            lambda s: "'" + s if s.lstrip().startswith(("=", "+", "-", "@")) else s, return_dtype=pl.String
        )
        for c, dtype in frame.schema.items()
        if dtype == pl.String
    ]
    return frame.with_columns(expressions).write_csv() if expressions else frame.write_csv()


def export_results(result: AnalysisResult, path: str | Path | None = None) -> bytes:
    """ZIP containing CSV results/factors/calibration and complete JSON run metadata."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as z:
        for name in ("results", "factors", "history"):
            z.writestr(name + ".csv", safe_csv(getattr(result, name)))
        z.writestr("analysis.json", json.dumps(result.to_dict(), indent=2, allow_nan=False))
    payload = buffer.getvalue()
    if path is not None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_bytes(payload)
    return payload


def export_google_sheets_package(result: AnalysisResult) -> bytes:
    """Portable ZIP for Google Sheets or any spreadsheet app.

    Each CSV opens as a separate Google Sheets tab after import. No Excel runtime
    or formula recalculation is required.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("results.csv", safe_csv(result.results))
        archive.writestr("development_factors.csv", safe_csv(result.factors))
        archive.writestr("historical_calibration.csv", safe_csv(result.history))
        archive.writestr("analysis.json", json.dumps(result.to_dict(), indent=2, allow_nan=False))
        archive.writestr(
            "README.txt",
            "Import each CSV into its own Google Sheets tab. analysis.json contains the complete "
            "typed assumptions, metadata and diagnostics. CSVs are values-only exports; the worked "
            "formula workbook remains a separate educational example.",
        )
    return buffer.getvalue()
