"""Single-user, loopback-only reserving workspace. Run one uvicorn worker."""

import io
import json
import os
import re
import threading
import time
import zipfile
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from functools import lru_cache
from pathlib import Path
from typing import Literal
from uuid import uuid4

import numpy as np
import polars as pl
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt

from actuarial_library import AnalysisConfig, build_triangles, export_results
from actuarial_library.agent import AnalystSession, ToolArgs, local_models
from actuarial_library.evidence_graph import EvidenceGraphStore
from actuarial_library.exploration import factor_triangle
from actuarial_library.export import safe_csv
from actuarial_library.models import AnalysisResult, StrictModel
from actuarial_library.review import method_impact, observation_pairs
from actuarial_library.selections import select_reserve
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


class SelectionRequest(StrictModel):
    # Let the library reject Infinity/NaN so FastAPI does not echo a non-JSON float
    # from its validation details; select_reserve still requires finite values.
    model_config = ConfigDict(extra="forbid", allow_inf_nan=True)

    origin: str = Field(min_length=1, max_length=80)
    method: Literal[
        "paid_cl",
        "incurred_cl",
        "paid_bf",
        "incurred_bf",
        "frequency_severity",
        "manual",
        "clear",
    ]
    note: str = Field(min_length=1, max_length=2000)
    manual_ultimate: StrictFloat | StrictInt | None = None
    expected_revision: StrictInt = Field(ge=0)


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
        "selection": getattr(session, "selection", None),
        "selection_history": getattr(session, "selection_history", []),
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


@app.post("/api/workspaces/{key}/selections")
def save_selection(key: str, request: SelectionRequest):
    with lock:
        if key in active:
            raise HTTPException(409, "Wait for the analyst to finish before changing this workspace.")
        try:
            checkpoint = store.get("sessions", key)
        except KeyError as exc:
            raise HTTPException(404, "Saved workspace was not found.") from exc
        previous = checkpoint.get("selection")
        revision = previous["revision"] if previous else 0
        if request.expected_revision != revision:
            raise HTTPException(409, f"Selection revision changed; expected {revision}.")
        session = get_session(key)
        source_analysis = analysis_from_snapshot(previous["analysis"]) if previous else session.baseline
        try:
            analysis = select_reserve(
                source_analysis,
                request.origin,
                request.method,
                request.note,
                request.manual_ultimate,
            )
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        action_id = uuid4().hex
        created_at = datetime.now(UTC).isoformat()
        authorship = {"actor": "local-user", "role": "analyst", "action": "reserve_selection"}
        record = {
            "revision": revision + 1,
            "action_id": action_id,
            "created_at": created_at,
            "authorship": authorship,
            "source_run": "baseline",
            "origin": request.origin,
            "method": request.method,
            "note": request.note.strip(),
            "manual_ultimate": request.manual_ultimate,
            "analysis": analysis.to_dict(),
        }
        history = [*checkpoint.get("selection_history", []), record]
        snapshot = encode_session(session)
        snapshot["selection"] = record
        snapshot["selection_history"] = history
        try:
            store.put("sessions", key, snapshot)
        except Exception as exc:
            raise HTTPException(500, "Could not save the selection checkpoint.") from exc
        session.selection = record
        session.selection_history = history
        sessions[key] = session
        return workspace_view(key, session)


def graph_for_saved_workspace(key: str, run: str = "baseline"):
    """Backfill the graph from the saved checkpoint, never from a live session."""
    with lock:
        try:
            snapshot = store.get("sessions", key)
        except KeyError as exc:
            raise HTTPException(404, "Saved workspace was not found.") from exc
        if run != "baseline" and run not in snapshot.get("scenarios", {}):
            raise HTTPException(404, "Saved scenario was not found.")
        graph = EvidenceGraphStore(store.path)
        graph.ensure_workspace(key, snapshot)
        return graph


@app.get("/api/workspaces/{key}/graph")
def graph_summary(
    key: str,
    run: str = "baseline",
    node_limit: int = Query(default=50, ge=1, le=200),
    node_cursor: str | None = None,
):
    graph = graph_for_saved_workspace(key, run)
    try:
        return graph.summary(key, run, node_limit=node_limit, node_cursor=node_cursor)
    except ValueError as exc:
        raise HTTPException(400 if node_cursor is not None else 422, str(exc)) from exc


@app.get("/api/workspaces/{key}/graph/nodes/{node_id}")
def graph_node(key: str, node_id: str, revision: int = Query(default=1, ge=1)):
    graph = graph_for_saved_workspace(key)
    try:
        return graph.node(key, node_id, revision)
    except KeyError as exc:
        raise HTTPException(404, "Graph node revision was not found.") from exc


@app.get("/api/workspaces/{key}/graph/nodes/{node_id}/adjacency")
def graph_adjacency(
    key: str,
    node_id: str,
    revision: int = Query(default=1, ge=1),
    limit: int = Query(default=200, ge=1, le=2000),
    cursor: str | None = None,
):
    graph = graph_for_saved_workspace(key)
    try:
        return graph.adjacency(key, node_id, revision=revision, limit=limit, cursor=cursor)
    except KeyError as exc:
        raise HTTPException(404, "Graph node revision was not found.") from exc
    except ValueError as exc:
        raise HTTPException(400 if cursor is not None else 422, str(exc)) from exc


@app.get("/api/workspaces/{key}/graph/nodes/{node_id}/payload")
def graph_payload(key: str, node_id: str, revision: int = Query(default=1, ge=1)):
    graph = graph_for_saved_workspace(key)
    try:
        return graph.payload(key, node_id, revision)
    except KeyError as exc:
        raise HTTPException(404, "Graph node revision was not found.") from exc


@app.get("/api/workspaces/{key}/graph/export")
def graph_export(key: str, run: str = "baseline"):
    graph = graph_for_saved_workspace(key, run)
    content = json.dumps(graph.export_review(key, run), ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    filename_run = re.sub(r"[^A-Za-z0-9_.-]", "_", run)[:64] or "baseline"
    return Response(
        content,
        media_type="application/json",
        headers={"Content-Disposition": f'attachment; filename="evidence-graph-{key[:8]}-{filename_run}.json"'},
    )


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


def analysis_from_snapshot(payload):
    return AnalysisResult(
        results=pl.DataFrame(payload["results"], infer_schema_length=None),
        factors=pl.DataFrame(payload["factors"], infer_schema_length=None),
        history=pl.DataFrame(payload["history"], infer_schema_length=None),
        warnings=payload["warnings"],
        config=AnalysisConfig.model_validate(payload["config"]),
        metadata=payload["metadata"],
    )


def export_selection(record):
    authorship = record["authorship"]
    analysis = analysis_from_snapshot(record["analysis"])
    metadata = {
        **analysis.metadata,
        "selection_revision": record["revision"],
        "selection_action_id": record["action_id"],
        "source_run": record["source_run"],
        "selection_created_at": record["created_at"],
        "selection_origin": record["origin"],
        "selection_method": record["method"],
        "selection_action_note": record["note"],
        "selection_authorship": authorship,
    }
    selected_analysis = AnalysisResult(
        results=analysis.results,
        factors=analysis.factors,
        history=analysis.history,
        warnings=analysis.warnings,
        config=analysis.config,
        metadata=metadata,
    )
    buffer = io.BytesIO()
    selection_columns = {
        "selection_revision": str(record["revision"]),
        "selection_action_id": record["action_id"],
        "source_run": record["source_run"],
        "selection_created_at": record["created_at"],
        "selection_origin": record["origin"],
        "selection_method": record["method"],
        "selection_action_note": record["note"],
        "selection_actor": authorship["actor"],
        "selection_role": authorship["role"],
        "selection_action": authorship["action"],
    }
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        result_frame = analysis.results.with_columns(
            [pl.lit(value).alias(column) for column, value in selection_columns.items()]
        )
        archive.writestr("results.csv", safe_csv(result_frame).encode())
        archive.writestr("factors.csv", safe_csv(analysis.factors).encode())
        archive.writestr("history.csv", safe_csv(analysis.history).encode())
        archive.writestr("analysis.json", json.dumps(selected_analysis.to_dict(), indent=2, allow_nan=False))
    return buffer.getvalue()


@app.get("/api/workspaces/{key}/export")
def export(key: str, scenario: str | None = None, selection_revision: int | None = Query(default=None, ge=1)):
    with lock:
        if scenario is not None and selection_revision is not None:
            raise HTTPException(422, "Choose either a scenario or a human selection revision.")
        session = decode_session(store.get("sessions", key)) if key in active else get_session(key)
        if selection_revision is not None:
            record = next(
                (item for item in getattr(session, "selection_history", []) if item["revision"] == selection_revision),
                None,
            )
            if record is None:
                raise HTTPException(404, "Selection revision was not found.")
            return Response(
                export_selection(record),
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="reserving-{key[:8]}-selection-r{selection_revision}.zip"'
                },
            )
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
