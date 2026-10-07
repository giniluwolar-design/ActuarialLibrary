"""Reproducible, fictitious claim snapshots. Latent outcomes are never analysis input."""

import argparse
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import polars as pl

from .data import period_end, period_index


def generate_demo(claims_per_portfolio=2000, seed=20260914, cutoff=date(2025, 12, 31)):
    rng = np.random.default_rng(seed)
    records, truth = [], []
    ends = [period_end(i, "Q") for i in range(2006 * 4, period_index(cutoff, "Q") + 1)]
    coverage = [
        {
            "portfolio": p,
            "currency": "EUR",
            "amount_basis": "after_deductible",
            "valuation_date": d,
            "complete": True,
        }
        for p in ["Motor", "Liability"]
        for d in ends
    ]
    for portfolio in ("Motor", "Liability"):
        slow = portfolio == "Liability"
        for k in range(claims_per_portfolio):
            year = 2006 + k % 20
            accident = date(year, 1, 1) + timedelta(days=int(rng.integers(0, 365)))
            lag = int(rng.exponential(100 if slow else 12))
            if k % 47 == 0:
                lag += 450
            report = accident + timedelta(days=lag)
            amount = float(rng.lognormal(np.log(18000 if slow else 2200), 0.9) * (1.025 ** (year - 2006)))
            if k % 113 == 0:
                amount *= 12
            if k % 29 == 0:
                amount = 0
            ultimate = round(amount, 2)
            duration = int(rng.integers(900, 3000) if slow else rng.integers(90, 900))
            closed_date = report + timedelta(days=duration)
            deductible = float(rng.choice([0, 250, 500, 1000]))
            claim_id = f"{portfolio[:3].upper()}-{k + 1:06d}"
            truth.append(
                {
                    "portfolio": portfolio,
                    "claim_id": claim_id,
                    "accident_date": accident,
                    "report_date": report,
                    "ultimate": ultimate,
                    "settlement_date": closed_date,
                }
            )
            # The simulator knows the lifetime; the exported snapshots only expose information at that date.
            for at in ends:
                if at < report:
                    continue
                elapsed = (at - report).days
                progress = min(1.0, elapsed / duration)
                fraction = np.floor(progress * 8) / 8 if progress < 1 else 1
                paid = round(ultimate * fraction, 2)
                closed = progress >= 1
                # Temporary closure followed by reopening, with no future knowledge in status.
                temporary_close = k % 37 == 0 and 0.35 <= progress < 0.50
                reserve = (
                    0
                    if closed or temporary_close
                    else round(
                        max(0, ultimate - paid) * (1 + 0.22 * np.sin(elapsed / 180 + k) * (1 - progress)), 2
                    )
                )
                records.append(
                    {
                        "portfolio": portfolio,
                        "claim_id": claim_id,
                        "accident_date": accident,
                        "report_date": report,
                        "valuation_date": at,
                        "status": "closed" if closed or temporary_close else "open",
                        "paid": paid,
                        "case_reserve": reserve,
                        "deductible": deductible,
                        "currency": "EUR",
                        "amount_basis": "after_deductible",
                    }
                )
    return pl.DataFrame(records), pl.DataFrame(coverage), pl.DataFrame(truth)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("data/demo"))
    parser.add_argument("--claims-per-portfolio", type=int, default=2000)
    args = parser.parse_args()
    if args.claims_per_portfolio < 20:
        parser.error("Use at least 20 claims per portfolio.")
    claims, coverage, _ = generate_demo(args.claims_per_portfolio)
    args.output.mkdir(parents=True, exist_ok=True)
    claims.write_parquet(args.output / "claims.parquet")
    coverage.write_csv(args.output / "coverage.csv")
    # Small, intentional defects, kept separate from the clean demo.
    sample = claims.head(8).with_columns(
        pl.col("valuation_date").cast(pl.String),
        pl.col("accident_date").cast(pl.String),
        pl.col("report_date").cast(pl.String),
    )
    bad = sample.to_dicts()
    bad[1]["paid"] = -10
    bad[2]["report_date"] = "2099-01-01"
    bad[3]["status"], bad[3]["case_reserve"] = "closed", 500
    bad[4]["amount_basis"] = "unknown"
    bad.append(bad[0].copy())
    pl.DataFrame(bad).write_csv(args.output / "invalid_claims.csv")
    print(f"Created {claims.height:,} snapshots; latent truth was not exported.")


if __name__ == "__main__":
    main()
