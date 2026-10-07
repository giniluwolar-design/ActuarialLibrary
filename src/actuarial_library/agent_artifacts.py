"""Downloadable drafts and synthetic test fixtures from validated library results."""

import io
import json
import zipfile

from .demo import generate_demo


def review_report(result):
    rows = result.results.to_dicts()
    lines = [
        "# Reserving review — exploratory draft",
        "",
        "This report uses calculated library results. Final actuarial selection and approval are not implied.",
        "",
        "## Run metadata",
        "```json",
        json.dumps(result.metadata, indent=2, default=str),
        "```",
        "",
        "## Method estimates by accident period",
        "| Origin | Method | Ultimate | Outstanding | Case reserve | Additional reserve | Selected |",
        "|---|---|---:|---:|---:|---:|---|",
    ]

    def amount(value):
        return "Unavailable" if value is None else f"{value:,.2f}"

    for r in rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    str(r["origin"]).replace("|", "\\|"),
                    r["method"],
                    *[
                        amount(r[k])
                        for k in ["ultimate", "outstanding", "case_reserve", "additional_reserve"]
                    ],
                    str(r["selected"]),
                ]
            )
            + " |"
        )
    lines += [
        "",
        "## Definitions",
        (
            "Outstanding = ultimate − paid. Case reserve = incurred − paid. "
            "Additional reserve = ultimate − incurred. BF means Bornhuetter–Ferguson."
        ),
        "",
        "## Assumptions",
        "```json",
        result.config.model_dump_json(indent=2),
        "```",
        "",
        "## Diagnostics",
        *[f"- {warning}" for warning in result.warnings],
        "",
        "## Review before use",
        (
            "Assess unusual development, reporting changes, tail assumptions and "
            "method suitability. This deterministic model does not quantify reserve uncertainty."
        ),
    ]
    return "\n".join(lines).encode()


def synthetic_test_package():
    claims, coverage, _ = generate_demo(claims_per_portfolio=40, seed=20260918)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("claims.csv", claims.write_csv())
        archive.writestr("coverage.csv", coverage.write_csv())
        archive.writestr(
            "README.txt",
            "Synthetic test data only. Seed 20260918; 40 latent claims per portfolio, "
            "Motor and Liability; quarterly snapshots through 2025-12-31. "
            "Load claims.csv and coverage.csv together in the app. Sparse data is intentional; "
            "some factors or methods may be unavailable. No future latent outcomes are included. "
            "Deductible is metadata only. This is a small input fixture, not a benchmark of accuracy.",
        )
    return buffer.getvalue()
