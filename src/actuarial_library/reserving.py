"""Deterministic reserving with inspectable factors, priors and calibration rows."""

import math
from datetime import UTC, datetime

import numpy as np
import polars as pl

from .models import AnalysisConfig, AnalysisResult, DevelopmentConfig, Triangle

METHODS = ("paid_cl", "incurred_cl", "paid_bf", "incurred_bf", "frequency_severity")


def finite(value):
    return float(value) if value is not None and math.isfinite(value) else None


def development(triangle: Triangle, basis: str, config: DevelopmentConfig):
    a = getattr(triangle, basis)
    n = len(triangle.origins)
    if any(k >= n for k in config.overrides):
        raise ValueError("Override age exceeds triangle development range.")
    if any(o not in triangle.origins or d < 1 or d >= n for o, d in config.excluded):
        raise ValueError("Unknown origin or age in development exclusions.")
    selected, rows, warnings = [], [], []
    for j in range(n - 1):
        eligible = [
            i
            for i in range(n - j - 1)
            if np.isfinite(a[i, j])
            and a[i, j] > 0
            and np.isfinite(a[i, j + 1])
            and (triangle.origins[i], j + 1) not in config.excluded
        ]
        if config.window:
            eligible = eligible[-config.window :]
        volume = sum(a[i, j + 1] for i in eligible) / sum(a[i, j] for i in eligible) if eligible else None
        simple = float(np.mean([a[i, j + 1] / a[i, j] for i in eligible])) if eligible else None
        factor = config.overrides.get(j + 1, volume if config.average == "volume" else simple)
        if factor is None or factor <= 0:
            factor = None
            warnings.append(f"{basis} age {j + 1}: no valid positive selected factor.")
        elif factor < 1:
            warnings.append(
                f"{basis} age {j + 1}: selected factor below one; inspect reserve releases/corrections."
            )
        selected.append(factor)
        rows.append(
            {
                "basis": basis,
                "development": j + 1,
                "volume": finite(volume),
                "simple": finite(simple),
                "selected": finite(factor),
                "pairs": len(eligible),
                "origins_used": ", ".join(triangle.origins[i] for i in eligible),
                "override": j + 1 in config.overrides,
                "rationale": config.rationale,
            }
        )
    cdf = [None] * n
    cdf[-1] = config.tail
    for j in range(n - 2, -1, -1):
        cdf[j] = (
            finite(selected[j] * cdf[j + 1]) if selected[j] is not None and cdf[j + 1] is not None else None
        )
    for j, row in enumerate(rows):
        row["cdf"] = cdf[j]
    rows.append(
        {
            "basis": basis,
            "development": n,
            "volume": None,
            "simple": None,
            "selected": config.tail,
            "pairs": 0,
            "origins_used": "Tail assumption",
            "override": config.tail != 1,
            "rationale": config.rationale,
            "cdf": config.tail,
        }
    )
    latest = triangle.latest(basis)
    ultimates = [finite(latest[i] * cdf[n - i - 1]) if cdf[n - i - 1] is not None else None for i in range(n)]
    return ultimates, cdf, rows, warnings


def run_reserving(triangle: Triangle, config: AnalysisConfig | None = None) -> AnalysisResult:
    config = config or AnalysisConfig()
    origins = triangle.origins
    for mapping in [
        config.priors,
        config.selections,
        config.manual_ultimates,
        config.selection_notes,
        config.frequency_severity.expected_counts,
        config.frequency_severity.exposures,
        config.frequency_severity.frequencies,
        config.frequency_severity.historical_counts,
        config.frequency_severity.historical_ultimates,
    ]:
        if set(mapping) - set(origins):
            raise ValueError(f"Unknown origin keys: {sorted(set(mapping) - set(origins))}")
    cl, cdfs, factor_rows, warnings = {}, {}, [], []
    for basis in ("paid", "incurred", "count"):
        cl[basis], cdfs[basis], rows, warn = development(triangle, basis, getattr(config, basis))
        factor_rows.extend(rows)
        warnings.extend(warn)
    fs = config.frequency_severity
    # Independent calibration: never read the final selected ultimate here.
    historical = {}
    for i, origin in enumerate(origins):
        y = triangle.origin_years[i]
        historical.setdefault(y, []).append(
            (
                origin,
                fs.historical_ultimates.get(origin, cl["incurred"][i]),
                fs.historical_counts.get(origin, cl["count"][i]),
            )
        )
    annual = {}
    for year, parts in historical.items():
        complete_year = len(parts) == (1 if triangle.grain == "Y" else 4)
        valid = complete_year and all(u is not None and c is not None for _, u, c in parts)
        annual[year] = (sum(u for _, u, _ in parts), sum(c for _, _, c in parts)) if valid else (None, None)
    n = len(origins)
    latest_paid, latest_inc, latest_count = [triangle.latest(b) for b in ("paid", "incurred", "count")]
    history_rows, result_rows = [], []
    for i, origin in enumerate(origins):
        year = triangle.origin_years[i]
        years = [
            y
            for y in sorted(annual)
            if year - fs.lookback_years <= y < year
            and (fs.historical_years is None or y in fs.historical_years)
        ]
        usable, unusable = [], []
        for y in years:
            u, c = annual[y]
            if u is None or c is None or c <= 0:
                unusable.append(y)
                continue
            trend_factor = (1 + fs.trend) ** (year - y)
            severity = u / c * trend_factor
            usable.append((severity, c))
            history_rows.append(
                {
                    "target": origin,
                    "year": y,
                    "ultimate": u,
                    "count": c,
                    "trend_factor": trend_factor,
                    "trended_severity": severity,
                }
            )
        # Do not silently drop missing/zero-count selected calibration years.
        severity = None
        if usable and not unusable:
            severity = (
                sum(s * c for s, c in usable) / sum(c for _, c in usable)
                if fs.average == "weighted"
                else sum(s for s, _ in usable) / len(usable)
            )
        count = {
            "developed": cl["count"][i],
            "manual": fs.expected_counts.get(origin),
            "reported": finite(latest_count[i]),
        }.get(fs.count_mode)
        if fs.count_mode == "exposure":
            exposure, frequency = fs.exposures.get(origin), fs.frequencies.get(origin)
            count = exposure * frequency if exposure is not None and frequency is not None else None
        expected = finite(severity * count) if severity is not None and count is not None else None
        prior = config.priors.get(origin, expected)
        prior_source = "manual" if origin in config.priors else "frequency_severity"
        estimations = {
            "paid_cl": cl["paid"][i],
            "incurred_cl": cl["incurred"][i],
            "frequency_severity": expected,
        }
        reasons = {}
        if expected is None:
            reasons["frequency_severity"] = (
                f"Unavailable calibration years: {unusable}"
                if unusable
                else "No prior-year calibration or target count available."
            )
        for basis, latest in [("paid", latest_paid), ("incurred", latest_inc)]:
            f = cdfs[basis][n - i - 1]
            remaining = finite(1 - 1 / f) if f is not None and f > 0 else None
            valid = remaining is not None and -1e-12 <= remaining <= 1 + 1e-12
            estimations[basis + "_bf"] = (
                finite(latest[i] + prior * remaining) if valid and prior is not None else None
            )
            if not valid:
                reasons[basis + "_bf"] = (
                    "Invalid BF remaining share: require CDF >= 1. Adjust the development pattern."
                )
            elif prior is None:
                reasons[basis + "_bf"] = "Expected ultimate prior is unavailable."
        selection = config.selections.get(origin, "")
        if selection and selection not in (*METHODS, "manual"):
            raise ValueError(f"Unknown selection {selection} for {origin}.")
        if selection == "manual":
            if origin not in config.manual_ultimates:
                raise ValueError(f"Provide a manual ultimate and note for {origin}.")
            estimations["manual"] = config.manual_ultimates[origin]
        if selection and estimations.get(selection) is None:
            raise ValueError(f"Selected method {selection} is unavailable for {origin}.")
        for method, ultimate in estimations.items():
            p, inc = finite(latest_paid[i]), finite(latest_inc[i])
            outstanding = finite(ultimate - p) if ultimate is not None and p is not None else None
            additional = finite(ultimate - inc) if ultimate is not None and inc is not None else None
            reason = reasons.get(method, "")
            if ultimate is None and not reason:
                reason = "Latest observation or required development factor is unavailable."
            if outstanding is not None and outstanding < 0:
                warnings.append(f"{origin} {method}: negative outstanding reserve; not floored.")
            if additional is not None and additional < 0:
                warnings.append(f"{origin} {method}: negative additional reserve; not floored.")
            result_rows.append(
                {
                    "origin": origin,
                    "method": method,
                    "ultimate": ultimate,
                    "paid": p,
                    "incurred": inc,
                    "case_reserve": finite(inc - p) if p is not None and inc is not None else None,
                    "outstanding": outstanding,
                    "additional_reserve": additional,
                    "expected_count": count,
                    "severity": severity,
                    "prior": prior,
                    "prior_source": prior_source,
                    "history_years": ", ".join(map(str, years)),
                    "reason": reason,
                    "selected": method == selection,
                    "selection_note": config.selection_notes.get(origin, "") if method == selection else "",
                }
            )
    from . import __version__

    return AnalysisResult(
        pl.DataFrame(result_rows),
        pl.DataFrame(factor_rows),
        pl.DataFrame(
            history_rows,
            schema={
                "target": pl.String,
                "year": pl.Int64,
                "ultimate": pl.Float64,
                "count": pl.Float64,
                "trend_factor": pl.Float64,
                "trended_severity": pl.Float64,
            },
        ),
        sorted(set(warnings)),
        config,
        {**triangle.metadata, "version": __version__, "executed_at": datetime.now(UTC).isoformat()},
    )
