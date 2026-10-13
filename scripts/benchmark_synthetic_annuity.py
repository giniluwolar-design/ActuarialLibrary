"""Budgeted synthetic annuity baseline; normal package imports, no optimizations.

Use the installed project's Python. Each measured repeat runs in a fresh child
process. JSON output is measurement evidence, not an actuarial release gate.
"""

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
import tracemalloc
from dataclasses import asdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SIZES = (1, 10, 100)
WORKLOADS = (("regular", "annual"), ("regular", "monthly"),
             ("partner", "annual"), ("partner", "monthly"))


def identity():
    packages = {}
    for name in ("actuarial-library", "polars", "numpy", "pydantic"):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = "not installed"
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, timeout=1, stderr=subprocess.DEVNULL,
        ).decode().strip()
    except (OSError, subprocess.SubprocessError):
        commit = "unavailable"
    cpu = platform.processor() or "unreported by platform"
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.is_file():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                cpu = line.split(":", 1)[1].strip()
                break
    hashes = {}
    for path in (Path(__file__), ROOT / "src/actuarial_library/mortality.py",
                 ROOT / "src/actuarial_library/annuity.py"):
        hashes[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {
        "python": sys.version, "python_executable": sys.executable,
        "os": platform.platform(), "architecture": platform.machine(),
        "cpu_model": cpu, "logical_cpus_visible": os.cpu_count(),
        "cpu_affinity_count": len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else None,
        "packages": packages, "checkout_commit": commit, "file_sha256": hashes,
        "hardware_limit": "Guest-visible identity; not host capacity or guaranteed CPU allocation.",
    }


def peak_rss():
    try:
        import resource
    except ImportError:
        return None
    value = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    if sys.platform == "darwin":
        return value
    if sys.platform.startswith("linux"):
        return value * 1024
    return None


def worker(count, factor_type, frequency):
    # Explicitly select checkout source, then use the NORMAL package import;
    # __init__ and its dependencies must succeed. No namespace bypass/mocks.
    sys.path.insert(0, str(ROOT / "src"))
    import_started = time.perf_counter()
    try:
        from actuarial_library.annuity import DiscountFactorEvidence, calculate_annuity, payment_dates
        from actuarial_library.mortality import MortalityCell, MortalitySource
    except ImportError as error:
        return {"status": "blocked", "reason": f"Normal package import: {type(error).__name__}: {error}",
                "package_import_seconds": time.perf_counter() - import_started}
    import_seconds = time.perf_counter() - import_started
    tracemalloc.start()
    phases = {}

    def measure(name, function):
        before = tracemalloc.get_traced_memory()[0]
        tracemalloc.reset_peak()
        started = time.perf_counter()
        value = function()
        elapsed = time.perf_counter() - started
        current, peak = tracemalloc.get_traced_memory()
        phases[name] = {"seconds": elapsed, "python_traced_current_bytes": current,
                        "python_traced_peak_bytes": peak, "python_traced_start_bytes": before,
                        "python_traced_peak_growth_bytes": max(0, peak - before)}
        return value

    def construct():
        mortality = MortalitySource("benchmark-synthetic-v1", "Synthetic invented qx; not AG", tuple(
            MortalityCell(sex, age, year, .005 + .0005 * (age - 50) + .0002 * (year - 2026) + extra)
            for sex, extra in (("male", .001), ("female", 0))
            for age in range(50, 81) for year in range(2026, 2030)
        ))
        valuation, commencement, horizon = date(2026, 6, 30), date(2026, 7, 1), date(2029, 6, 30)
        dates = payment_dates(valuation, commencement, horizon, frequency=frequency, timing="ultimo")
        discount = DiscountFactorEvidence(
            valuation, "benchmark-flat-2-percent", "Synthetic annual-effective 2% fixture", "ACT/365F",
            tuple((day, 1.02 ** (-(day - valuation).days / 365)) for day in dates),
        )
        cases = []
        for index in range(count):
            cases.append({
                "source": mortality, "participant_dob": date(1956 + index % 12, 7, 1),
                "partner_dob": date(1960 + index % 12, 2, 29) if index % 12 in (0, 4, 8)
                else date(1960 + index % 12, 3, 1),
                "valuation_date": valuation, "commencement_date": commencement, "horizon": horizon,
                "frequency": frequency, "timing": "ultimo", "factor_type": factor_type,
                "participant_sex_weights": (("male", .4), ("female", .6)),
                "partner_sex_weights": (("male", .6), ("female", .4)), "discount_evidence": discount,
            })
            if factor_type == "regular":
                cases[-1].pop("partner_dob")
        return cases

    cases = measure("source_construction", construct)
    results = measure("calculation", lambda: [calculate_annuity(**case) for case in cases])
    with tempfile.TemporaryDirectory(prefix="synthetic-annuity-benchmark-") as directory:
        def export():
            payload = json.dumps([asdict(result) for result in results], default=str,
                                 allow_nan=False, sort_keys=True).encode()
            target = Path(directory) / "synthetic-traces.json"
            target.write_bytes(payload)
            return target.stat().st_size
        export_bytes = measure("export", export)
    rss = peak_rss()
    tracemalloc.stop()
    return {"status": "measured", "package_import_seconds": import_seconds, "phases": phases,
            "child_process_peak_rss_bytes": rss, "export_bytes": export_bytes,
            "payment_branch_rows": sum(len(result.payments) for result in results),
            "factor_sum": sum(result.factor for result in results)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--budget-seconds", type=float, default=20, help="Hard child execution budget, <=60 seconds")
    parser.add_argument("--repeats", type=int, default=3, help="Fresh child repeats per workload, 1..5")
    parser.add_argument("--output", type=Path, help="Optional new JSON file; existing files are preserved")
    parser.add_argument("--worker", nargs=3, metavar=("CASES", "TYPE", "FREQUENCY"), help=argparse.SUPPRESS)
    args = parser.parse_args()
    if not 0 < args.budget_seconds <= 60 or not 1 <= args.repeats <= 5:
        parser.error("Budget must be positive and <=60; repeats must be 1..5.")
    if args.worker:
        count, factor_type, frequency = args.worker
        if int(count) not in SIZES or (factor_type, frequency) not in WORKLOADS:
            parser.error("Unknown named worker workload.")
        print(json.dumps(worker(int(count), factor_type, frequency), allow_nan=False))
        return
    if args.output and args.output.exists():
        parser.error("Output already exists; choose a new path to preserve existing evidence.")
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
    started = time.perf_counter()
    report = {"schema": "synthetic-annuity-baseline-v1", "identity": identity(),
              "budget_seconds": args.budget_seconds, "requested_repeats": args.repeats,
              "fixtures": "248 synthetic qx cells, 3-year finite horizon from 2026-06-30, ultimo; no AG",
              "memory_method": "Instrumented timings with tracemalloc phase peaks (Python allocations only). "
              "Child process high-water RSS includes imports/all native allocations; not stage-specific. "
              "Export includes asdict/JSON serialization and temporary-file write, no fsync guarantee.",
              "repeat_method": "Fresh subprocess each repeat; cold Python imports, possible warm OS caches. "
              "All results retained through export; sequential workloads, not concurrent portfolio execution.",
              "measurements": []}
    blocked = None
    for count in SIZES:
        for factor_type, frequency in WORKLOADS:
            for repeat in range(1, args.repeats + 1):
                item = {"workload": f"synthetic-{factor_type}-{frequency}-{count}", "cases": count,
                        "factor_type": factor_type, "frequency": frequency, "repeat": repeat}
                remaining = args.budget_seconds - (time.perf_counter() - started)
                if blocked or remaining <= 0:
                    item.update(status="omitted", reason=blocked or "Total execution budget exhausted")
                else:
                    try:
                        completed = subprocess.run(
                            [sys.executable, str(Path(__file__).resolve()), "--worker", str(count),
                             factor_type, frequency], capture_output=True, text=True, timeout=remaining,
                            check=False,
                        )
                        if completed.returncode:
                            item.update(status="blocked", reason=f"Worker exited {completed.returncode}; "
                                        "inspect normal installed-project execution")
                        else:
                            item.update(json.loads(completed.stdout))
                        if item["status"] == "blocked":
                            blocked = item["reason"]
                    except subprocess.TimeoutExpired:
                        item.update(status="omitted", reason="Child terminated at total execution budget")
                    except (OSError, ValueError) as error:
                        blocked = f"Benchmark execution: {type(error).__name__}: {error}"
                        item.update(status="blocked", reason=blocked)
                report["measurements"].append(item)
    report["elapsed_seconds"] = time.perf_counter() - started
    payload = json.dumps(report, indent=2, allow_nan=False) + "\n"
    if args.output:
        with args.output.open("x") as target:
            target.write(payload)
    print(payload, end="")


if __name__ == "__main__":
    main()
