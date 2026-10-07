"""Single-user, loopback-only reserving workspace. Run one uvicorn worker."""

import os
import threading
import time
from contextlib import asynccontextmanager
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
import polars as pl
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from actuarial_library import AnalysisConfig, build_triangles, export_results
from actuarial_library.agent import AnalystSession, ToolArgs, local_models
from actuarial_library.exploration import factor_triangle
from actuarial_library.review import method_impact, observation_pairs
from actuarial_library.workspace import WorkspaceStore, decode_session, encode_session

ROOT = Path(__file__).parent
store = WorkspaceStore(os.environ.get("ACTUARIAL_WORKSPACE_DB", ROOT / "local_runs/workspace.sqlite3"))
sessions = {}
lock = threading.RLock()
active = {}


@asynccontextmanager
async def lifespan(app):
    store.interrupt_jobs()
    yield


app = FastAPI(title="Actuarial Library", version="0.3.0", lifespan=lifespan)
app.mount("/web", StaticFiles(directory=ROOT / "web"), name="web")


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    # A remote website must not be able to command the local agent.
    host = request.url.hostname
    origin = request.headers.get("origin")
    if host not in {"127.0.0.1", "localhost", "testserver"}:
        return JSONResponse({"detail": "This workspace is local-only."}, status_code=403)
    if origin and origin != f"{request.url.scheme}://{request.url.netloc}":
        return JSONResponse({"detail": "Cross-origin requests are not allowed."}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Cache-Control"] = "no-store"
    return response


class AnalyseRequest(BaseModel):
    portfolio: Literal["Motor", "Liability"] = "Liability"
    grain: Literal["Y", "Q"] = "Y"
    valuation: date = date(2025, 12, 31)


class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=6000)
    model: str = Field(min_length=1, max_length=200)


class FeedbackRequest(BaseModel):
    kind: Literal["helpful", "problem", "idea"]
    message: str = Field(min_length=1, max_length=2000)


class ToolRequest(BaseModel):
    name: Literal[
        "inspect_observations", "compare_scenario", "create_artifact", "explain_library", "inspect_data"
    ]
    arguments: ToolArgs = Field(default_factory=ToolArgs)


@lru_cache(maxsize=1)
def demo_data():
    # Use bundled snapshots, so restarts do not regenerate a different source.
    return (
        pl.read_parquet(ROOT / "data/demo/claims.parquet"),
        pl.read_csv(ROOT / "data/demo/coverage.csv", try_parse_dates=True),
    )


def new_session(request):
    claims, coverage = demo_data()
    group = coverage.filter(pl.col("portfolio") == request.portfolio).row(0, named=True)
    triangle = build_triangles(
        claims,
        coverage,
        valuation=request.valuation,
        portfolio=request.portfolio,
        currency=group["currency"],
        amount_basis=group["amount_basis"],
        grain=request.grain,
    )
    return AnalystSession(triangle, AnalysisConfig())


def get_session(key):
    if key not in sessions:
        try:
            sessions[key] = decode_session(store.get("sessions", key))
        except KeyError as exc:
            raise HTTPException(404, "Saved workspace was not found. Open a new workspace.") from exc
    return sessions[key]


def save(key, session):
    store.put("sessions", key, encode_session(session))


def finite_matrix(values):
    return [[float(v) if np.isfinite(v) else None for v in row] for row in values]


def workspace_view(key, session):
    t = session.triangle
    return {
        "id": key,
        "metadata": t.metadata,
        "valuation": str(t.valuation),
        "grain": t.grain,
        "origins": t.origins,
        "states": t.states.tolist(),
        "triangles": {basis: finite_matrix(getattr(t, basis)) for basis in ("paid", "incurred", "count")},
        "development_factors": {
            basis: finite_matrix(factor_triangle(t, basis)) for basis in ("paid", "incurred", "count")
        },
        "analysis": session.baseline.to_dict(),
        "record": session.record(),
        "scenarios": [
            {
                "id": sid,
                "config": result.config.model_dump(mode="json"),
                "impact": method_impact(session.baseline, result).to_dicts(),
            }
            for sid, result in session.scenarios.items()
        ],
    }


@app.get("/api/health")
def health():
    try:
        models, error = local_models(), None
    except ValueError:
        models, error = [], "Open Ollama on this computer, then refresh models."
    return {
        "status": "ok",
        "ollama_models": models,
        "model_error": error,
        "processing": "Local only · no paid API key",
    }


@app.post("/api/workspaces")
def create_workspace(request: AnalyseRequest):
    with lock:
        try:
            session = new_session(request)
            key = uuid4().hex
            session.triangle.metadata["workspace_id"] = key
            session.baseline.metadata["workspace_id"] = key
            save(key, session)
            sessions[key] = session
            return workspace_view(key, session)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.get("/api/workspaces/{key}")
def read_workspace(key: str):
    with lock:
        if key in active:
            # Checkpoints are consistent even while model inference is in progress.
            return workspace_view(key, decode_session(store.get("sessions", key)))
        return workspace_view(key, get_session(key))


@app.get("/api/workspaces/{key}/observations")
def observations(key: str, basis: Literal["paid", "incurred", "count"] = "paid", development: int = 1):
    with lock:
        session = get_session(key)
        rows = observation_pairs(session.triangle, basis, getattr(session.config, basis))
        return rows.filter(pl.col("development") == development).to_dicts()


@app.post("/api/workspaces/{key}/tools")
def use_tool(key: str, request: ToolRequest):
    with lock:
        if key in active:
            raise HTTPException(409, "Wait for the analyst to finish before changing this workspace.")
        session = get_session(key)
        try:
            result = session.execute(request.name, request.arguments.model_dump())
            session.evidence.append(
                {
                    "id": f"T{len(session.evidence) + 1}",
                    "tool": request.name,
                    "arguments": request.arguments.model_dump(),
                    "result": result,
                }
            )
            save(key, session)
            return {"result": result, "workspace": workspace_view(key, session)}
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc


@app.post("/api/workspaces/{key}/explain")
def explain_library(key: str):
    with lock:
        if key in active:
            raise HTTPException(409, "Stop the current analyst task before adding a documentation answer.")
        session = get_session(key)
        answer = session.explain_directly()
        save(key, session)
        return {"answer": answer, "workspace": workspace_view(key, session)}


@app.post("/api/workspaces/{key}/feedback", status_code=201)
def feedback(key: str, request: FeedbackRequest):
    with lock:
        session = get_session(key)
        if not request.message.strip():
            raise HTTPException(422, "Enter a short description.")
        identifier = uuid4().hex
        store.put(
            "feedback",
            identifier,
            {
                "id": identifier,
                "workspace_id": key,
                "kind": request.kind,
                "message": request.message.strip(),
                "created_at": time.time(),
                "status": "new",
                "model": session.model_info.get("name"),
                "source": "user",
                "evidence_ids": [item["id"] for item in session.evidence],
            },
        )
        return {"id": identifier, "status": "Saved locally for review"}


def run_job(key, job_id, request, cancel):
    session = get_session(key)
    job = store.get("jobs", job_id)

    def checkpoint():
        with lock:
            save(key, session)

    def progress(message):
        if cancel.is_set():
            raise ValueError("Cancelled. Completed evidence and files have been saved.")
        with lock:
            job.update(status="running", progress=message)
            store.put("jobs", job_id, job)

    try:
        progress("Connecting to the local model…")
        answer = session.ask(request.prompt, request.model, progress=progress, checkpoint=checkpoint)
        job.update(
            status="cancelled"
            if cancel.is_set()
            else "paused"
            if answer.startswith("Analysis paused:")
            else "completed",
            answer=answer,
            progress=answer if answer.startswith("Analysis paused:") else "Saved locally",
        )
    except Exception as exc:  # noqa: BLE001 — record terminal failure for background jobs
        job.update(status="cancelled" if cancel.is_set() else "failed", progress=str(exc))
    finally:
        with lock:
            save(key, session)
            job["finished_at"] = time.time()
            store.put("jobs", job_id, job)
            if job["status"] in {"paused", "failed"}:
                store.put(
                    "feedback",
                    f"job_{job_id}",
                    {
                        "id": f"job_{job_id}",
                        "source": "runtime",
                        "kind": "problem",
                        "status": "new",
                        "workspace_id": key,
                        "job_id": job_id,
                        "model": request.model,
                        "created_at": time.time(),
                        "message": job["progress"],
                    },
                )
            active.pop(key, None)


@app.post("/api/workspaces/{key}/chat", status_code=202)
def chat(key: str, request: ChatRequest):
    with lock:
        get_session(key)
        if active:
            raise HTTPException(409, "The local analyst is already working. Wait or cancel the current task.")
        cancel = threading.Event()
        job_id = uuid4().hex
        job = {
            "id": job_id,
            "workspace_id": key,
            "status": "queued",
            "progress": "Waiting for local model",
            "started_at": time.time(),
            "prompt": request.prompt,
        }
        store.put("jobs", job_id, job)
        active[key] = (job_id, cancel)
        threading.Thread(target=run_job, args=(key, job_id, request, cancel), daemon=True).start()
        return job


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    try:
        return store.get("jobs", job_id)
    except KeyError as exc:
        raise HTTPException(404, "Task not found.") from exc


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    with lock:
        job = job_status(job_id)
        item = active.get(job["workspace_id"])
        if item and item[0] == job_id:
            item[1].set()
            job.update(
                status="cancelling",
                progress="Stopping local inference; completed work will be kept.",
            )
            store.put("jobs", job_id, job)
        return job


@app.get("/api/workspaces/{key}/files/{file_id}")
def download(key: str, file_id: str):
    with lock:
        session = decode_session(store.get("sessions", key)) if key in active else get_session(key)
        try:
            file = session.artifacts[file_id]
        except KeyError as exc:
            raise HTTPException(404, "File not found.") from exc
        return Response(
            file["content"],
            media_type=file["mime"],
            headers={"Content-Disposition": f'attachment; filename="{file["filename"]}"'},
        )


@app.get("/api/workspaces/{key}/export")
def export(key: str, scenario: str | None = None):
    with lock:
        session = decode_session(store.get("sessions", key)) if key in active else get_session(key)
        if scenario and scenario not in session.scenarios:
            raise HTTPException(404, "Scenario not found.")
        result = session.scenarios[scenario] if scenario else session.baseline
        return Response(
            export_results(result),
            media_type="application/zip",
            headers={
                "Content-Disposition": f'attachment; filename="reserving-{key[:8]}-{scenario or "baseline"}.zip"'
            },
        )


@app.get("/")
def frontend():
    return FileResponse(ROOT / "web/index.html")
