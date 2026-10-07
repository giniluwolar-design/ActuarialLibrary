"""Snapshot validation and coverage-aware triangle construction. No inferred history."""

import calendar
import hashlib
from datetime import date

import numpy as np
import polars as pl

from .models import Triangle, ValidationResult

KEY = ["portfolio", "claim_id", "valuation_date"]
GROUP = ["portfolio", "currency", "amount_basis"]
REQUIRED = GROUP + [
    "claim_id",
    "accident_date",
    "report_date",
    "valuation_date",
    "status",
    "paid",
    "case_reserve",
    "deductible",
]
ISSUE_SCHEMA = {"severity": pl.String, "code": pl.String, "row": pl.Int64, "message": pl.String}


def frame_hash(frame):
    return hashlib.sha256(frame.write_csv().encode()).hexdigest()


def period_index(d: date, grain: str) -> int:
    return d.year if grain == "Y" else d.year * 4 + (d.month - 1) // 3


def label(index, grain):
    return str(index) if grain == "Y" else f"{index // 4}Q{index % 4 + 1}"


def period_end(index, grain):
    y, m = (index, 12) if grain == "Y" else (index // 4, 3 * (index % 4 + 1))
    return date(y, m, calendar.monthrange(y, m)[1])


def dates(frame, columns):
    for c in columns:
        if c in frame.columns:
            frame = frame.with_columns(pl.col(c).cast(pl.String).str.to_date("%Y-%m-%d", strict=False))
    return frame


def validate_claims(claims: pl.DataFrame, coverage: pl.DataFrame) -> ValidationResult:
    issues = []

    def issue(code, message, row=None, severity="error"):
        issues.append((severity, code, row, message))

    missing = set(REQUIRED) - set(claims.columns)
    cov_missing = set(GROUP + ["valuation_date", "complete"]) - set(coverage.columns)
    if missing or cov_missing:
        issue("schema", f"Missing claims columns {sorted(missing)}; coverage columns {sorted(cov_missing)}")
        return ValidationResult(claims, coverage, pl.DataFrame(issues, schema=ISSUE_SCHEMA, orient="row"))
    d = dates(claims, ["accident_date", "report_date", "valuation_date"]).with_row_index("_row", offset=2)
    d = d.with_columns(
        [pl.col(c).cast(pl.Float64, strict=False) for c in ["paid", "case_reserve", "deductible"]]
    )
    d = d.with_columns([pl.col(c).cast(pl.String) for c in GROUP + ["claim_id", "status"]])
    cov = dates(coverage, ["valuation_date"])
    cov = cov.with_columns([pl.col(c).cast(pl.String) for c in GROUP])
    cov = cov.with_columns(
        pl.col("complete")
        .cast(pl.String)
        .str.to_lowercase()
        .replace_strict(
            {"true": True, "false": False, "1": True, "0": False}, default=None, return_dtype=pl.Boolean
        )
    )

    def rows(mask, code, message, severity="error"):
        for r in d.filter(mask)["_row"].to_list():
            issue(code, message, r, severity)

    rows(
        pl.any_horizontal([pl.col(c).is_null() for c in REQUIRED]),
        "missing",
        "Required field is missing or malformed.",
    )
    rows(
        pl.any_horizontal([pl.col(c).str.strip_chars() == "" for c in GROUP + ["claim_id"]]),
        "empty_identifier",
        "Identifiers and grouping fields must not be blank.",
    )
    rows(
        pl.any_horizontal([~pl.col(c).is_finite() for c in ["paid", "case_reserve", "deductible"]]),
        "nonfinite",
        "Amounts must be finite.",
    )
    rows(pl.struct(KEY).is_duplicated(), "duplicate", "Duplicate portfolio/claim/valuation key.")
    rows(
        (pl.col("accident_date") > pl.col("report_date"))
        | (pl.col("report_date") > pl.col("valuation_date")),
        "date_order",
        "Require accident date <= report date <= valuation date.",
    )
    rows(~pl.col("status").is_in(["open", "closed"]), "status", "Status must be open or closed.")
    rows(
        ~pl.col("amount_basis").is_in(["before_deductible", "after_deductible"]),
        "basis",
        "Use before_deductible or after_deductible; no automatic deduction is applied.",
    )
    rows(
        (pl.col("paid") < 0) | (pl.col("case_reserve") < 0) | (pl.col("deductible") < 0),
        "negative_balance",
        "Cumulative paid, case reserve and deductible must be nonnegative.",
    )
    rows(
        (pl.col("status") == "closed") & (pl.col("case_reserve").abs() > 0.005),
        "closed_reserve",
        "Closed claim has a nonzero case reserve.",
    )
    if "incurred" in d.columns:
        d = d.with_columns(pl.col("incurred").cast(pl.Float64, strict=False))
        rows(
            pl.col("incurred").is_null()
            | ~pl.col("incurred").is_finite()
            | ((pl.col("incurred") - pl.col("paid") - pl.col("case_reserve")).abs() > 0.005),
            "incurred_tie",
            "Supplied incurred does not equal paid + case reserve.",
        )
    d = d.with_columns((pl.col("paid") + pl.col("case_reserve")).alias("incurred"))
    if cov.select(pl.any_horizontal(pl.all().is_null()).any()).item():
        issue("coverage_schema", "Coverage contains missing or malformed values.")
    if cov.select(pl.struct(GROUP + ["valuation_date"]).is_duplicated().any()).item():
        issue("coverage_duplicate", "Duplicate coverage key.")
    # Stable claim identity matters for counts and historical grouping.
    stable = d.group_by(["portfolio", "claim_id"]).agg(
        [
            pl.col(c).n_unique().alias(c)
            for c in ["accident_date", "report_date", "currency", "amount_basis", "deductible"]
        ]
    )
    if stable.filter(pl.any_horizontal([pl.col(c) > 1 for c in stable.columns[2:]])).height:
        issue(
            "identity_change",
            "A claim's dates, currency, amount basis or deductible changed across snapshots.",
        )
    uncovered = (
        d.select(GROUP + ["valuation_date"]).unique().join(cov, on=GROUP + ["valuation_date"], how="left")
    )
    if uncovered.filter(pl.col("complete").is_null()).height:
        issue("coverage_missing", "Some supplied snapshots have no coverage declaration.")
    if cov.filter(~pl.col("complete").fill_null(False)).height:
        issue("coverage_incomplete", "Incomplete snapshots remain missing in triangles.", severity="warning")
    if d.select(GROUP).unique().height > 1:
        issue(
            "multiple_groups",
            "Multiple portfolios/currencies/bases: select one group before fitting.",
            severity="warning",
        )
    # Every previously observed claim must persist in each subsequent complete snapshot.
    if not any(x[0] == "error" for x in issues):
        for g in cov.select(GROUP).unique().iter_rows(named=True):
            filt = pl.all_horizontal([pl.col(k) == v for k, v in g.items()])
            sub = d.filter(filt).sort(["claim_id", "valuation_date"])
            first = sub.group_by("claim_id").agg(pl.col("valuation_date").min().alias("first"))
            actual = sub.group_by("valuation_date").len()
            for c in cov.filter(filt & pl.col("complete")).iter_rows(named=True):
                expected = first.filter(pl.col("first") <= c["valuation_date"]).height
                got = actual.filter(pl.col("valuation_date") == c["valuation_date"])
                n = got["len"][0] if got.height else 0
                if n != expected:
                    issue(
                        "missing_claims",
                        f"{g['portfolio']} {c['valuation_date']}: complete snapshot has {n} claims, expected {expected}.",
                    )
            changed = sub.with_columns((pl.col("paid").diff().over("claim_id")).alias("_change"))
            for row in changed.filter(pl.col("_change") < -0.005).iter_rows(named=True):
                issue(
                    "negative_payment",
                    "Cumulative paid decreased; retained as a correction.",
                    row["_row"],
                    "warning",
                )
    return ValidationResult(d, cov, pl.DataFrame(issues, schema=ISSUE_SCHEMA, orient="row"))


def build_triangles(
    claims,
    coverage,
    *,
    valuation: date,
    portfolio: str,
    currency="EUR",
    amount_basis="after_deductible",
    grain="Y",
    start_year=None,
) -> Triangle:
    if grain not in ("Y", "Q") or valuation != period_end(period_index(valuation, grain), grain):
        raise ValueError("Valuation must be the end of a complete year (Y) or quarter (Q).")
    # Scope before checking history: future data must neither influence results nor block a past run.
    group = {"portfolio": portfolio, "currency": currency, "amount_basis": amount_basis}
    filt = pl.all_horizontal([pl.col(k) == v for k, v in group.items()])
    scoped = dates(claims, ["valuation_date"]).filter(
        filt & ((pl.col("valuation_date") <= valuation) | pl.col("valuation_date").is_null())
    )
    cov = dates(coverage, ["valuation_date"]).filter(
        filt & ((pl.col("valuation_date") <= valuation) | pl.col("valuation_date").is_null())
    )
    validation = validate_claims(scoped, cov)
    validation.require_valid()
    d, cov = validation.data, validation.coverage
    if cov.is_empty():
        raise ValueError("No coverage for this portfolio/currency/basis and valuation.")
    first_year = start_year if start_year is not None else cov["valuation_date"].min().year
    start = first_year if grain == "Y" else first_year * 4
    end = period_index(valuation, grain)
    if start > end:
        raise ValueError("Start year is later than valuation.")
    # Yearly snapshots are December balances, not sums of quarterly balances.
    d = d.with_columns(
        pl.col("accident_date")
        .map_elements(lambda x: label(period_index(x, grain), grain), return_dtype=pl.String)
        .alias("_origin"),
        pl.col("valuation_date")
        .map_elements(lambda x: period_index(x, grain), return_dtype=pl.Int64)
        .alias("_valuation_index"),
    )
    d = d.filter(
        pl.col("valuation_date").map_elements(
            lambda x: x == period_end(period_index(x, grain), grain), return_dtype=pl.Boolean
        )
    )
    agg = d.group_by(["_origin", "_valuation_index"]).agg(
        pl.col("paid").sum(), pl.col("incurred").sum(), pl.len().alias("count")
    )
    values = {(r["_origin"], r["_valuation_index"]): r for r in agg.iter_rows(named=True)}
    complete = {r["valuation_date"]: r["complete"] for r in cov.iter_rows(named=True)}
    n = end - start + 1
    matrices = {b: np.full((n, n), np.nan) for b in ("paid", "incurred", "count")}
    states = np.full((n, n), "future", dtype=object)
    origins = [label(i, grain) for i in range(start, end + 1)]
    for i, origin in enumerate(origins):
        for j in range(n - i):
            v = start + i + j
            if not complete.get(period_end(v, grain), False):
                states[i, j] = "missing"
                continue
            states[i, j] = "observed"
            row = values.get((origin, v), {})
            for b, matrix in matrices.items():
                matrix[i, j] = row.get(b, 0.0)
    return Triangle(
        origins,
        [int(o[:4]) for o in origins],
        grain,
        valuation,
        **matrices,
        states=states,
        claims=d,
        metadata={
            **group,
            "claims_hash": frame_hash(scoped),
            "coverage_hash": frame_hash(cov),
            "start_year": first_year,
            "grain": grain,
            "valuation": valuation.isoformat(),
            "validation_warnings": validation.issues.filter(pl.col("severity") == "warning").to_dicts(),
        },
    )


def load_triangle(data: pl.DataFrame, *, valuation: date, grain="Y", metadata=None) -> Triangle:
    """Long input: origin, development, paid, incurred, count, state. Explicit full square."""
    required = {"origin", "development", "paid", "incurred", "count", "state"}
    if required - set(data.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(data.columns))}")
    if grain not in ("Y", "Q") or valuation != period_end(period_index(valuation, grain), grain):
        raise ValueError("Valuation is not a period end.")
    data = data.with_columns(pl.col("origin").cast(pl.String))
    origins = sorted(data["origin"].unique().to_list())
    n = len(origins)
    expected = [
        label(i, grain)
        for i in range(period_index(valuation, grain) - n + 1, period_index(valuation, grain) + 1)
    ]
    if (
        not n
        or origins != expected
        or data.height != n * n
        or data.select(pl.struct(["origin", "development"]).is_duplicated().any()).item()
    ):
        raise ValueError(
            "Provide contiguous origins through valuation and one row per cell of the full square."
        )
    arrays = {b: np.full((n, n), np.nan) for b in ("paid", "incurred", "count")}
    states = np.full((n, n), "future", dtype=object)
    for r in data.iter_rows(named=True):
        i, j = origins.index(r["origin"]), int(r["development"]) - 1
        if not 0 <= j < n or r["development"] != j + 1:
            raise ValueError("Development ages must be integers from 1 to triangle width.")
        s = r["state"]
        if s not in ("observed", "missing", "future") or (s == "future") != (i + j >= n):
            raise ValueError("Cell state is inconsistent with the valuation boundary.")
        states[i, j] = s
        for b, array in arrays.items():
            v = r[b]
            if s != "observed" and v is not None:
                raise ValueError("Missing/future cells must contain null amounts.")
            if v is not None:
                if not np.isfinite(v) or v < 0:
                    raise ValueError("Observed cumulative amounts/counts must be finite and nonnegative.")
                if b == "count" and v != int(v):
                    raise ValueError("Observed reported claim counts must be integers.")
                array[i, j] = v
        if r["paid"] is not None and r["incurred"] is not None and r["incurred"] < r["paid"]:
            raise ValueError("Incurred cannot be smaller than paid in this input convention.")
    return Triangle(
        origins,
        [int(o[:4]) for o in origins],
        grain,
        valuation,
        **arrays,
        states=states,
        metadata={
            **(metadata or {}),
            "aggregate_hash": frame_hash(data),
            "grain": grain,
            "valuation": valuation.isoformat(),
        },
    )
