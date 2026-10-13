"""Explicit synthetic mortality cells and finite-horizon cohort survival."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime


def _calendar_date(value: object, name: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"{name} must be a calendar date (not a datetime).")
    return value


def _checked_q(value: object) -> float:
    if isinstance(value, (bool, str, bytes, bytearray)):
        raise ValueError("Mortality q must be a finite number from 0 through 1.")
    try:
        q = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Mortality q must be a finite number from 0 through 1.") from error
    if not math.isfinite(q) or not 0 <= q <= 1:
        raise ValueError("Mortality q must be a finite number from 0 through 1.")
    return q


@dataclass(frozen=True)
class MortalityCell:
    """One synthetic qx for a sex, attained age and calendar year."""

    sex: str
    attained_age: int
    calendar_year: int
    q: float

    def __post_init__(self) -> None:
        if self.sex not in ("male", "female"):
            raise ValueError("Mortality cell sex must be 'male' or 'female'.")
        if (
            isinstance(self.attained_age, bool)
            or not isinstance(self.attained_age, int)
            or self.attained_age < 0
        ):
            raise ValueError("Attained age must be a nonnegative integer.")
        if (
            isinstance(self.calendar_year, bool)
            or not isinstance(self.calendar_year, int)
            or not 1 <= self.calendar_year <= 9999
        ):
            raise ValueError("Calendar year must be from 1 through 9999.")
        object.__setattr__(self, "q", _checked_q(self.q))


@dataclass(frozen=True)
class MortalitySource:
    """Immutable, explicitly supplied mortality cells; no external ingestion."""

    source_id: str
    label: str
    cells: tuple[MortalityCell, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.source_id, str) or not self.source_id.strip():
            raise ValueError("Mortality source identifier is required.")
        if not isinstance(self.label, str) or not self.label.strip():
            raise ValueError("Mortality source label is required.")
        try:
            cells = tuple(self.cells)
        except TypeError as error:
            raise ValueError("Mortality source requires an iterable of cells.") from error
        if not cells:
            raise ValueError("Mortality source requires at least one cell.")
        if any(not isinstance(cell, MortalityCell) for cell in cells):
            raise ValueError("Mortality source cells must be MortalityCell values.")
        keys = [(cell.sex, cell.attained_age, cell.calendar_year) for cell in cells]
        if len(keys) != len(set(keys)):
            raise ValueError("Mortality source contains duplicate sex-age-year cells.")
        ordered = tuple(sorted(cells, key=lambda cell: (cell.sex, cell.attained_age, cell.calendar_year)))
        object.__setattr__(self, "cells", ordered)

    def qx(self, sex: str, attained_age: int, calendar_year: int) -> float:
        for cell in self.cells:
            if (cell.sex, cell.attained_age, cell.calendar_year) == (sex, attained_age, calendar_year):
                return cell.q
        raise ValueError(
            f"Mortality coverage is missing for {sex}, age {attained_age}, year {calendar_year}."
        )


@dataclass(frozen=True)
class MortalityInterval:
    sex: str
    start: date
    end: date
    attained_age: int
    calendar_year: int
    q: float
    year_days: int
    fraction: float
    survival_factor: float


@dataclass(frozen=True)
class SurvivalTrace:
    dob: date
    valuation_date: date
    horizon: date
    sex: str
    source_id: str
    source_label: str
    intervals: tuple[MortalityInterval, ...]
    mortality_cells: tuple[MortalityCell, ...]
    survival_at_horizon: float


def attained_age_on(dob: date, on_date: date) -> int:
    """Return attained age; 29 February birthdays fall on 1 March in common years."""
    dob = _calendar_date(dob, "Date of birth")
    on_date = _calendar_date(on_date, "Age date")
    if dob > on_date:
        raise ValueError("Date of birth cannot be after the age date.")
    birthday_day = dob.day
    birthday_month = dob.month
    if dob.month == 2 and dob.day == 29 and not _is_leap(on_date.year):
        birthday_month, birthday_day = 3, 1
    age = on_date.year - dob.year
    if (on_date.month, on_date.day) < (birthday_month, birthday_day):
        age -= 1
    return age


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _days_in_year(year: int) -> int:
    return 366 if _is_leap(year) else 365


def _next_birthday(dob: date, after: date) -> date | None:
    """Next policy birthday strictly after `after`, or None past date.max."""
    for year in (after.year, after.year + 1):
        if year > 9999:
            return None
        month, day = dob.month, dob.day
        if month == 2 and day == 29 and not _is_leap(year):
            month, day = 3, 1
        candidate = date(year, month, day)
        if candidate > after:
            return candidate
    return None


def survival_trace(
    source: MortalitySource,
    dob: date,
    valuation_date: date,
    horizon: date,
    sex: str,
) -> SurvivalTrace:
    """Build conditional survival from valuation through a covered finite horizon.

    Each interval is split at both birthdays and 1 January. Exposure uses
    actual segment days divided by 365 or 366 days in that calendar year.
    """
    if not isinstance(source, MortalitySource):
        raise ValueError("An explicit MortalitySource is required.")
    dob = _calendar_date(dob, "Date of birth")
    valuation_date = _calendar_date(valuation_date, "Valuation date")
    horizon = _calendar_date(horizon, "Horizon")
    if sex not in ("male", "female"):
        raise ValueError("Mortality sex must be 'male' or 'female'.")
    if dob > valuation_date:
        raise ValueError("Date of birth cannot be after valuation.")
    if horizon < valuation_date:
        raise ValueError("Horizon cannot precede valuation.")

    intervals: list[MortalityInterval] = []
    survival = 1.0
    cursor = valuation_date
    while cursor < horizon:
        year = cursor.year
        age = attained_age_on(dob, cursor)
        january = date(year + 1, 1, 1) if year < 9999 else None
        birthday = _next_birthday(dob, cursor)
        ends = [point for point in (horizon, january, birthday) if point is not None and cursor < point]
        end = min(ends)
        q = source.qx(sex, age, year)
        year_days = _days_in_year(year)
        fraction = (end - cursor).days / year_days
        factor = 0.0 if q == 1.0 else (1.0 if q == 0.0 else (1.0 - q) ** fraction)
        intervals.append(MortalityInterval(sex, cursor, end, age, year, q, year_days, fraction, factor))
        survival *= factor
        cursor = end
    used_keys = {(item.sex, item.attained_age, item.calendar_year) for item in intervals}
    used_cells = tuple(
        cell for cell in source.cells
        if (cell.sex, cell.attained_age, cell.calendar_year) in used_keys
    )
    return SurvivalTrace(
        dob, valuation_date, horizon, sex, source.source_id, source.label,
        tuple(intervals), used_cells, survival,
    )
