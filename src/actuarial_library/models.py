"""Explicit contracts for data, assumptions and results."""

from dataclasses import dataclass, field
from datetime import date
from typing import Literal

import numpy as np
import polars as pl
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class DevelopmentConfig(StrictModel):
    average: Literal["volume", "simple"] = "volume"
    window: int | None = Field(default=None, ge=1)
    excluded: list[tuple[str, int]] = Field(default_factory=list)
    overrides: dict[int, float] = Field(default_factory=dict)
    tail: float = Field(default=1.0, ge=1)
    rationale: str = ""

    @model_validator(mode="after")
    def valid_selection(self):
        if any(k < 1 or v <= 0 for k, v in self.overrides.items()):
            raise ValueError("Factor overrides require positive ages and factors.")
        if (self.overrides or self.excluded or self.tail != 1) and not self.rationale.strip():
            raise ValueError("Explain factor overrides, exclusions and non-unit tails.")
        return self


class FrequencySeverityConfig(StrictModel):
    lookback_years: int = Field(default=10, ge=1)
    historical_years: list[int] | None = None
    average: Literal["weighted", "simple"] = "weighted"
    trend: float = Field(default=0.0, gt=-1)
    count_mode: Literal["developed", "manual", "exposure", "reported"] = "developed"
    no_further_reporting: bool = False
    expected_counts: dict[str, float] = Field(default_factory=dict)
    exposures: dict[str, float] = Field(default_factory=dict)
    frequencies: dict[str, float] = Field(default_factory=dict)
    historical_ultimates: dict[str, float] = Field(default_factory=dict)
    historical_counts: dict[str, float] = Field(default_factory=dict)
    rationale: str = ""

    @model_validator(mode="after")
    def valid_counts(self):
        if self.count_mode == "reported" and not self.no_further_reporting:
            raise ValueError("Confirm no further reporting before using reported counts directly.")
        for values in (self.expected_counts, self.exposures, self.frequencies, self.historical_counts):
            if any(v < 0 for v in values.values()):
                raise ValueError("Counts, exposures and frequencies cannot be negative.")
        if (self.historical_counts or self.historical_ultimates) and not self.rationale.strip():
            raise ValueError("Explain historical ultimate/count selections.")
        return self


class AnalysisConfig(StrictModel):
    paid: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    incurred: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    count: DevelopmentConfig = Field(default_factory=DevelopmentConfig)
    frequency_severity: FrequencySeverityConfig = Field(default_factory=FrequencySeverityConfig)
    priors: dict[str, float] = Field(default_factory=dict)
    selections: dict[str, str] = Field(default_factory=dict)
    manual_ultimates: dict[str, float] = Field(default_factory=dict)
    selection_notes: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def valid_prior(self):
        if any(v < 0 for v in self.priors.values()):
            raise ValueError("Expected ultimate priors must be nonnegative.")
        for origin in self.manual_ultimates:
            if not self.selection_notes.get(origin, "").strip():
                raise ValueError(f"Explain manual ultimate for {origin}.")
        return self


@dataclass
class ValidationResult:
    data: pl.DataFrame
    coverage: pl.DataFrame
    issues: pl.DataFrame

    @property
    def valid(self) -> bool:
        return self.issues.filter(pl.col("severity") == "error").is_empty()

    def require_valid(self):
        if not self.valid:
            errors = self.issues.filter(pl.col("severity") == "error")
            raise ValueError("Invalid claims data: " + "; ".join(errors["message"].unique().to_list()))


@dataclass
class Triangle:
    origins: list[str]
    origin_years: list[int]
    grain: str
    valuation: date
    paid: np.ndarray
    incurred: np.ndarray
    count: np.ndarray
    states: np.ndarray
    metadata: dict = field(default_factory=dict)
    claims: pl.DataFrame | None = field(default=None, repr=False)

    def frame(self, basis="paid", incremental=False) -> pl.DataFrame:
        values = getattr(self, basis).copy()
        if incremental:
            values[:, 1:] = values[:, 1:] - values[:, :-1]
        columns = {"origin": self.origins}
        columns.update(
            {
                str(j + 1): [None if not np.isfinite(v) else float(v) for v in values[:, j]]
                for j in range(values.shape[1])
            }
        )
        return pl.DataFrame(columns)

    def latest(self, basis):
        values = getattr(self, basis)
        n = len(self.origins)
        # Latest means the analysis valuation, never the latest non-missing earlier cell.
        return np.array([values[i, n - i - 1] for i in range(n)])

    def trace(self, origin: str, development: int) -> pl.DataFrame:
        if self.claims is None:
            raise ValueError("Claim drill-down is unavailable for aggregate input.")
        i = self.origins.index(origin)
        j = development - 1
        if j < 0 or j >= len(self.origins) or self.states[i, j] != "observed":
            raise ValueError("Choose an observed cell.")
        from .data import period_index

        target = period_index(self.valuation, self.grain) - len(self.origins) + 1 + i + j
        return self.claims.filter((pl.col("_origin") == origin) & (pl.col("_valuation_index") == target))


@dataclass
class AnalysisResult:
    results: pl.DataFrame
    factors: pl.DataFrame
    history: pl.DataFrame
    warnings: list[str]
    config: AnalysisConfig
    metadata: dict

    def to_dict(self):
        return {
            "results": self.results.to_dicts(),
            "factors": self.factors.to_dicts(),
            "history": self.history.to_dicts(),
            "warnings": self.warnings,
            "config": self.config.model_dump(mode="json"),
            "metadata": self.metadata,
        }
