"""Local JSON/SQLite checkpoints for the single-user browser workspace."""

import base64
import io
import json
import sqlite3
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl

from .agent import AnalystSession
from .models import AnalysisConfig, AnalysisResult, Triangle


def encode_session(session):
    t = session.triangle
    snapshot = {
        "origins": t.origins,
        "origin_years": t.origin_years,
        "grain": t.grain,
        "valuation": str(t.valuation),
        "metadata": t.metadata,
        "states": t.states.tolist(),
    }
    for basis in ("paid", "incurred", "count"):
        snapshot[basis] = [[float(v) if np.isfinite(v) else None for v in row] for row in getattr(t, basis)]
    if t.claims is not None:
        buffer = io.BytesIO()
        t.claims.write_parquet(buffer)
        snapshot["claims"] = base64.b64encode(buffer.getvalue()).decode()
    return {
        "triangle": snapshot,
        "config": session.config.model_dump(mode="json"),
        "messages": session.messages,
        "transcript": session.transcript,
        "evidence": session.evidence,
        "model_info": session.model_info,
        "baseline": session.baseline.to_dict(),
        "scenarios": {key: value.to_dict() for key, value in session.scenarios.items()},
        "artifacts": {
            key: {**value, "content": base64.b64encode(value["content"]).decode()}
            for key, value in session.artifacts.items()
        },
    }


def decode_session(data):
    raw = dict(data["triangle"])
    claims = raw.pop("claims", None)
    raw["valuation"] = date.fromisoformat(raw["valuation"])
    for basis in ("paid", "incurred", "count"):
        raw[basis] = np.array(raw[basis], dtype=float)
    raw["states"] = np.array(raw["states"])
    raw["claims"] = pl.read_parquet(io.BytesIO(base64.b64decode(claims))) if claims else None
    session = AnalystSession(Triangle(**raw), AnalysisConfig.model_validate(data["config"]))
    for name in ("messages", "transcript", "evidence", "model_info"):
        setattr(session, name, data[name])

    def result_from_dict(result):
        return AnalysisResult(
            **{
                name: pl.DataFrame(result[name], infer_schema_length=None)
                for name in ("results", "factors", "history")
            },
            config=AnalysisConfig.model_validate(result["config"]),
            warnings=result["warnings"],
            metadata=result["metadata"],
        )

    session.baseline = result_from_dict(data["baseline"])
    session.scenarios = {key: result_from_dict(result) for key, result in data["scenarios"].items()}
    session.artifacts = {
        key: {**value, "content": base64.b64decode(value["content"])}
        for key, value in data["artifacts"].items()
    }
    return session


class WorkspaceStore:
    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE IF NOT EXISTS feedback (id TEXT PRIMARY KEY, payload TEXT NOT NULL)")

    def connect(self):
        return sqlite3.connect(self.path, timeout=15)

    def put(self, table, key, value):
        assert table in {"sessions", "jobs", "feedback"}
        with self.connect() as db:
            db.execute(
                f"INSERT OR REPLACE INTO {table} VALUES (?, ?)", (key, json.dumps(value, allow_nan=False))
            )

    def get(self, table, key):
        assert table in {"sessions", "jobs", "feedback"}
        with self.connect() as db:
            row = db.execute(f"SELECT payload FROM {table} WHERE id = ?", (key,)).fetchone()
        if row is None:
            raise KeyError(key)
        return json.loads(row[0])

    def interrupt_jobs(self):
        with self.connect() as db:
            rows = db.execute("SELECT id, payload FROM jobs").fetchall()
        for key, raw in rows:
            job = json.loads(raw)
            if job["status"] in {"running", "queued", "cancelling"}:
                job.update(
                    status="interrupted",
                    progress="Server restarted. Saved evidence is available; ask a follow-up to continue.",
                )
                self.put("jobs", key, job)
