"""Measure import, validation/triangle build, fit and sampled peak RSS separately."""

import json
import platform
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

import polars as pl
import psutil

from actuarial_library import build_triangles, run_reserving
from actuarial_library.demo import generate_demo


def measure(n):
    d, c, _ = generate_demo(n)
    with tempfile.TemporaryDirectory() as folder:
        path = Path(folder) / "claims.parquet"
        d.write_parquet(path)
        del d
        process = psutil.Process()
        peak = [process.memory_info().rss]
        stop = threading.Event()

        def sample():
            while not stop.wait(0.01):
                peak[0] = max(peak[0], process.memory_info().rss)

        thread = threading.Thread(target=sample, daemon=True)
        thread.start()
        start = time.perf_counter()
        d = pl.read_parquet(path)
        imported = time.perf_counter()
        t = build_triangles(d, c, valuation=date(2025, 12, 31), portfolio="Motor")
        built = time.perf_counter()
        run_reserving(t)
        fitted = time.perf_counter()
        stop.set()
        thread.join()
    return {
        "claims_per_portfolio": n,
        "snapshot_rows": d.height,
        "import_seconds": imported - start,
        "validation_and_triangle_seconds": built - imported,
        "fit_seconds": fitted - built,
        "sampled_peak_rss_mb": peak[0] / 1024**2,
    }


if __name__ == "__main__":
    out = {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "note": "One run per size, warm OS caches possible. Peak is total process RSS sampled every 10ms; generation excluded.",
        "results": [measure(2000), measure(10000)],
    }
    root = Path(__file__).resolve().parents[1]
    (root / "docs/benchmark.json").write_text(json.dumps(out, indent=2))
    print(json.dumps(out, indent=2))
