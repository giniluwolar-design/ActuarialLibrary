"""Independent synthetic reference and calendar regressions at public module seams.

Run with unittest or pytest in an installed project. No AG tables or private data.
Decimal grid references are intentionally distinct from actual calendar dates.
"""

import unittest
from dataclasses import FrozenInstanceError
from datetime import date, datetime, timedelta
from decimal import Decimal, localcontext

from actuarial_library.annuity import DiscountFactorEvidence, calculate_annuity, payment_dates
from actuarial_library.mortality import MortalityCell, MortalitySource, attained_age_on, survival_trace


def discount_fixture(valuation, source_id, factors):
    return DiscountFactorEvidence(valuation, source_id, "Synthetic test curve only", "injected fixture convention", factors)


def source(cells):
    return MortalitySource("synthetic-reference-v2", "Synthetic reference only", tuple(
        MortalityCell(sex, age, year, q) for sex, age, year, q in cells
    ))


def constant_source(male=0.1, female=0.2):
    return source((sex, age, year, q) for sex, q in (("male", male), ("female", female))
                  for age in range(55, 122) for year in range(2026, 2031))


def regular(table=None, **kwargs):
    defaults = dict(
        source=table or constant_source(), participant_dob=date(1962, 1, 1),
        valuation_date=date(2027, 1, 1), commencement_date=date(2027, 1, 2),
        horizon=date(2028, 1, 1), frequency="annual", timing="primo",
    )
    defaults.update(kwargs)
    return calculate_annuity(**defaults)


class LiteralReferenceTests(unittest.TestCase):
    def test_all_six_corrected_v2_grid_literals(self):
        # Independent high-precision arithmetic: these are equal-offset grids,
        # including t=0 in the monthly-primo example, not calendar schedules.
        with localcontext() as ctx:
            ctx.prec = 50
            rate = Decimal("1.02")
            factors = []
            for qs in ((".0100", ".0120", ".0140"), (".0080", ".0096", ".0112")):
                alive, total = Decimal(1), Decimal(0)
                for term, q in enumerate(qs, 1):
                    alive *= 1 - Decimal(q)
                    total += alive / rate ** term
                factors.append(total)
            monthly = sum(((Decimal(".99") ** (Decimal(k) / 12)
                            + Decimal(".992") ** (Decimal(k) / 12)) / 2
                           / rate ** (Decimal(k) / 12) for k in range(12)), Decimal(0))
            participant, partner, partner_factor = Decimal(1), Decimal(1), Decimal(0)
            for term, (qa, qp) in enumerate(zip((".016", ".018", ".020"),
                                                (".008", ".0096", ".0112")), 1):
                participant *= 1 - Decimal(qa)
                partner *= 1 - Decimal(qp)
                partner_factor += (1 - participant) * partner / rate ** term
            actual = (*factors, sum(factors) / 2, monthly, monthly / 12, partner_factor)
            expected = ("2.819527104960", "2.832315809756", "2.825921457358",
                        "11.842812103818", "0.986901008651", "0.095948830798")
            for result, literal in zip(actual, expected):
                with self.subTest(literal=literal):
                    self.assertLess(abs(result - Decimal(literal)), Decimal("1e-12"))

    def test_regular_engine_annual_dates_match_independent_literals(self):
        table = source((sex, 65 + k, 2027 + k, q)
                       for sex, qs in (("male", (.01, .012, .014)),
                                       ("female", (.008, .0096, .0112)))
                       for k, q in enumerate(qs))
        dates = (date(2028, 1, 1), date(2029, 1, 1), date(2030, 1, 1))
        evidence = discount_fixture(date(2027, 1, 1), "synthetic-2-percent-grid",
                                          tuple((d, 1.02 ** -k) for k, d in enumerate(dates, 1)))
        for weights, expected in (((('male', 1.0), ('female', 0.0)), 2.819527104960),
                                  ((('male', 0.0), ('female', 1.0)), 2.832315809756),
                                  ((('male', .5), ('female', .5)), 2.825921457358)):
            with self.subTest(weights=weights):
                result = regular(table, horizon=date(2030, 1, 1),
                                 participant_sex_weights=weights, discount_evidence=evidence)
                self.assertAlmostEqual(result.factor, expected, delta=1e-12)

    def test_partner_engine_matches_independent_literal(self):
        table = source([('male', 68 + k, 2027 + k, q)
                        for k, q in enumerate((.016, .018, .020))]
                       + [('female', 65 + k, 2027 + k, q)
                          for k, q in enumerate((.008, .0096, .0112))])
        dates = (date(2028, 1, 1), date(2029, 1, 1), date(2030, 1, 1))
        evidence = discount_fixture(date(2027, 1, 1), "synthetic-grid",
                                          tuple((d, 1.02 ** -k) for k, d in enumerate(dates, 1)))
        result = regular(table, participant_dob=date(1959, 1, 1), horizon=date(2030, 1, 1),
                         factor_type='partner', partner_dob=date(1962, 1, 1),
                         participant_sex_weights=(('male', 1), ('female', 0)),
                         partner_sex_weights=(('male', 0), ('female', 1)), discount_evidence=evidence)
        self.assertAlmostEqual(result.factor, .095948830798, delta=1e-12)


class SurvivalCalendarTests(unittest.TestCase):
    def test_january_birth_full_year_and_boundary_without_next_cell(self):
        result = survival_trace(source([('male', 65, 2027, .1)]), date(1962, 1, 1),
                                date(2027, 1, 1), date(2028, 1, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9, places=15)
        self.assertEqual(len(result.intervals), 1)

    def test_midyear_birth_uses_actual_181_and_184_days(self):
        result = survival_trace(source([('male', 64, 2027, .1), ('male', 65, 2027, .2)]),
                                date(1962, 7, 1), date(2027, 1, 1), date(2028, 1, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9 ** (181 / 365) * .8 ** (184 / 365),
                               places=15)
        self.assertEqual(tuple((x.end - x.start).days for x in result.intervals), (181, 184))

    def test_leap_day_birthday_leap_year(self):
        result = survival_trace(source([('male', 63, 2028, .1), ('male', 64, 2028, .2)]),
                                date(1964, 2, 29), date(2028, 2, 28), date(2028, 3, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9 ** (1 / 366) * .8 ** (1 / 366),
                               places=15)
        self.assertEqual(tuple(x.year_days for x in result.intervals), (366, 366))

    def test_leap_day_birthday_nonleap_year_ages_on_march_first(self):
        table = source([('male', 62, 2027, .1)])
        result = survival_trace(table, date(1964, 2, 29), date(2027, 2, 28), date(2027, 3, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9 ** (1 / 365), places=15)
        self.assertEqual(attained_age_on(date(1964, 2, 29), date(2027, 2, 28)), 62)
        self.assertEqual(attained_age_on(date(1964, 2, 29), date(2027, 3, 1)), 63)

    def test_year_boundary_splits_even_without_birthday(self):
        result = survival_trace(source([('male', 64, 2027, .1), ('male', 64, 2028, .2)]),
                                date(1963, 7, 1), date(2027, 12, 31), date(2028, 1, 2), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9 ** (1 / 365) * .8 ** (1 / 366), places=15)

    def test_survival_is_conditional_at_valuation(self):
        result = survival_trace(source([('male', 65, 2027, .1)]), date(1962, 1, 1),
                                date(2027, 7, 1), date(2028, 1, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .9 ** (184 / 365), places=15)

    def test_q_zero_one_and_zero_duration(self):
        for q, expected in ((0, 1), (1, 0)):
            with self.subTest(q=q):
                table = source([('male', 65, 2027, q)])
                result = survival_trace(table, date(1962, 1, 1), date(2027, 1, 1),
                                        date(2027, 1, 2), 'male')
                self.assertEqual(result.survival_at_horizon, expected)
                same = survival_trace(table, date(1962, 1, 1), date(2027, 1, 1),
                                      date(2027, 1, 1), 'male')
                self.assertEqual(same.survival_at_horizon, 1)

    def test_unsupported_cell_blocks_even_after_certain_death(self):
        for q in (0, 1):
            with self.subTest(q=q), self.assertRaises(ValueError):
                survival_trace(source([('male', 65, 2027, q)]), date(1962, 1, 1),
                               date(2027, 1, 1), date(2028, 1, 2), 'male')

    def test_q120_preserved_and_residual_is_nonzero(self):
        result = survival_trace(source([('male', 120, 2027, .35)]), date(1907, 1, 1),
                                date(2027, 1, 1), date(2028, 1, 1), 'male')
        self.assertAlmostEqual(result.survival_at_horizon, .65, places=15)
        self.assertEqual(result.intervals[0].q, .35)

    def test_invalid_q_is_controlled(self):
        for q in (-.01, 1.01, float('nan'), float('inf'), 10 ** 400, True, '.1'):
            with self.subTest(q=str(q)), self.assertRaises(ValueError):
                source([('male', 65, 2027, q)])

    def test_invalid_dates_are_controlled(self):
        for dob, val, horizon in ((date(2028, 1, 1), date(2027, 1, 1), date(2028, 1, 1)),
                                  (date(1962, 1, 1), date(2028, 1, 1), date(2027, 1, 1)),
                                  (datetime(1962, 1, 1), date(2027, 1, 1), date(2028, 1, 1))):
            with self.subTest(dob=dob, val=val), self.assertRaises(ValueError):
                survival_trace(constant_source(), dob, val, horizon, 'male')


class PaymentScheduleTests(unittest.TestCase):
    def test_date_max_has_no_year_overflow(self):
        self.assertEqual(payment_dates(date(9999, 12, 1), date(9999, 12, 1), date.max,
                                       frequency='monthly', timing='ultimo'), (date.max,))

    def test_already_commenced_benefits_are_allowed(self):
        self.assertEqual(payment_dates(date(2027, 6, 30), date(2020, 1, 1), date(2027, 8, 1),
                                       frequency='monthly', timing='primo'),
                         (date(2027, 7, 1), date(2027, 8, 1)))

    def test_q2_reference_four_schedules(self):
        args = (date(2026, 6, 30), date(2026, 7, 1), date(2026, 12, 31))
        for frequency, timing, expected in (
            ('monthly', 'primo', tuple(date(2026, m, 1) for m in range(7, 13))),
            ('monthly', 'ultimo', (date(2026, 7, 31), date(2026, 8, 31), date(2026, 9, 30),
                                    date(2026, 10, 31), date(2026, 11, 30), date(2026, 12, 31))),
            ('annual', 'primo', ()), ('annual', 'ultimo', (date(2026, 12, 31),)),
        ):
            with self.subTest(frequency=frequency, timing=timing):
                self.assertEqual(payment_dates(*args, frequency=frequency, timing=timing), expected)

    def test_same_day_cutoff_and_commencement_no_proration(self):
        self.assertEqual(payment_dates(date(2027, 7, 1), date(2027, 7, 1), date(2027, 9, 15),
                                       frequency='monthly', timing='primo'),
                         (date(2027, 8, 1), date(2027, 9, 1)))
        self.assertEqual(payment_dates(date(2027, 6, 30), date(2027, 7, 15), date(2027, 8, 1),
                                       frequency='monthly', timing='primo'), (date(2027, 8, 1),))

    def test_leap_february_end_and_offgrid_horizon(self):
        self.assertEqual(payment_dates(date(2028, 1, 31), date(2028, 2, 1), date(2028, 3, 30),
                                       frequency='monthly', timing='ultimo'), (date(2028, 2, 29),))

    def test_commencement_after_horizon_yields_no_payment(self):
        self.assertEqual(payment_dates(date(2027, 1, 1), date(2029, 1, 1), date(2028, 1, 1),
                                       frequency='annual', timing='primo'), ())

    def test_invalid_modes_rejected(self):
        for frequency, timing in (('weekly', 'primo'), ('monthly', 'arrears')):
            with self.subTest(frequency=frequency), self.assertRaises(ValueError):
                payment_dates(date(2027, 1, 1), date(2027, 1, 2), date(2028, 1, 1),
                              frequency=frequency, timing=timing)


class FactorEvidenceTests(unittest.TestCase):
    def test_daily_reference_for_two_birthdays_year_boundaries_and_leap_year(self):
        cells = [('male' if sex == 0 else 'female', age, year,
                  .01 + .002 * (age - 60) + .003 * (year - 2027) + .002 * sex)
                 for sex in (0, 1) for age in range(60, 67) for year in (2027, 2028, 2029)]
        table = source(cells)
        lookup = {(sex, age, year): q for sex, age, year, q in cells}
        val, horizon = date(2027, 1, 15), date(2029, 3, 10)
        # Literal first-of-month grid independent from engine scheduler.
        dates = tuple(date(y, m, 1) for y, months in ((2027, range(2, 13)),
                                                     (2028, range(1, 13)), (2029, range(1, 4)))
                      for m in months)
        evidence = discount_fixture(val, 'synthetic-negative-rate-ACT365F',
                                          tuple((d, .99 ** (-(d - val).days / 365)) for d in dates))
        dobs = (date(1964, 2, 29), date(1963, 7, 1))
        alive = {(life, sex): 1.0 for life in (0, 1) for sex in ('male', 'female')}
        probabilities = {}
        cursor = val
        while cursor < horizon:
            for life, dob in enumerate(dobs):
                leap = cursor.year % 4 == 0 and (cursor.year % 100 != 0 or cursor.year % 400 == 0)
                birthday = (3, 1) if dob.month == 2 and dob.day == 29 and not leap else (dob.month, dob.day)
                age = cursor.year - dob.year - int((cursor.month, cursor.day) < birthday)
                for sex in ('male', 'female'):
                    alive[life, sex] *= (1 - lookup[sex, age, cursor.year]) ** (1 / (366 if leap else 365))
            cursor += timedelta(days=1)
            if cursor in dates:
                probabilities[cursor] = (.3 * (1 - alive[0, 'male']) + .7 * (1 - alive[0, 'female'])) \
                    * (.6 * alive[1, 'male'] + .4 * alive[1, 'female'])
        expected = sum(probabilities[d] * df / 12 for d, df in evidence.factors)
        result = regular(table, participant_dob=dobs[0], partner_dob=dobs[1], factor_type='partner',
                         valuation_date=val, commencement_date=date(2020, 1, 1), horizon=horizon,
                         frequency='monthly', timing='primo', discount_evidence=evidence,
                         participant_sex_weights=(('male', .3), ('female', .7)),
                         partner_sex_weights=(('male', .6), ('female', .4)))
        self.assertEqual(result.payment_dates, dates)
        self.assertAlmostEqual(result.factor, expected, delta=1e-13)

    def test_finite_inputs_cannot_publish_overflowing_factor(self):
        evidence = discount_fixture(date(2027, 1, 1), 'synthetic-overflow',
                                          ((date(2028, 1, 1), 1e308), (date(2029, 1, 1), 1e308)))
        with self.assertRaises(ValueError):
            regular(constant_source(0, 0), horizon=date(2029, 1, 1), discount_evidence=evidence)

    def test_subnormal_weight_still_requires_participant_coverage(self):
        table = source([('male', 65, 2027, .1), ('male', 59, 2027, .1), ('female', 59, 2027, .1)])
        with self.assertRaises(ValueError):
            regular(table, factor_type='partner', partner_dob=date(1968, 1, 1),
                    participant_sex_weights=(('male', 1), ('female', 5e-324)))

    def test_result_records_scope_sources_residual_and_assumptions(self):
        result = regular()
        self.assertIn('truncated', result.scope_label)
        self.assertEqual(result.mortality_source_id, 'synthetic-reference-v2')
        self.assertEqual(len(result.residual_survival), 2)
        self.assertAlmostEqual(result.residual_survival[0][2], .9, places=15)
        self.assertAlmostEqual(result.residual_survival[1][2], .8, places=15)
        self.assertTrue(result.mortality_cells)
        words = ' '.join(result.assumptions).lower()
        for term in ('conditional', 'indexation', 'pending', 'composition', 'independen'):
            with self.subTest(term=term):
                self.assertIn(term, words)

    def test_duplicate_cells_dates_and_unknown_sexes_rejected(self):
        with self.assertRaises(ValueError):
            source([('male', 65, 2027, .1), ('male', 65, 2027, .2)])
        with self.assertRaises(ValueError):
            source([('invented', 65, 2027, .1)])
        with self.assertRaises(ValueError):
            discount_fixture(date(2027, 1, 1), 'synthetic-duplicate',
                                   ((date(2028, 1, 1), 1), (date(2028, 1, 1), .5)))

    def test_calendar_monthly_normalization_against_literal_dates(self):
        # Expected dates/exponents are written independently, not from schedule/survival helpers.
        dates = (date(2027, 7, 31), date(2027, 8, 31), date(2027, 9, 30),
                 date(2027, 10, 31), date(2027, 11, 30), date(2027, 12, 31))
        valuation = date(2027, 6, 30)
        evidence = discount_fixture(valuation, 'synthetic-flat-2-percent-ACT365F',
                                          tuple((d, 1.02 ** (-(d - valuation).days / 365)) for d in dates))
        result = regular(valuation_date=valuation, commencement_date=date(2027, 7, 15),
                         horizon=date(2027, 12, 31), frequency='monthly', timing='ultimo',
                         discount_evidence=evidence)
        expected = sum((.9 ** (days / 365) + .8 ** (days / 365)) / 2
                       * 1.02 ** (-days / 365) / 12 for days in (31, 62, 92, 123, 153, 184))
        self.assertAlmostEqual(result.factor, expected, places=14)
        self.assertTrue(all(p.benefit == 1 / 12 for p in result.payments))
        self.assertAlmostEqual(sum(p.pv_contribution for p in result.payments), result.factor, places=14)

    def test_fixed_partner_uses_each_lifes_weights_and_independence(self):
        evidence = discount_fixture(date(2027, 1, 1), 'synthetic-unit-DF', ((date(2028, 1, 1), 1),))
        result = regular(factor_type='partner', partner_dob=date(1968, 1, 1),
                         participant_sex_weights=(('male', .25), ('female', .75)),
                         partner_sex_weights=(('male', .8), ('female', .2)), discount_evidence=evidence)
        expected = (.25 * .1 + .75 * .2) * (.8 * .9 + .2 * .8)
        self.assertAlmostEqual(result.factor, expected, places=15)
        self.assertEqual(len(result.payments), 4)
        self.assertAlmostEqual(sum(p.weight for p in result.payments), 1, places=15)
        self.assertTrue(any('independen' in a.lower() for a in result.assumptions))

    def test_zero_participant_death_never_creates_partner_benefit(self):
        result = regular(constant_source(0, 0), factor_type='partner', partner_dob=date(1968, 1, 1))
        self.assertEqual(result.undiscounted_factor, 0)
        self.assertTrue(all(p.contingency_probability == 0 for p in result.payments))

    def test_missing_discount_retains_survival_and_blocks_factor(self):
        result = regular()
        self.assertIsNone(result.factor)
        self.assertTrue(result.block_reason)
        self.assertTrue(result.branches)
        self.assertTrue(all(p.discount_factor is None and p.pv_contribution is None for p in result.payments))

    def test_wrong_valuation_and_incomplete_discount_block(self):
        for evidence in (discount_fixture(date(2026, 1, 1), 'synthetic-wrong-date', ((date(2028, 1, 1), 1),)),
                         discount_fixture(date(2027, 1, 1), 'synthetic-incomplete', ())):
            with self.subTest(evidence=evidence):
                result = regular(discount_evidence=evidence)
                self.assertIsNone(result.factor)
                self.assertTrue(result.block_reason)
                self.assertTrue(result.branches)

    def test_zero_weight_branches_need_no_unsupported_cells(self):
        result = regular(source([('male', 65, 2027, .1)]),
                         participant_sex_weights=(('male', 1), ('female', 0)))
        self.assertAlmostEqual(result.undiscounted_factor, .9, places=15)
        with self.assertRaises(ValueError):
            regular(source([('male', 65, 2027, .1)]))

    def test_horizon_coverage_checked_without_scheduled_payments(self):
        with self.assertRaises(ValueError):
            regular(source([('male', 65, 2027, .1)]), commencement_date=date(2030, 1, 1),
                    horizon=date(2028, 1, 2), participant_sex_weights=(('male', 1), ('female', 0)))

    def test_partner_requires_exact_dob_and_coverage(self):
        with self.assertRaises(ValueError):
            regular(factor_type='partner')
        with self.assertRaises(ValueError):
            regular(source([('male', 65, 2027, .1)]), factor_type='partner',
                    partner_dob=date(1968, 1, 1), participant_sex_weights=(('male', 1), ('female', 0)),
                    partner_sex_weights=(('male', 1), ('female', 0)))

    def test_weights_and_discount_values_require_finite_numbers(self):
        for weight in (-.1, 1.1, float('nan'), float('inf'), 10 ** 400, True):
            with self.subTest(weight=str(weight)), self.assertRaises(ValueError):
                regular(participant_sex_weights=(('male', weight), ('female', 1)))
        for df in (-1, float('nan'), float('inf'), 10 ** 400, True):
            with self.subTest(df=str(df)), self.assertRaises(ValueError):
                discount_fixture(date(2027, 1, 1), 'synthetic-invalid', ((date(2028, 1, 1), df),))

    def test_input_and_returned_traces_are_immutable_snapshots(self):
        cells = [MortalityCell('male', 65, 2027, .1)]
        table = MortalitySource('synthetic-snapshot', 'Synthetic only', cells)
        factors = [[date(2028, 1, 1), 1.0]]
        evidence = discount_fixture(date(2027, 1, 1), 'synthetic-snapshot', factors)
        result = regular(table, participant_sex_weights=(('male', 1), ('female', 0)), discount_evidence=evidence)
        cells.clear()
        factors[0][1] = .25
        self.assertAlmostEqual(result.factor, .9, places=15)
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            result.payments[0].benefit = 123
        with self.assertRaises((FrozenInstanceError, AttributeError, TypeError)):
            result.branches[0].participant.intervals[0].q = 1


if __name__ == '__main__':
    unittest.main()
