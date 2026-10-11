"""Deterministic discounting against explicitly supplied annual spot-rate nodes."""

from __future__ import annotations

import hashlib
import io
import math
import posixpath
import re
import zipfile
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import PurePosixPath
from types import MappingProxyType
from typing import Any
from xml.etree import ElementTree

_PROVENANCE_FIELDS = ("source_url", "source_date", "content_hash", "units", "variant", "retrieved_at")
_MAX_UPLOAD_BYTES = 25 * 1024 * 1024
_MAX_ARCHIVE_FILES = 2000
_MAX_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
_MAX_XML_BYTES = 50 * 1024 * 1024
_SPREADSHEET_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
_OFFICE_REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_PACKAGE_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"


class DiscountingError(ValueError):
    """An unavailable discount factor with a stable machine-readable reason."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class DiscountCurve:
    """A dated curve of annual-effective spot rates at integer year maturities."""

    valuation: date
    currency: str
    variant: str
    spot_rates: Mapping[int, float]
    provenance: Mapping[str, str]

    def __post_init__(self) -> None:
        if not isinstance(self.valuation, date) or isinstance(self.valuation, datetime):
            raise TypeError("Curve valuation must be a calendar date.")
        if not isinstance(self.currency, str) or not self.currency.strip():
            raise ValueError("Curve currency is required.")
        if self.variant not in {"no-VA", "with-VA"}:
            raise ValueError("Curve variant must be 'no-VA' or 'with-VA'.")
        if not isinstance(self.spot_rates, Mapping) or not self.spot_rates:
            raise ValueError("Curve must contain at least one annual spot-rate node.")
        checked: dict[int, float] = {}
        for maturity, raw_rate in self.spot_rates.items():
            if isinstance(maturity, bool) or not isinstance(maturity, int) or not 1 <= maturity <= 150:
                raise ValueError("Curve maturities must be integers from 1 through 150.")
            try:
                rate = float(raw_rate)
            except (TypeError, ValueError, OverflowError) as error:
                raise ValueError(f"Invalid spot rate at maturity {maturity}.") from error
            if not math.isfinite(rate) or rate <= -1:
                raise ValueError(f"Spot rate at maturity {maturity} must be finite and greater than -1.")
            checked[maturity] = rate
        if not isinstance(self.provenance, Mapping):
            raise TypeError("Explicit curve provenance is required.")
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in self.provenance.items()):
            raise TypeError("Curve provenance keys and values must be strings.")
        missing = [name for name in _PROVENANCE_FIELDS if not str(self.provenance.get(name, "")).strip()]
        if missing:
            raise ValueError("Curve provenance is missing: " + ", ".join(missing))
        units = str(self.provenance["units"]).lower()
        if "decimal" not in units or "annual effective" not in units:
            raise ValueError("Curve provenance units must identify decimal annual-effective spot rates.")
        if self.provenance["variant"] != self.variant:
            raise ValueError("Curve provenance variant must match the curve variant.")
        object.__setattr__(self, "spot_rates", MappingProxyType(dict(sorted(checked.items()))))
        object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))


def _discount_factor_at_node(maturity: int, rate: float) -> float:
    try:
        factor = math.exp(-maturity * math.log1p(rate))
    except (OverflowError, ValueError) as error:
        raise DiscountingError("INTERPOLATION_FAILURE", "The curve node has no finite discount factor.") from error
    if not math.isfinite(factor) or factor <= 0:
        raise DiscountingError("INTERPOLATION_FAILURE", "The curve node has no finite positive discount factor.")
    return factor


def discount_factor(curve: DiscountCurve, t: float) -> float:
    """Return D(t) using annual-effective nodes and log-linear DF interpolation."""
    if isinstance(t, bool):
        raise TypeError("Discount time must be a finite nonnegative number of years.")
    try:
        time = float(t)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Discount time must be a finite nonnegative number of years.") from error
    if not math.isfinite(time) or time < 0:
        raise ValueError("Discount time must be a finite nonnegative number of years.")
    if time == 0:
        return 1.0
    if time > 150:
        raise DiscountingError("OUTSIDE_CURVE_HORIZON", "Discount time exceeds the supported 150-year horizon.")

    lower = math.floor(time)
    upper = math.ceil(time)
    if upper > max(curve.spot_rates):
        raise DiscountingError(
            "OUTSIDE_CURVE_HORIZON", "Discount time exceeds the horizon of the supplied curve nodes."
        )
    if lower == upper:
        rate = curve.spot_rates.get(lower)
        if rate is None:
            raise DiscountingError("MISSING_NODE", f"Curve is missing the {lower}-year node.")
        return _discount_factor_at_node(lower, rate)

    lower_factor = 1.0 if lower == 0 else _node_factor(curve, lower)
    upper_factor = _node_factor(curve, upper)
    weight = time - lower
    try:
        result = math.exp((1.0 - weight) * math.log(lower_factor) + weight * math.log(upper_factor))
    except (OverflowError, ValueError) as error:
        raise DiscountingError("INTERPOLATION_FAILURE", "Discount-factor interpolation failed.") from error
    if not math.isfinite(result) or result <= 0:
        raise DiscountingError("INTERPOLATION_FAILURE", "Interpolated discount factor is not finite and positive.")
    return result


def _node_factor(curve: DiscountCurve, maturity: int) -> float:
    rate = curve.spot_rates.get(maturity)
    if rate is None:
        raise DiscountingError("MISSING_NODE", f"Curve is missing the {maturity}-year node.")
    return _discount_factor_at_node(maturity, rate)


def _as_date(value: Any, field: str) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{field} must be an ISO calendar date.") from error
    raise ValueError(f"{field} must be an ISO calendar date or date object.")


def _json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        converted = float(value)
        if not math.isfinite(converted):
            raise ValueError("Payment rows cannot contain non-finite numbers.")
        return converted
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, float, bool)):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("Payment rows cannot contain non-finite numbers.")
        return value
    if hasattr(value, "item"):
        return _json_value(value.item())
    raise ValueError(f"Payment row contains unsupported value type: {type(value).__name__}.")


def _finite_sum(values: list[float]) -> float | None:
    try:
        result = math.fsum(values)
    except OverflowError:
        return None
    return result if math.isfinite(result) else None


def _finite_difference(left: float | None, right: float | None) -> float | None:
    if left is None or right is None:
        return None
    result = left - right
    return result if math.isfinite(result) else None


def _group_totals(rows: list[dict[str, Any]], key: str) -> dict[str, dict[str, float | None]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        group_key = row["payment_date"][:4] if key == "payment_year" else str(row.get(key, ""))
        grouped.setdefault(group_key, []).append(row)

    groups: dict[str, dict[str, float | None]] = {}
    for group_key, group_rows in grouped.items():
        undiscounted = _finite_sum([row["amount"] for row in group_rows])
        discounted_values = [row["discounted_amount"] for row in group_rows]
        present_value = (
            None
            if any(value is None for value in discounted_values)
            else _finite_sum([value for value in discounted_values if value is not None])
        )
        groups[group_key] = {
            "undiscounted": undiscounted,
            "present_value": present_value,
            "discount_effect": _finite_difference(undiscounted, present_value),
        }
    return groups


def discount_payments(
    rows: list[Mapping[str, Any]],
    curve: DiscountCurve | None,
    valuation: date,
    currency: str,
    variant: str,
) -> dict[str, Any]:
    """Discount dated signed payments; retain all rows and undiscounted totals if blocked."""
    valuation_date = _as_date(valuation, "valuation")
    if not isinstance(currency, str) or not currency.strip():
        raise ValueError("Payment currency is required.")
    if variant not in {"no-VA", "with-VA"}:
        raise ValueError("Variant must be 'no-VA' or 'with-VA'.")

    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, Mapping):
            raise TypeError("Each payment row must be a mapping.")
        if "payment_date" not in row or "amount" not in row:
            raise ValueError("Each payment row requires payment_date and amount.")
        payment_date = _as_date(row["payment_date"], "payment_date")
        try:
            amount = float(row["amount"])
        except (TypeError, ValueError, OverflowError) as error:
            raise ValueError("Payment amount must be a finite number.") from error
        if not math.isfinite(amount):
            raise ValueError("Payment amount must be a finite number.")
        days = (payment_date - valuation_date).days
        if days < 0:
            raise ValueError("Payment date cannot precede the valuation date.")
        item = _json_value(dict(row))
        item.update(
            {
                "payment_date": payment_date.isoformat(),
                "amount": amount,
                "days_from_valuation": days,
                "time_years": days / 365,
                "discount_factor": None,
                "discounted_amount": None,
            }
        )
        normalized.append(item)

    total_undiscounted = _finite_sum([row["amount"] for row in normalized])
    status = "available"
    reason: str | None = None
    if total_undiscounted is None:
        status, reason = "blocked", "NUMERICAL_OVERFLOW"
    elif curve is None:
        status, reason = "blocked", "MISSING_CURVE"
    elif curve.valuation != valuation_date:
        status, reason = "blocked", "VALUATION_DATE_MISMATCH"
    elif curve.currency != currency:
        status, reason = "blocked", "CURRENCY_MISMATCH"
    elif curve.variant != variant:
        status, reason = "blocked", "VARIANT_MISMATCH"
    else:
        try:
            factors = [discount_factor(curve, row["time_years"]) for row in normalized]
        except DiscountingError as error:
            status, reason = "blocked", error.code
        else:
            products = [row["amount"] * factor for row, factor in zip(normalized, factors, strict=True)]
            if not all(math.isfinite(product) for product in products):
                status, reason = "blocked", "NUMERICAL_OVERFLOW"
            else:
                for row, factor, product in zip(normalized, factors, products, strict=True):
                    row["discount_factor"] = factor
                    row["discounted_amount"] = product

    by_origin = _group_totals(normalized, "origin")
    by_payment_year = _group_totals(normalized, "payment_year")
    total_present_value = (
        None
        if status == "blocked"
        else _finite_sum([row["discounted_amount"] for row in normalized if row["discounted_amount"] is not None])
    )
    if status == "available" and (
        total_present_value is None
        or _finite_difference(total_undiscounted, total_present_value) is None
        or any(
            total is None
            for group in (*by_origin.values(), *by_payment_year.values())
            for total in group.values()
        )
    ):
        status, reason = "blocked", "NUMERICAL_OVERFLOW"
        for row in normalized:
            row["discount_factor"] = None
            row["discounted_amount"] = None
        by_origin = _group_totals(normalized, "origin")
        by_payment_year = _group_totals(normalized, "payment_year")
        total_present_value = None

    totals = {
        "undiscounted": total_undiscounted,
        "present_value": total_present_value,
        "discount_effect": _finite_difference(total_undiscounted, total_present_value),
        "by_origin": by_origin,
        "by_payment_year": by_payment_year,
    }

    metadata = {
        "valuation": valuation_date.isoformat(),
        "currency": currency,
        "variant": variant,
        "day_count": "ACT/365F",
        "compounding": "annual_effective",
        "interpolation": "log_linear_discount_factor_v1",
        "status": status,
        "reason": reason,
        "curve_provenance": None if curve is None else dict(curve.provenance),
    }
    return {"status": status, "reason": reason, "rows": normalized, "totals": totals, "metadata": metadata}


def _safe_xml(archive: zipfile.ZipFile, name: str) -> ElementTree.Element:
    try:
        info = archive.getinfo(name)
    except KeyError as error:
        raise ValueError(f"Workbook is missing {name}.") from error
    if info.file_size > _MAX_XML_BYTES:
        raise ValueError("Workbook XML part exceeds the permitted size.")
    data = archive.read(info)
    try:
        builder = _RejectingDtdTreeBuilder()
        parser = ElementTree.XMLParser(target=builder)
        parser.feed(data)
        return parser.close()
    except ValueError:
        raise
    except ElementTree.ParseError as error:
        raise ValueError(f"Workbook contains malformed XML in {name}.") from error


class _RejectingDtdTreeBuilder(ElementTree.TreeBuilder):
    def doctype(self, name: str, public_id: str | None, system_id: str | None) -> None:
        raise ValueError("Workbook XML declarations are not accepted.")


def _cell_value(cell: ElementTree.Element, shared_strings: list[str]) -> str | None:
    cell_type = cell.attrib.get("t")
    if cell_type == "inlineStr":
        return "".join(node.text or "" for node in cell.iter(f"{{{_SPREADSHEET_NS}}}t"))
    value_node = cell.find(f"{{{_SPREADSHEET_NS}}}v")
    if value_node is None or value_node.text is None:
        return None
    if cell_type == "s":
        try:
            return shared_strings[int(value_node.text)]
        except (ValueError, IndexError) as error:
            raise ValueError("Workbook has an invalid shared-string reference.") from error
    return value_node.text


def _sheet_values(root: ElementTree.Element, shared_strings: list[str]) -> dict[str, str | None]:
    values: dict[str, str | None] = {}
    for cell in root.iter(f"{{{_SPREADSHEET_NS}}}c"):
        address = cell.attrib.get("r", "")
        if re.fullmatch(r"[A-Z]{1,3}[1-9][0-9]*", address):
            values[address] = _cell_value(cell, shared_strings)
    return values


def import_eiopa_curve_xlsx(
    data: bytes,
    variant: str,
    *,
    source_url: str,
    retrieved_at: str,
) -> DiscountCurve:
    """Parse a user-supplied EIOPA term-structures XLSX without external I/O or macros."""
    if variant not in {"no-VA", "with-VA"}:
        raise ValueError("Variant must be 'no-VA' or 'with-VA'.")
    if not isinstance(data, bytes) or not data or len(data) > _MAX_UPLOAD_BYTES:
        raise ValueError("Provide a nonempty XLSX upload no larger than 25 MiB.")
    if not source_url.strip() or not retrieved_at.strip():
        raise ValueError("Source URL and retrieval timestamp are required.")

    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except (zipfile.BadZipFile, OSError) as error:
        raise ValueError("Uploaded file is not a valid XLSX ZIP archive.") from error
    with archive:
        infos = archive.infolist()
        if len(infos) > _MAX_ARCHIVE_FILES or sum(item.file_size for item in infos) > _MAX_UNCOMPRESSED_BYTES:
            raise ValueError("Workbook exceeds the permitted archive size.")
        names = {item.filename for item in infos}
        for info in infos:
            path = PurePosixPath(info.filename)
            if path.is_absolute() or ".." in path.parts or info.flag_bits & 0x1:
                raise ValueError("Workbook contains an unsafe or encrypted archive member.")
        if any("vbaproject" in name.lower() or name.startswith("xl/externalLinks/") for name in names):
            raise ValueError("Macro-enabled workbooks and external links are not accepted.")
        content_types = archive.read("[Content_Types].xml") if "[Content_Types].xml" in names else b""
        if b"macroEnabled" in content_types or b"vbaProject" in content_types:
            raise ValueError("Macro-enabled workbooks are not accepted.")

        workbook = _safe_xml(archive, "xl/workbook.xml")
        relationships = _safe_xml(archive, "xl/_rels/workbook.xml.rels")
        relation_targets: dict[str, str] = {}
        for relation in relationships.findall(f"{{{_PACKAGE_REL_NS}}}Relationship"):
            if relation.attrib.get("TargetMode") == "External":
                raise ValueError("External workbook relationships are not accepted.")
            target = relation.attrib.get("Target", "")
            resolved = (
                posixpath.normpath(target.lstrip("/"))
                if target.startswith("/")
                else posixpath.normpath(posixpath.join("xl", target))
            )
            if not resolved.startswith("xl/") or ".." in PurePosixPath(resolved).parts:
                raise ValueError("Workbook contains an unsafe worksheet relationship.")
            relation_targets[relation.attrib.get("Id", "")] = resolved

        shared_strings: list[str] = []
        if "xl/sharedStrings.xml" in names:
            shared_root = _safe_xml(archive, "xl/sharedStrings.xml")
            for item in shared_root.findall(f"{{{_SPREADSHEET_NS}}}si"):
                shared_strings.append("".join(node.text or "" for node in item.iter(f"{{{_SPREADSHEET_NS}}}t")))

        sheet_name = f"RFR_spot_{variant.replace('-', '_')}"
        sheet_path: str | None = None
        for sheet in workbook.findall(f".//{{{_SPREADSHEET_NS}}}sheet"):
            if sheet.attrib.get("name") == sheet_name:
                sheet_path = relation_targets.get(sheet.attrib.get(f"{{{_OFFICE_REL_NS}}}id", ""))
                break
        if sheet_path is None:
            raise ValueError(f"Workbook does not contain the {sheet_name} sheet.")
        cells = _sheet_values(_safe_xml(archive, sheet_path), shared_strings)

    identifier = cells.get("C3") or ""
    match = re.fullmatch(r"EUR_(\d{2})_(\d{2})_(\d{4})_SWP_LLP_20_EXT_40_UFR_3\.30", identifier)
    if match is None:
        raise ValueError("Selected sheet has no recognized EUR curve identifier in cell C3.")
    day, month, year = map(int, match.groups())
    try:
        valuation = date(year, month, day)
    except ValueError as error:
        raise ValueError("Curve identifier contains an invalid valuation date.") from error

    def metadata_number(address: str, *, blank_ok: bool = False) -> float | None:
        raw = cells.get(address)
        if (raw is None or not raw.strip()) and blank_ok:
            return None
        try:
            return float(raw) if raw is not None else None
        except (TypeError, ValueError) as error:
            raise ValueError(f"Selected sheet has invalid source metadata in {address}.") from error

    # Read and retain the source parameter cells, and reject sheets whose identifiers do not agree.
    llp = metadata_number("C5")
    convergence = metadata_number("C6")
    ufr = metadata_number("C7")
    alpha = metadata_number("C8")
    cra = metadata_number("C9")
    va = metadata_number("C10", blank_ok=variant == "no-VA")
    numeric_metadata = (llp, convergence, ufr, alpha, cra)
    if any(value is None or not math.isfinite(value) for value in numeric_metadata):
        raise ValueError("Selected sheet has incomplete or non-finite curve source metadata.")
    if llp != 20 or convergence != 40 or not math.isclose(ufr, 3.30, rel_tol=0, abs_tol=1e-12):
        raise ValueError("Selected sheet has incomplete or unsupported curve source metadata.")
    if variant == "no-VA" and va is not None:
        raise ValueError("No-VA sheet unexpectedly contains a VA adjustment.")
    if variant == "with-VA" and (va is None or not math.isfinite(va) or va <= 0):
        raise ValueError("With-VA sheet is missing its published VA adjustment.")

    spot_rates: dict[int, float] = {}
    for maturity in range(1, 151):
        raw_maturity = cells.get(f"B{maturity + 10}")
        raw_rate = cells.get(f"C{maturity + 10}")
        try:
            published_maturity = float(raw_maturity) if raw_maturity is not None else math.nan
            rate = float(raw_rate) if raw_rate is not None else math.nan
        except (TypeError, ValueError) as error:
            raise ValueError(f"Selected sheet has invalid annual node at maturity {maturity}.") from error
        if published_maturity != maturity or not math.isfinite(rate) or rate <= -1:
            raise ValueError(f"Selected sheet has invalid or missing annual node at maturity {maturity}.")
        spot_rates[maturity] = rate

    provenance = {
        "source_url": source_url,
        "source_date": valuation.isoformat(),
        "content_hash": "sha256:" + hashlib.sha256(data).hexdigest(),
        "units": "decimal fractions; annual effective spot rates",
        "variant": variant,
        "retrieved_at": retrieved_at,
        "publication_reference": "EIOPA RFR term structures; source identifier from selected sheet cell C3",
        "curve_identifier": identifier,
        "sheet": sheet_name,
        "llp_years": str(llp),
        "convergence_years": str(convergence),
        "ufr": str(ufr),
        "ufr_percent": str(round(ufr, 8)),
        "ufr_units": "percent",
        "alpha": str(alpha),
        "cra": str(cra),
        "cra_basis_points": str(cra),
        "cra_units": "basis points",
        "va": "none" if va is None else str(va),
        "va_basis_points": "none" if va is None else str(va),
        "va_units": "basis points",
        "rate_units": "decimal fractions",
    }
    return DiscountCurve(valuation, "EUR", variant, spot_rates, provenance)
