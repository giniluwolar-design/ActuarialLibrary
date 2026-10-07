"""Descriptive views; flags are review prompts, never automatic exclusions."""

import numpy as np
import polars as pl


def factor_triangle(triangle, basis):
    if basis not in ("paid", "incurred", "count"):
        raise ValueError("Choose paid, incurred or count.")
    values = getattr(triangle, basis)
    start, end = values[:, :-1], values[:, 1:]
    valid = np.isfinite(start) & (start > 0) & np.isfinite(end)
    ratios = np.full(start.shape, np.nan)
    np.divide(end, start, out=ratios, where=valid)
    return ratios


def claim_diagnostics(claims, valuation):
    """One valuation only: repeated historical snapshots cannot inflate the count.

    Upper Tukey fence on log1p(incurred), 3 IQR, within the selected portfolio.
    Small/degenerate samples are left unflagged, with an explicit reason.
    """
    current = claims.filter(pl.col("valuation_date") == valuation).with_columns(
        (pl.col("paid") + pl.col("case_reserve")).alias("incurred")
    )
    values = current["incurred"].to_numpy()
    threshold, reason = None, "Fewer than 20 claims at this valuation; no statistical flags."
    if len(values) >= 20:
        q1, q3 = np.quantile(np.log1p(values), [0.25, 0.75])
        if q3 > q1:
            threshold = float(np.expm1(q3 + 3 * (q3 - q1)))
            reason = "Incurred exceeds the upper 3-IQR fence on log(1 + incurred)."
        else:
            reason = "No interquartile variation; no statistical flags."
    return current.with_columns(
        (pl.col("incurred") > threshold if threshold is not None else pl.lit(False)).alias("review_flag")
    ), {"threshold": threshold, "rule": reason, "valuation": str(valuation), "claim_count": len(values)}
