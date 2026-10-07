"""Traceable development diagnostics shared by the UI and future agent tools."""

import numpy as np
import polars as pl

from .models import DevelopmentConfig, Triangle
from .reserving import development


def observation_pairs(triangle: Triangle, basis: str, config: DevelopmentConfig) -> pl.DataFrame:
    """Every observed adjacent pair, including unusable and excluded observations.

    Exclusions remove a pair from factor fitting, never from the source triangle.
    Window membership exactly follows the reserving engine.
    """
    values = getattr(triangle, basis)
    _, _, factors, _ = development(triangle, basis, config)
    rows = []
    for j in range(len(triangle.origins) - 1):
        candidates = [
            i
            for i in range(len(triangle.origins) - j - 1)
            if np.isfinite(values[i, j])
            and values[i, j] > 0
            and np.isfinite(values[i, j + 1])
            and (triangle.origins[i], j + 1) not in config.excluded
        ]
        used = candidates[-config.window :] if config.window else candidates
        denominator = sum(values[i, j] for i in used)
        for i in range(len(triangle.origins) - j - 1):
            start, end = values[i, j], values[i, j + 1]
            valid = np.isfinite(start) and start > 0 and np.isfinite(end)
            excluded = (triangle.origins[i], j + 1) in config.excluded
            state = (
                "Invalid / missing"
                if not valid
                else "Excluded"
                if excluded
                else "Used"
                if i in used
                else "Outside window"
            )
            rows.append(
                {
                    "origin": triangle.origins[i],
                    "development": j + 1,
                    "from_amount": float(start) if np.isfinite(start) else None,
                    "to_amount": float(end) if np.isfinite(end) else None,
                    "link_ratio": float(end / start) if valid else None,
                    "status": state,
                    "volume_weight": float(start / denominator) if i in used else None,
                    "selected_factor": factors[j]["selected"],
                }
            )
    return pl.DataFrame(
        rows,
        schema={
            "origin": pl.String,
            "development": pl.Int64,
            "from_amount": pl.Float64,
            "to_amount": pl.Float64,
            "link_ratio": pl.Float64,
            "status": pl.String,
            "volume_weight": pl.Float64,
            "selected_factor": pl.Float64,
        },
    )


def method_impact(baseline, scenario) -> pl.DataFrame:
    """Like-for-like assumption impact. Not a valuation-to-valuation reserve movement."""
    keys = ["origin", "method"]
    before = baseline.results.select(*keys, pl.col("ultimate").alias("baseline_ultimate"))
    after = scenario.results.select(*keys, pl.col("ultimate").alias("scenario_ultimate"))
    return before.join(after, on=keys, how="inner").with_columns(
        (pl.col("scenario_ultimate") - pl.col("baseline_ultimate")).alias("ultimate_change")
    )
