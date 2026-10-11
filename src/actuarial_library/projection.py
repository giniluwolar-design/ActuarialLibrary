"""Deterministic allocation of selected outstanding reserves to future payments."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date

import numpy as np
import polars as pl

from .data import label, period_end, period_index
from .models import (
    AnalysisResult,
    ProjectionConfig,
    Triangle,
)

CONDITIONING_LIMIT = 1e-10
CONDITIONING_VERSION = "projection-conditioning-v1"
_AMOUNT_KEYS = ("claims_hash", "aggregate_hash")


@dataclass
class ProjectionResult:
    rows: list[dict]
    origin_reconciliation: list[dict]
    calendar_totals: list[dict]
    included_origins: list[str]
    excluded_origins: list[dict]
    selection_complete: bool
    full_total: float | None
    config: dict
    metadata: dict
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "rows": self.rows,
            "origin_reconciliation": self.origin_reconciliation,
            "calendar_totals": self.calendar_totals,
            "included_origins": self.included_origins,
            "excluded_origins": self.excluded_origins,
            "selection_complete": self.selection_complete,
            "full_total": self.full_total,
            "config": self.config,
            "metadata": self.metadata,
            "warnings": self.warnings,
        }


def _finite(value):
    return value is not None and math.isfinite(float(value))


def _require_matching_run(triangle: Triangle, result: AnalysisResult):
    n = len(triangle.origins)
    if (
        n == 0
        or len(set(triangle.origins)) != n
        or len(triangle.origin_years) != n
        or triangle.paid.shape != (n, n)
        or triangle.states.shape != (n, n)
        or triangle.grain not in ("Y", "Q")
        or triangle.valuation != period_end(period_index(triangle.valuation, triangle.grain), triangle.grain)
    ):
        raise ValueError("Unsupported triangle geometry or valuation boundary.")
    first = period_index(triangle.valuation, triangle.grain) - n + 1
    expected_origins = [label(first + i, triangle.grain) for i in range(n)]
    if triangle.origins != expected_origins or triangle.origin_years != [int(origin[:4]) for origin in expected_origins]:
        raise ValueError("Triangle origins must be the complete contiguous square through valuation.")
    if any(getattr(triangle, basis).shape != (n, n) for basis in ("paid", "incurred", "count")):
        raise ValueError("Unsupported triangle geometry: all reserving bases must be square and aligned.")
    tm, rm = triangle.metadata, result.metadata
    for key in ("valuation", "currency", "amount_basis"):
        left = tm.get(key)
        right = rm.get(key)
        if left is None or right is None or left != right:
            raise ValueError(f"Triangle and result must have matching {key} metadata.")
    left_hash = next((tm.get(key) for key in _AMOUNT_KEYS if tm.get(key)), None)
    right_hash = next((rm.get(key) for key in _AMOUNT_KEYS if rm.get(key)), None)
    if left_hash is None or right_hash is None or left_hash != right_hash:
        raise ValueError("Triangle and result must have the same non-empty input snapshot hash.")
    if rm.get("grain") != tm.get("grain") or tm.get("grain") != triangle.grain:
        raise ValueError("Triangle and result must have matching grain metadata.")
    if rm.get("valuation") != triangle.valuation.isoformat():
        raise ValueError("Triangle and result valuation does not match the input triangle.")


def _selected_rows(triangle: Triangle, result: AnalysisResult):
    if "origin" not in result.results.columns or set(result.results["origin"].to_list()) != set(triangle.origins):
        raise ValueError("Triangle and result must contain the same origin set.")
    selected = result.results.filter(pl.col("selected"))
    by_origin = {}
    for row in selected.iter_rows(named=True):
        origin = row.get("origin")
        if origin not in triangle.origins:
            raise ValueError(f"Selected result contains unknown origin {origin!r}.")
        if origin in by_origin:
            raise ValueError(f"More than one explicitly selected result for origin {origin}.")
        if row.get("method") != result.config.selections.get(origin):
            raise ValueError(f"Selected result for {origin} does not match its configured selection.")
        by_origin[origin] = row
    return by_origin


def _paid_cdfs(result: AnalysisResult, n: int):
    paid = result.factors.filter(pl.col("basis") == "paid").sort("development")
    cdfs = [None] * n
    for row in paid.iter_rows(named=True):
        development = row.get("development")
        if isinstance(development, int) and 1 <= development <= n:
            cdfs[development - 1] = row.get("cdf")
    if len(cdfs) != n or any(not _finite(value) or float(value) <= 0 for value in cdfs):
        return None
    return [float(value) for value in cdfs]


def _currency_tolerance(currency, outstanding, amounts, minor_unit):
    scale = max(abs(outstanding), sum(abs(value) for value in amounts))
    if currency == "EUR":
        return max(0.01, 1e-12 * scale)
    if minor_unit is None:
        return None
    return max(10.0 ** (-minor_unit), 1e-12 * scale)


def _standard_components(
    *, triangle, origin, i, outstanding, cdfs, config, output_grain, currency
):
    n = len(triangle.origins)
    age = n - i
    p = [1 / cdf for cdf in cdfs]
    increments = [p[j] - p[j - 1] for j in range(age, n)]
    tail_increment = 1 - p[-1]
    increments.append(tail_increment)
    remaining = 1 - p[age - 1]
    if not all(math.isfinite(value) for value in increments + [remaining]):
        return None, "non_finite_pattern", "Paid pattern contains a non-finite coefficient."
    if abs(sum(increments) - remaining) > 1e-12 * max(1.0, sum(abs(v) for v in increments), abs(remaining)):
        return None, "pattern_reconciliation_error", "Future increments do not reconcile to the selected CDF."
    if remaining == 0:
        if outstanding == 0 and all(value == 0 for value in increments):
            return [], None, None
        return None, "zero_remaining_share", "A zero remaining share cannot scale a nonzero or cancelling reserve."
    kappa = max(1.0, sum(abs(value) for value in increments) / abs(remaining))
    if kappa * np.finfo(float).eps > CONDITIONING_LIMIT:
        return None, "UNSTABLE_PATTERN_NORMALIZATION", "Signed pattern normalization exceeds the conditioning limit."
    amounts = [outstanding * value / remaining for value in increments]
    if not all(math.isfinite(value) for value in amounts):
        return None, "UNSTABLE_PATTERN_NORMALIZATION", "Pattern normalization produced a non-finite payment."
    if output_grain == "Q" and triangle.grain == "Y":
        return None, "missing_quarterly_pattern", "Annual observations cannot be split into quarters without an external schedule."
    base = period_index(triangle.valuation, triangle.grain) - n + 1 + i
    components = []
    for offset, amount in enumerate(amounts[:-1]):
        if amount == 0 and increments[offset] == 0:
            continue
        step_age = age + offset + 1
        idx = base + step_age - 1
        if triangle.grain != output_grain:
            # Quarterly-to-annual display aggregates dates after preserving the detailed quarter row.
            payment_date = period_end(idx, triangle.grain)
        else:
            payment_date = period_end(idx, triangle.grain)
        components.append({
            "payment_date": payment_date,
            "amount": amount,
            "development": step_age,
            "is_tail": False,
            "coefficient": increments[offset] / remaining,
            "coverage_ages": [step_age],
            "tail_timing": config.tail_timing,
            "source": "selected paid development factors",
            "rationale": "Paid CDF increments allocated to the selected outstanding reserve.",
        })
    if tail_increment != 0:
        if config.tail_timing == "undated_pending":
            components.append({
                "payment_date": None,
                "amount": amounts[-1],
                "development": n + 1,
                "is_tail": True,
                "coefficient": tail_increment / remaining,
                "coverage_ages": [n + 1],
                "tail_timing": "undated_pending",
                "source": "selected paid development factors",
                "rationale": "Tail amount is calculated but payment timing is pending.",
            })
        elif config.tail_timing == "selected_next_development_period":
            idx = base + n
            components.append({
                "payment_date": period_end(idx, triangle.grain),
                "amount": amounts[-1],
                "development": n + 1,
                "is_tail": True,
                "coefficient": tail_increment / remaining,
                "coverage_ages": [n + 1],
                "tail_timing": config.tail_timing,
                "source": "selected paid development factors",
                "rationale": config.tail_rationale,
            })
        else:
            return None, "missing_external_tail", "External tail timing was selected but no external origin pattern was supplied."
    return components, None, None


def _external_components(triangle, origin, outstanding, age, cdfs, pattern):
    components = sorted(pattern.components, key=lambda component: component.payment_date)
    if any(component.payment_date <= triangle.valuation for component in components):
        return None, "external_date_not_future", "Every external payment date must be strictly after valuation."
    if not set(range(age + 1, len(triangle.origins) + 2)).issubset(set(pattern.coverage_ages)):
        return None, "external_coverage_incomplete", "External pattern does not cover every future development age."
    if pattern.value_type == "amount":
        amounts = [float(component.value) for component in components]
        coefficients = [None] * len(components)
    elif pattern.weight_semantics == "future_conditional":
        weights = [float(component.value) for component in components]
        if abs(sum(weights) - 1) > 1e-9:
            return None, "external_weights_not_normalized", "Future-conditional external weights must sum to one."
        kappa = max(1.0, sum(abs(weight) for weight in weights))
        if kappa * np.finfo(float).eps > CONDITIONING_LIMIT:
            return None, "UNSTABLE_PATTERN_NORMALIZATION", "External normalization exceeds the conditioning limit."
        coefficients = weights
        amounts = [outstanding * weight for weight in weights]
    else:
        p_age = 1 / cdfs[age - 1]
        cumulative = [float(component.value) for component in components]
        if not cumulative or abs(cumulative[-1] - 1) > 1e-9:
            return None, "external_cumulative_incomplete", "Cumulative external proportions must end at one."
        previous = p_age
        increments = []
        for value in cumulative:
            increments.append(value - previous)
            previous = value
        remaining = 1 - p_age
        if remaining == 0:
            return None, "zero_remaining_share", "Cumulative external weights cannot scale a zero remaining share."
        kappa = max(1.0, sum(abs(value) for value in increments) / abs(remaining))
        if kappa * np.finfo(float).eps > CONDITIONING_LIMIT:
            return None, "UNSTABLE_PATTERN_NORMALIZATION", "External normalization exceeds the conditioning limit."
        coefficients = [increment / remaining for increment in increments]
        amounts = [outstanding * coefficient for coefficient in coefficients]
    if len(amounts) != len(components) or not all(math.isfinite(value) for value in amounts):
        return None, "non_finite_pattern", "External pattern contains a non-finite amount or coefficient."
    rows = []
    for component, amount, coefficient in zip(components, amounts, coefficients, strict=True):
        rows.append({
            "payment_date": component.payment_date,
            "amount": amount,
            "development": component.age,
            "is_tail": False,
            "coefficient": coefficient,
            "coverage_ages": pattern.coverage_ages,
            "tail_timing": f"external:{pattern.name}",
            "source": pattern.source,
            "rationale": pattern.rationale,
        })
    return rows, None, None


def project_payments(
    triangle: Triangle, result: AnalysisResult, config: ProjectionConfig | None = None
) -> ProjectionResult:
    """Project only explicitly selected outstanding amounts using the selected paid pattern."""
    config = config or ProjectionConfig()
    _require_matching_run(triangle, result)
    n = len(triangle.origins)
    cdfs = _paid_cdfs(result, n)
    if cdfs is None:
        raise ValueError("A complete finite selected paid CDF is required for projection.")
    selected = _selected_rows(triangle, result)
    unknown_patterns = set(config.external_patterns) - set(triangle.origins)
    if unknown_patterns:
        raise ValueError(f"External patterns contain unknown origins: {sorted(unknown_patterns)}.")
    output_grain = config.output_grain or triangle.grain
    rows, recs, included, excluded, warnings = [], [], [], [], []
    pending_present = False
    currency = triangle.metadata["currency"]
    for i, origin in enumerate(triangle.origins):
        selected_row = selected.get(origin)
        if selected_row is None:
            excluded.append({"origin": origin, "reason_code": "selection_missing", "reason": "No explicit result selection exists for this origin."})
            continue
        outstanding = selected_row.get("outstanding")
        if not _finite(outstanding):
            excluded.append({"origin": origin, "reason_code": "selected_result_unavailable", "reason": selected_row.get("reason") or "Selected outstanding reserve is unavailable."})
            continue
        outstanding = float(outstanding)
        age = n - i
        pattern = config.external_patterns.get(origin)
        if pattern is not None:
            components, reason_code, reason = _external_components(triangle, origin, outstanding, age, cdfs, pattern)
        elif output_grain == "Q" and triangle.grain == "Y":
            components, reason_code, reason = None, "missing_quarterly_pattern", "Annual observations cannot be split into quarters without an external schedule."
        elif config.tail_timing == "external":
            components, reason_code, reason = None, "missing_external_pattern", "Selected external timing has no schedule for this origin."
        else:
            components, reason_code, reason = _standard_components(
                triangle=triangle,
                origin=origin,
                i=i,
                outstanding=outstanding,
                cdfs=cdfs,
                config=config,
                output_grain=output_grain,
                currency=currency,
            )
        if reason_code:
            excluded.append({"origin": origin, "reason_code": reason_code, "reason": reason})
            continue
        amounts = [float(row["amount"]) for row in components if row["payment_date"] is not None]
        pending_amount = sum(float(row["amount"]) for row in components if row["payment_date"] is None)
        has_pending = any(row["payment_date"] is None for row in components)
        pending_present = pending_present or has_pending
        dated_total = sum(amounts)
        tolerance = _currency_tolerance(currency, outstanding, [float(r["amount"]) for r in components], config.currency_minor_unit)
        if tolerance is None:
            excluded.append({"origin": origin, "reason_code": "currency_tolerance_missing", "reason": f"Currency {currency} requires explicit minor-unit metadata for reconciliation."})
            continue
        diff = dated_total + pending_amount - outstanding
        if abs(diff) > tolerance:
            excluded.append({"origin": origin, "reason_code": "amount_reconciliation_error", "reason": "Dated and pending payments do not reconcile to selected outstanding."})
            recs.append({"origin": origin, "method": selected_row["method"], "selected_outstanding": outstanding, "dated_payments": dated_total, "pending_amount": pending_amount, "difference": diff, "tolerance": tolerance, "status": "error"})
            continue
        recs.append({"origin": origin, "method": selected_row["method"], "selected_outstanding": outstanding, "dated_payments": dated_total, "pending_amount": pending_amount, "difference": diff, "tolerance": tolerance, "status": "ok"})
        if has_pending:
            excluded.append({
                "origin": origin,
                "reason_code": "tail_timing_pending",
                "reason": "Tail amount is shown without a date and is excluded from dated calendar totals.",
            })
            warnings.append(f"{origin}: tail amount has no assigned payment date.")
        else:
            included.append(origin)
        for component in components:
            payment_date = component["payment_date"]
            period = label(period_index(payment_date, output_grain), output_grain) if payment_date else None
            row = {
                "origin": origin,
                "method": selected_row["method"],
                "development": component["development"],
                "payment_date": payment_date.isoformat() if payment_date else None,
                "period": period,
                "amount": float(component["amount"]),
                "coefficient": component["coefficient"],
                "coverage_origins": [origin],
                "coverage_ages": component["coverage_ages"],
                "is_tail": component["is_tail"],
                "tail_timing": component["tail_timing"],
                "source": component["source"],
                "rationale": component["rationale"],
                "diagnosis": None,
            }
            if row["amount"] < 0:
                row["diagnosis"] = (
                    "negative implied payment: paid factor below one at age m"
                    if row["coefficient"] is not None and row["coefficient"] < 0
                    else "negative outstanding base retained"
                )
                warnings.append(f"{origin}: negative component retained in signed projection.")
            rows.append(row)
    selection_complete = not excluded and not pending_present and len(included) == n
    totals = {}
    for row in rows:
        if row["payment_date"] is None:
            continue
        date_value = date.fromisoformat(row["payment_date"])
        period = label(period_index(date_value, output_grain), output_grain)
        totals[period] = totals.get(period, 0.0) + row["amount"]
    calendar_totals = [
        {"period": period, "amount": totals[period], "grain": output_grain}
        for period in sorted(totals)
    ]
    dated_total = sum(row["amount"] for row in rows if row["payment_date"] is not None)
    calendar_sum = sum(row["amount"] for row in calendar_totals)
    if abs(calendar_sum - dated_total) > max(1e-12, 1e-12 * max(abs(calendar_sum), abs(dated_total))):
        raise ArithmeticError("Calendar totals do not reconcile to dated origin payments.")
    if any(row["amount"] < 0 for row in rows):
        warnings.append("Calendar totals are net sums and include negative components.")
    metadata = {
        "valuation": triangle.valuation.isoformat(),
        "currency": currency,
        "amount_basis": triangle.metadata["amount_basis"],
        "input_hash": next(triangle.metadata[key] for key in _AMOUNT_KEYS if triangle.metadata.get(key)),
        "currency_minor_unit": config.currency_minor_unit,
        "source_version": result.metadata.get("version"),
        "conditioning_version": CONDITIONING_VERSION,
        "conditioning_limit": CONDITIONING_LIMIT,
        "tolerance_rule": "EUR max(0.01, 1e-12*scale); other currencies require currency_minor_unit",
    }
    return ProjectionResult(
        rows=rows,
        origin_reconciliation=recs,
        calendar_totals=calendar_totals,
        included_origins=included,
        excluded_origins=excluded,
        selection_complete=selection_complete,
        full_total=dated_total if selection_complete else None,
        config=config.model_dump(mode="json"),
        metadata=metadata,
        warnings=sorted(set(warnings)),
    )
