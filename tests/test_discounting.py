from __future__ import annotations

import io
import json
import zipfile
from datetime import date

import pytest

from actuarial_library.discounting import (
    DiscountCurve,
    DiscountingError,
    discount_factor,
    discount_payments,
    import_eiopa_curve_xlsx,
)


def synthetic_curve(
    spot_rates: dict[int, float] | None = None,
    *,
    valuation: date = date(2026, 6, 30),
    currency: str = "EUR",
    variant: str = "no-VA",
) -> DiscountCurve:
    return DiscountCurve(
        valuation=valuation,
        currency=currency,
        variant=variant,
        spot_rates=spot_rates if spot_rates is not None else {1: 0.10, 2: 0.10},
        provenance={
            "source_url": "synthetic://test-fixture",
            "source_date": "2026-06-30",
            "content_hash": "sha256:synthetic-fixture",
            "units": "decimal fractions; annual effective spot rates",
            "variant": variant,
            "retrieved_at": "2026-10-07T00:00:00Z",
        },
    )


def test_discounting_two_payments_matches_independent_literal():
    curve = synthetic_curve()
    result = discount_payments(
        [
            {"payment_date": "2027-06-30", "amount": 100, "origin": "2026"},
            {"payment_date": "2028-06-29", "amount": 100, "origin": "2025"},
        ],
        curve,
        date(2026, 6, 30),
        "EUR",
        "no-VA",
    )
    assert result["status"] == "available"
    assert result["totals"]["undiscounted"] == pytest.approx(200)
    assert result["totals"]["present_value"] == pytest.approx(173.553719008264, abs=1e-12)
    assert result["totals"]["discount_effect"] == pytest.approx(26.446280991736, abs=1e-12)
    assert [row["discount_factor"] for row in result["rows"]] == pytest.approx([1 / 1.1, 1 / 1.1**2])
    assert result["totals"]["by_origin"]["2026"]["present_value"] == pytest.approx(100 / 1.1)
    assert result["totals"]["by_payment_year"]["2028"]["present_value"] == pytest.approx(100 / 1.1**2)


def test_discount_factor_anchor_interpolation_and_node_recovery():
    curve = synthetic_curve({1: 0.10, 2: 0.21, 3: 0.05})
    assert discount_factor(curve, 0) == 1
    assert discount_factor(curve, 1) == pytest.approx(1 / 1.1)
    assert discount_factor(curve, 2) == pytest.approx(1 / 1.21**2)
    assert discount_factor(curve, 1.5) == pytest.approx((1 / 1.1) ** 0.5 * (1 / 1.21**2) ** 0.5)
    assert discount_factor(curve, 0.5) == pytest.approx((1 / 1.1) ** 0.5)


def test_zero_signed_and_negative_rates_are_supported():
    zero_curve = synthetic_curve({1: 0, 2: 0})
    assert discount_factor(zero_curve, 1.5) == pytest.approx(1)
    result = discount_payments(
        [
            {"payment_date": "2027-06-30", "amount": 100},
            {"payment_date": "2028-06-29", "amount": -25},
        ],
        zero_curve,
        date(2026, 6, 30),
        "EUR",
        "no-VA",
    )
    assert result["totals"]["present_value"] == pytest.approx(75)
    negative_curve = synthetic_curve({1: -0.01, 2: -0.02})
    assert discount_factor(negative_curve, 1) > 1


def test_payment_dates_use_act_365f_including_leap_day():
    curve = synthetic_curve({1: 0.10, 2: 0.10})
    result = discount_payments(
        [{"payment_date": "2026-09-30", "amount": 100}],
        curve,
        date(2026, 6, 30),
        "EUR",
        "no-VA",
    )
    assert result["rows"][0]["days_from_valuation"] == 92
    assert result["rows"][0]["time_years"] == pytest.approx(92 / 365)
    leap_result = discount_payments(
        [{"payment_date": "2024-03-01", "amount": 100}],
        curve,
        date(2024, 2, 29),
        "EUR",
        "no-VA",
    )
    assert leap_result["rows"][0]["days_from_valuation"] == 1
    assert leap_result["rows"][0]["time_years"] == pytest.approx(1 / 365)


@pytest.mark.parametrize(
    ("spot_rates", "time", "reason"),
    [
        ({1: 0.01, 3: 0.03}, 2, "MISSING_NODE"),
        ({1: 0.01, 2: 0.02}, 2.1, "OUTSIDE_CURVE_HORIZON"),
        ({1: 0.01}, 150.1, "OUTSIDE_CURVE_HORIZON"),
    ],
)
def test_missing_adjacent_node_or_horizon_is_blocked(spot_rates, time, reason):
    with pytest.raises(DiscountingError) as error:
        discount_factor(synthetic_curve(spot_rates), time)
    assert error.value.code == reason


@pytest.mark.parametrize(
    ("spot_rates",),
    [({1: -1.0},), ({1: float("nan")},), ({1: float("inf")},), ({0: 0.01},), ({151: 0.01},)],
)
def test_curve_rejects_invalid_rate_or_maturity(spot_rates):
    with pytest.raises(ValueError):
        synthetic_curve(spot_rates)


@pytest.mark.parametrize(
    ("curve", "valuation", "currency", "variant", "reason"),
    [
        (None, date(2026, 6, 30), "EUR", "no-VA", "MISSING_CURVE"),
        (synthetic_curve(valuation=date(2026, 5, 31)), date(2026, 6, 30), "EUR", "no-VA", "VALUATION_DATE_MISMATCH"),
        (synthetic_curve(currency="GBP"), date(2026, 6, 30), "EUR", "no-VA", "CURRENCY_MISMATCH"),
        (synthetic_curve(variant="with-VA"), date(2026, 6, 30), "EUR", "no-VA", "VARIANT_MISMATCH"),
    ],
)
def test_unavailable_or_mismatched_curve_keeps_undiscounted_rows(curve, valuation, currency, variant, reason):
    payments = [{"payment_date": "2027-06-30", "amount": 100, "origin": "2026"}]
    result = discount_payments(payments, curve, valuation, currency, variant)
    assert result["status"] == "blocked"
    assert result["reason"] == reason
    assert result["totals"]["undiscounted"] == 100
    assert result["totals"]["present_value"] is None
    assert result["rows"][0]["amount"] == 100
    assert result["rows"][0]["discounted_amount"] is None
    assert result["rows"][0]["origin"] == "2026"


def _synthetic_xlsx(variant: str = "no-VA") -> bytes:
    sheet_name = f"RFR_spot_{variant.replace('-', '_')}"
    workbook = f"""<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="{sheet_name}" sheetId="1" r:id="rId1"/></sheets>
    </workbook>"""
    rels = """<?xml version="1.0" encoding="UTF-8"?>
    <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
      <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
    </Relationships>"""
    cells = {
        "C3": "EUR_30_06_2026_SWP_LLP_20_EXT_40_UFR_3.30",
        "C5": "20",
        "C6": "40",
        "C7": "3.3",
        "C8": "0.073103",
        "C9": "10",
    }
    if variant == "with-VA":
        cells["C10"] = "14"
    cells.update({"B11": "1", "C11": "0.02592" if variant == "no-VA" else "0.02732", "B12": "2", "C12": "0.026"})
    row_numbers: dict[int, list[str]] = {}
    for address in cells:
        row_numbers.setdefault(int("".join(char for char in address if char.isdigit())), []).append(address)
    for maturity in range(3, 151):
        row_numbers.setdefault(maturity + 10, []).extend([f"B{maturity + 10}", f"C{maturity + 10}"])
    row_xml = []
    for row_number, addresses in sorted(row_numbers.items()):
        row_xml.append(f'<row r="{row_number}">')
        for address in sorted(addresses):
            maturity = int("".join(char for char in address if char.isdigit())) - 10
            value = cells.get(address, str(maturity if address.startswith("B") else 0.026))
            if address == "C3":
                row_xml.append(f'<c r="{address}" t="inlineStr"><is><t>{value}</t></is></c>')
            else:
                row_xml.append(f'<c r="{address}"><v>{value}</v></c>')
        row_xml.append("</row>")
    sheet = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
        + "".join(row_xml)
        + "</sheetData></worksheet>"
    )
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        archive.writestr("xl/workbook.xml", workbook)
        archive.writestr("xl/_rels/workbook.xml.rels", rels)
        archive.writestr("xl/worksheets/sheet1.xml", sheet)
    return output.getvalue()


def _xlsx_with_workbook_xml(replacement: bytes, *, absolute_target: bool = False) -> bytes:
    raw = _synthetic_xlsx()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw), "r") as source, zipfile.ZipFile(output, "w") as target:
        for entry in source.infolist():
            content = replacement if entry.filename == "xl/workbook.xml" else source.read(entry.filename)
            if absolute_target and entry.filename == "xl/_rels/workbook.xml.rels":
                content = content.replace(b'Target="worksheets/', b'Target="/xl/worksheets/')
            target.writestr(entry.filename, content)
    return output.getvalue()


def _xlsx_with_cell_value(address: str, value: str) -> bytes:
    raw = _synthetic_xlsx()
    output = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(raw), "r") as source, zipfile.ZipFile(output, "w") as target:
        for entry in source.infolist():
            content = source.read(entry.filename)
            if entry.filename == "xl/worksheets/sheet1.xml":
                start = content.index(f'<c r="{address}"'.encode())
                end = content.index(b"</c>", start) + len(b"</c>")
                content = content[:start] + f'<c r="{address}"><v>{value}</v></c>'.encode() + content[end:]
            target.writestr(entry.filename, content)
    return output.getvalue()


def test_xlsx_import_reads_selected_sheet_source_metadata_and_hash():
    raw = _synthetic_xlsx()
    curve = import_eiopa_curve_xlsx(
        raw,
        "no-VA",
        source_url="https://example.invalid/synthetic.xlsx",
        retrieved_at="2026-10-07T12:00:00Z",
    )
    assert curve.valuation == date(2026, 6, 30)
    assert curve.currency == "EUR"
    assert curve.variant == "no-VA"
    assert curve.spot_rates[1] == 0.02592
    assert curve.spot_rates[2] == 0.026
    assert len(curve.spot_rates) == 150
    assert curve.provenance["content_hash"].startswith("sha256:")
    assert curve.provenance["source_date"] == "2026-06-30"
    assert curve.provenance["units"] == "decimal fractions; annual effective spot rates"
    assert curve.provenance["ufr_percent"] == "3.3"
    assert curve.provenance["ufr_units"] == "percent"
    assert curve.provenance["cra_basis_points"] == "10.0"
    assert curve.provenance["cra_units"] == "basis points"
    assert curve.provenance["rate_units"] == "decimal fractions"
    json.dumps(discount_payments([], curve, curve.valuation, "EUR", "no-VA"))


def test_xlsx_import_reads_with_va_variant_and_native_metadata_units():
    curve = import_eiopa_curve_xlsx(
        _synthetic_xlsx("with-VA"),
        "with-VA",
        source_url="https://example.invalid/synthetic.xlsx",
        retrieved_at="2026-10-11T12:00:00Z",
    )
    assert curve.valuation == date(2026, 6, 30)
    assert curve.spot_rates[1] == pytest.approx(0.02732)
    assert curve.provenance["ufr_percent"] == "3.3"
    assert curve.provenance["cra_basis_points"] == "10.0"
    assert curve.provenance["va_basis_points"] == "14.0"
    assert curve.provenance["va_units"] == "basis points"


@pytest.mark.parametrize(
    "encoding,doctype",
    [
        (
            "utf-8",
            '<!DOCTYPE workbook [<!ENTITY injected "expanded">]>',
        ),
        (
            "utf-16",
            '<!DOCTYPE workbook [<!ENTITY injected "expanded">]>',
        ),
        (
            "utf-8",
            '<!DOCTYPE workbook [<!ENTITY injected SYSTEM "file:///private/should-not-be-read">]>',
        ),
    ],
)
def test_xlsx_import_rejects_dtd_and_entities_before_expansion(encoding, doctype):
    workbook = f'''<?xml version="1.0" encoding="{encoding}"?>
    {doctype}
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="RFR_spot_no_VA" sheetId="1" r:id="rId1"/></sheets>
      <definedNames><definedName name="unused">&injected;</definedName></definedNames>
    </workbook>'''.encode(encoding)
    with pytest.raises(ValueError, match="XML declarations"):
        import_eiopa_curve_xlsx(
            _xlsx_with_workbook_xml(workbook),
            "no-VA",
            source_url="https://example.invalid/upload.xlsx",
            retrieved_at="2026-10-11T12:00:00Z",
        )


def test_xlsx_import_resolves_package_absolute_relationship_targets():
    workbook = b'''<?xml version="1.0" encoding="UTF-8"?>
    <workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
      xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
      <sheets><sheet name="RFR_spot_no_VA" sheetId="1" r:id="rId1"/></sheets>
    </workbook>'''
    curve = import_eiopa_curve_xlsx(
        _xlsx_with_workbook_xml(workbook, absolute_target=True),
        "no-VA",
        source_url="https://example.invalid/upload.xlsx",
        retrieved_at="2026-10-11T12:00:00Z",
    )
    assert len(curve.spot_rates) == 150


@pytest.mark.parametrize(
    ("amount", "rate"),
    [(1e308, -0.9), (-1e308, -0.99)],
)
def test_discounted_amount_overflow_is_a_json_safe_block(amount, rate):
    curve = synthetic_curve({1: rate})
    result = discount_payments(
        [{"payment_date": "2027-06-30", "amount": amount}],
        curve,
        curve.valuation,
        "EUR",
        "no-VA",
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "NUMERICAL_OVERFLOW"
    assert result["rows"][0]["amount"] == amount
    assert result["rows"][0]["discounted_amount"] is None
    assert result["totals"]["undiscounted"] == amount
    json.dumps(result, allow_nan=False)


def test_finite_canceling_payments_remain_available_and_json_safe():
    curve = synthetic_curve({1: 0, 2: 0})
    result = discount_payments(
        [
            {"payment_date": "2027-06-30", "amount": 1e308, "origin": "same"},
            {"payment_date": "2027-06-30", "amount": -1e308, "origin": "same"},
        ],
        curve,
        curve.valuation,
        "EUR",
        "no-VA",
    )
    assert result["status"] == "available"
    assert result["totals"]["undiscounted"] == 0
    assert result["totals"]["present_value"] == 0
    assert result["totals"]["by_origin"]["same"]["present_value"] == 0
    json.dumps(result, allow_nan=False)


def test_total_overflow_blocks_without_non_finite_json_values():
    curve = synthetic_curve({1: 0, 2: 0})
    result = discount_payments(
        [
            {"payment_date": "2027-06-30", "amount": 1e308},
            {"payment_date": "2027-06-30", "amount": 1e308},
        ],
        curve,
        curve.valuation,
        "EUR",
        "no-VA",
    )
    assert result["status"] == "blocked"
    assert result["reason"] == "NUMERICAL_OVERFLOW"
    assert result["totals"]["undiscounted"] is None
    assert all(row["discounted_amount"] is None for row in result["rows"])
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize(
    ("cell", "value"),
    [("C7", "nan"), ("C8", "inf"), ("C9", "nan")],
)
def test_xlsx_import_rejects_non_finite_source_metadata(cell, value):
    with pytest.raises(ValueError):
        import_eiopa_curve_xlsx(
            _xlsx_with_cell_value(cell, value),
            "no-VA",
            source_url="https://example.invalid/upload.xlsx",
            retrieved_at="2026-10-11T12:00:00Z",
        )


def test_xlsx_import_rejects_ufr_that_disagrees_with_source_identifier():
    with pytest.raises(ValueError, match="unsupported curve source metadata"):
        import_eiopa_curve_xlsx(
            _xlsx_with_cell_value("C7", "3.29"),
            "no-VA",
            source_url="https://example.invalid/upload.xlsx",
            retrieved_at="2026-10-11T12:00:00Z",
        )


@pytest.mark.parametrize("raw", [b"", b"not a workbook", b"PK\x03\x04broken"])
def test_xlsx_import_rejects_bad_bytes(raw):
    with pytest.raises(ValueError):
        import_eiopa_curve_xlsx(
            raw,
            "no-VA",
            source_url="https://example.invalid/upload.xlsx",
            retrieved_at="2026-10-07T12:00:00Z",
        )
