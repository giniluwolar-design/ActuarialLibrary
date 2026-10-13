"""Calendar-based finite-horizon life-contingent annuity factors."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime

from .mortality import MortalityCell, MortalitySource, SurvivalTrace, survival_trace


def _date(value: object, name: str) -> date:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise ValueError(f"{name} must be a calendar date (not a datetime).")
    return value


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, (bool, str, bytes, bytearray)):
        raise ValueError(f"{name} must be a finite number.")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be a finite number.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number.")
    return result


@dataclass(frozen=True)
class DiscountFactorEvidence:
    """Materialized date discount factors with inspectable curve provenance."""

    valuation_date: date
    source_id: str
    source_label: str
    day_count: str
    factors: tuple[tuple[date, float], ...]

    def __post_init__(self) -> None:
        valuation_date = _date(self.valuation_date, "Discount valuation date")
        provenance = (
            ("Discount source identifier", self.source_id),
            ("Discount source label", self.source_label),
            ("Discount day count", self.day_count),
        )
        for name, value in provenance:
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required.")
        try:
            raw_factors = tuple(self.factors)
        except TypeError as error:
            raise ValueError("Discount factors must be an iterable of date-factor pairs.") from error
        checked: list[tuple[date, float]] = []
        seen: set[date] = set()
        for item in raw_factors:
            if not isinstance(item, (tuple, list)) or len(item) != 2:
                raise ValueError("Each discount factor must be a (date, factor) pair.")
            payment_date = _date(item[0], "Discount factor date")
            factor = _finite_number(item[1], "Discount factor")
            if factor < 0:
                raise ValueError("Discount factors must be nonnegative.")
            if payment_date in seen:
                raise ValueError("Discount evidence contains duplicate dates.")
            checked.append((payment_date, factor))
            seen.add(payment_date)
        object.__setattr__(self, "valuation_date", valuation_date)
        object.__setattr__(self, "factors", tuple(sorted(checked, key=lambda pair: pair[0])))


@dataclass(frozen=True)
class PaymentTrace:
    payment_date: date
    sex_pair: tuple[str, ...]
    weight: float
    participant_survival: float
    partner_survival: float | None
    contingency_probability: float
    benefit: float
    discount_factor: float | None
    pv_contribution: float | None


@dataclass(frozen=True)
class AnnuityBranchTrace:
    sex_pair: tuple[str, ...]
    weight: float
    participant: SurvivalTrace
    partner: SurvivalTrace | None


@dataclass(frozen=True)
class AnnuityResult:
    factor_type: str
    frequency: str
    timing: str
    valuation_date: date
    commencement_date: date
    horizon: date
    factor: float | None
    undiscounted_factor: float
    discounted: bool
    block_reason: str | None
    payment_dates: tuple[date, ...]
    payments: tuple[PaymentTrace, ...]
    branches: tuple[AnnuityBranchTrace, ...]
    residual_survival: tuple[tuple[tuple[str, ...], float, float, float | None], ...]
    mortality_source_id: str
    mortality_source_label: str
    mortality_cells: tuple[MortalityCell, ...]
    discount_valuation_date: date | None
    discount_source_id: str | None
    discount_source_label: str | None
    discount_day_count: str | None
    discount_factors: tuple[tuple[date, float], ...]
    assumptions: tuple[str, ...]
    scope_label: str = "synthetic truncated finite-horizon"


def payment_dates(
    valuation_date: date,
    commencement_date: date,
    horizon: date,
    *,
    frequency: str,
    timing: str,
) -> tuple[date, ...]:
    """Return scheduled dates after valuation and on/after commencement."""
    valuation_date = _date(valuation_date, "Valuation date")
    commencement_date = _date(commencement_date, "Commencement date")
    horizon = _date(horizon, "Horizon")
    if not isinstance(frequency, str) or frequency not in ("annual", "monthly"):
        raise ValueError("Frequency must be 'annual' or 'monthly'.")
    if not isinstance(timing, str) or timing not in ("primo", "ultimo"):
        raise ValueError("Timing must be 'primo' or 'ultimo'.")
    if horizon < valuation_date:
        raise ValueError("Horizon cannot precede valuation.")
    if horizon < commencement_date:
        return ()

    dates: list[date] = []
    if frequency == "annual":
        for year in range(valuation_date.year, horizon.year + 1):
            scheduled = date(year, 1, 1) if timing == "primo" else date(year, 12, 31)
            if valuation_date < scheduled <= horizon and scheduled >= commencement_date:
                dates.append(scheduled)
    else:
        year, month = valuation_date.year, valuation_date.month
        while (year, month) <= (horizon.year, horizon.month):
            scheduled = (
                date(year, month, 1)
                if timing == "primo"
                else date(year, month, _month_length(year, month))
            )
            if valuation_date < scheduled <= horizon and scheduled >= commencement_date:
                dates.append(scheduled)
            if month == 12:
                if year == 9999:
                    break
                year, month = year + 1, 1
            else:
                month += 1
    return tuple(dates)


def _month_length(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (date(year, month + 1, 1) - date(year, month, 1)).days


def _weights(value: tuple[tuple[str, float], ...], name: str) -> tuple[tuple[str, float], ...]:
    try:
        entries = tuple(value)
    except TypeError as error:
        raise ValueError(f"{name} must be an iterable of (sex, weight) pairs.") from error
    if not entries:
        raise ValueError(f"{name} must include at least one sex branch.")
    result: list[tuple[str, float]] = []
    seen: set[str] = set()
    for item in entries:
        if not isinstance(item, (tuple, list)) or len(item) != 2:
            raise ValueError(f"{name} entries must be (sex, weight) pairs.")
        sex, raw_weight = item
        if sex not in ("male", "female") or sex in seen:
            raise ValueError(f"{name} sexes must be 'male' or 'female' and unique.")
        weight = _finite_number(raw_weight, f"{name} weight")
        if not 0 <= weight <= 1:
            raise ValueError(f"{name} weights must be from zero through one.")
        seen.add(sex)
        result.append((sex, weight))
    try:
        total = math.fsum(weight for _, weight in result)
    except OverflowError as error:
        raise ValueError(f"{name} weights must sum to one.") from error
    if not math.isfinite(total) or not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1e-12):
        raise ValueError(f"{name} weights must sum to one.")
    return tuple((sex, weight / total) for sex, weight in result)


def _survival_at(trace: SurvivalTrace, when: date) -> float:
    if when == trace.valuation_date:
        return 1.0
    result = 1.0
    for interval in trace.intervals:
        if when >= interval.end:
            result *= interval.survival_factor
        elif interval.start < when < interval.end:
            fraction = (when - interval.start).days / interval.year_days
            q = interval.q
            result *= 0.0 if q == 1.0 else (1.0 if q == 0.0 else (1.0 - q) ** fraction)
            break
        else:
            break
    return result


def calculate_annuity(
    source: MortalitySource,
    participant_dob: date,
    valuation_date: date,
    commencement_date: date,
    horizon: date,
    *,
    frequency: str,
    timing: str,
    factor_type: str = "regular",
    participant_sex_weights: tuple[tuple[str, float], ...] = (("male", 0.5), ("female", 0.5)),
    partner_dob: date | None = None,
    partner_sex_weights: tuple[tuple[str, float], ...] = (("male", 0.5), ("female", 0.5)),
    discount_evidence: DiscountFactorEvidence | None = None,
) -> AnnuityResult:
    """Calculate regular or known-partner factors on a finite calendar horizon.

    Missing or mismatched discount evidence blocks the discounted factor but
    leaves mortality branches and undiscounted payment probabilities inspectable.
    """
    if not isinstance(source, MortalitySource):
        raise ValueError("An explicit MortalitySource is required.")
    participant_dob = _date(participant_dob, "Participant date of birth")
    valuation_date = _date(valuation_date, "Valuation date")
    commencement_date = _date(commencement_date, "Commencement date")
    horizon = _date(horizon, "Horizon")
    if not isinstance(factor_type, str) or factor_type not in ("regular", "partner"):
        raise ValueError("Factor type must be 'regular' or 'partner'.")
    if factor_type == "partner":
        if partner_dob is None:
            raise ValueError("Partner factor requires the known partner date of birth.")
        partner_dob = _date(partner_dob, "Partner date of birth")
    elif partner_dob is not None:
        raise ValueError("Partner date of birth is only used for a partner factor.")

    schedule = payment_dates(
        valuation_date, commencement_date, horizon, frequency=frequency, timing=timing
    )
    participant_weights = _weights(participant_sex_weights, "Participant sex weights")
    partner_weights = _weights(partner_sex_weights, "Partner sex weights") if factor_type == "partner" else ()
    amount = 1.0 if frequency == "annual" else 1.0 / 12.0

    # Validate every positive-weight sex branch independently before forming
    # pair products. A subnormal nonzero weight can underflow in multiplication.
    participant_traces = {
        sex: survival_trace(source, participant_dob, valuation_date, horizon, sex)
        for sex, weight in participant_weights
        if weight > 0
    }
    partner_traces = (
        {
            sex: survival_trace(source, partner_dob, valuation_date, horizon, sex)
            for sex, weight in partner_weights
            if weight > 0
        }
        if factor_type == "partner" and partner_dob is not None
        else {}
    )

    branch_inputs: list[tuple[tuple[str, ...], float, str, str | None]] = []
    for participant_sex, p_weight in participant_weights:
        if p_weight == 0:
            continue
        if factor_type == "regular":
            branch_inputs.append(((participant_sex,), p_weight, participant_sex, None))
        else:
            for partner_sex, partner_weight in partner_weights:
                if partner_weight == 0:
                    continue
                weight = p_weight * partner_weight
                branch_inputs.append(((participant_sex, partner_sex), weight, participant_sex, partner_sex))

    branches: list[AnnuityBranchTrace] = []
    for pair, weight, participant_sex, partner_sex in branch_inputs:
        participant_trace = participant_traces[participant_sex]
        partner_trace = partner_traces.get(partner_sex) if partner_sex is not None else None
        branches.append(AnnuityBranchTrace(pair, weight, participant_trace, partner_trace))

    block_reason: str | None = None
    discount_map: dict[date, float] = {}
    if discount_evidence is None:
        block_reason = "Discount-factor evidence is required for a discounted factor."
    elif not isinstance(discount_evidence, DiscountFactorEvidence):
        raise ValueError("Discount evidence must be DiscountFactorEvidence.")
    elif discount_evidence.valuation_date != valuation_date:
        block_reason = "Discount-factor valuation date does not match the annuity valuation date."
    else:
        discount_map = dict(discount_evidence.factors)
        missing_dates = [day for day in schedule if day not in discount_map]
        if missing_dates:
            block_reason = "Discount-factor evidence is missing one or more scheduled payment dates."

    payments: list[PaymentTrace] = []
    undiscounted_terms: list[float] = []
    discounted_terms: list[float] = []
    for payment_date in schedule:
        discount = discount_map.get(payment_date) if block_reason is None else None
        for branch in branches:
            participant_survival = _survival_at(branch.participant, payment_date)
            partner_survival = _survival_at(branch.partner, payment_date) if branch.partner else None
            probability = (
                participant_survival
                if factor_type == "regular"
                else (1.0 - participant_survival) * partner_survival
            )
            base = branch.weight * probability * amount
            undiscounted_terms.append(base)
            pv = base * discount if discount is not None else None
            if pv is not None:
                discounted_terms.append(pv)
            payments.append(PaymentTrace(
                payment_date, branch.sex_pair, branch.weight,
                participant_survival, partner_survival, probability, amount, discount, pv,
            ))

    try:
        undiscounted_factor = math.fsum(undiscounted_terms)
        factor = math.fsum(discounted_terms) if block_reason is None else None
    except OverflowError as error:
        raise ValueError("Annuity factor exceeds the finite numeric range.") from error
    if not math.isfinite(undiscounted_factor) or (factor is not None and not math.isfinite(factor)):
        raise ValueError("Annuity factor exceeds the finite numeric range.")

    residual = tuple(
        (
            branch.sex_pair,
            branch.weight,
            branch.participant.survival_at_horizon,
            branch.partner.survival_at_horizon if branch.partner else None,
        )
        for branch in branches
    )
    assumptions = (
        "Truncated finite horizon; residual survival is exposed and no death is forced at the horizon.",
        "Survival is conditional on each life being alive at valuation.",
        "Both lives are initially alive; the partner is known and fixed eligible; marriage, divorce, "
        "and remarriage are not modelled (pending extensions).",
        "Indexation is zero.",
        "Mortality exposure splits at birthdays and 1 January using actual segment days / "
        "calendar-year days.",
        "A 29 February birth date has a 1 March birthday in non-leap years.",
        "Payments are full annual-benefit instalments on scheduled dates; no first-period proration.",
        "Each life mixes sex-specific factors in factor space; partner composition uses products "
        "of per-life weights.",
        "The selected sex compositions for participant and partner are independent.",
        "Participant and partner lifetimes are independent.",
        "Partner benefit requires the participant dead and partner alive at payment time.",
    )
    used_cells: dict[tuple[str, int, int], MortalityCell] = {}
    for branch in branches:
        for trace in (branch.participant, branch.partner):
            if trace is not None:
                for cell in trace.mortality_cells:
                    used_cells[(cell.sex, cell.attained_age, cell.calendar_year)] = cell
    return AnnuityResult(
        factor_type, frequency, timing, valuation_date, commencement_date, horizon,
        factor, undiscounted_factor, block_reason is None, block_reason,
        schedule, tuple(payments), tuple(branches), residual,
        source.source_id, source.label,
        tuple(used_cells[key] for key in sorted(used_cells)),
        discount_evidence.valuation_date if isinstance(discount_evidence, DiscountFactorEvidence) else None,
        discount_evidence.source_id if isinstance(discount_evidence, DiscountFactorEvidence) else None,
        discount_evidence.source_label if isinstance(discount_evidence, DiscountFactorEvidence) else None,
        discount_evidence.day_count if isinstance(discount_evidence, DiscountFactorEvidence) else None,
        discount_evidence.factors if isinstance(discount_evidence, DiscountFactorEvidence) else (),
        assumptions,
    )
