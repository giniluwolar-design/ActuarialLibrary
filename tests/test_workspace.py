"""Workflow checks at the same API boundary used by the browser."""

import io
import json
import sys
import time
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
fastapi = pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

import server
from actuarial_library.workspace import WorkspaceStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "store", WorkspaceStore(tmp_path / "workspace.sqlite3"))
    monkeypatch.setattr(server, "sessions", {})
    monkeypatch.setattr(server, "active", {})
    with TestClient(server.app) as client:
        yield client


def test_saved_scenario_report_and_export_keep_the_same_run(client):
    response = client.post("/api/workspaces", json={"portfolio": "Liability"})
    assert response.status_code == 200, response.text
    baseline = response.json()
    key = baseline["id"]
    root = f"/api/workspaces/{key}"
    observations = client.get(root + "/observations?basis=paid&development=1").json()
    observed = next(row for row in observations if row["status"] == "Used")
    response = client.post(
        root + "/tools",
        json={
            "name": "compare_scenario",
            "arguments": {
                "basis": "paid",
                "exclude_origin": observed["origin"],
                "exclude_development": 1,
                "reason": "Investigate a settlement pattern",
            },
        },
    )
    assert response.status_code == 200, response.text
    scenario = response.json()["workspace"]
    assert scenario["analysis"] == baseline["analysis"]
    assert len(scenario["scenarios"]) == 1
    report = client.post(
        root + "/tools", json={"name": "create_artifact", "arguments": {"artifact": "report"}}
    ).json()
    file_id = report["result"]["file_id"]
    download = client.get(root + f"/files/{file_id}")
    assert download.status_code == 200
    assert key in download.text and "Liability" in download.text
    assert "attachment" in download.headers["Content-Disposition"]
    before = client.get(root).json()
    # Reconstruct every object from disk, as after process restart.
    server.sessions.clear()
    after = client.get(root).json()
    assert after == before
    assert client.get(root + f"/files/{file_id}").content == download.content
    archive = zipfile.ZipFile(io.BytesIO(client.get(root + "/export?scenario=scenario_1").content))
    record = json.loads(archive.read("analysis.json"))
    assert record["metadata"]["workspace_id"] == key
    assert record["config"]["paid"]["excluded"] == [[observed["origin"], 1]]
    assert record["results"][0]["selected"] is False
    assert client.get(root + "/export?scenario=missing").status_code == 404
    invalid = client.post(root + "/tools", json={"name": "compare_scenario", "arguments": {"tail": 1.1}})
    assert invalid.status_code == 422


def test_health_is_available_without_ollama_and_remote_commands_blocked(client, monkeypatch):
    def offline():
        raise ValueError("offline")

    monkeypatch.setattr(server, "local_models", offline)
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["ollama_models"] == []
    assert (
        client.post("/api/workspaces", json={}, headers={"Origin": "https://untrusted.example"}).status_code
        == 403
    )
    assert client.get("/api/health", headers={"Host": "untrusted.example"}).status_code == 403
    assert client.post("/api/workspaces", json={"portfolio": "Missing"}).status_code == 422


def test_async_agent_checkpoints_transcript_and_marks_interrupted_jobs(client, monkeypatch):
    key = client.post("/api/workspaces", json={"portfolio": "Motor"}).json()["id"]
    original_ask = server.AnalystSession.ask

    def fake_ask(self, prompt, model, **kwargs):
        responses = iter(
            [
                {
                    "message": {
                        "tool_calls": [
                            {"function": {"name": "explain_library", "arguments": {"topic": "run_reserving"}}}
                        ]
                    }
                },
                {"message": {"content": "run_reserving takes a triangle and config [T1]."}},
            ]
        )
        return original_ask(self, prompt, model, chat=lambda _: next(responses), **kwargs)

    monkeypatch.setattr(server.AnalystSession, "ask", fake_ask)
    job = client.post(
        f"/api/workspaces/{key}/chat", json={"model": "test", "prompt": "Explain the API"}
    ).json()
    for _ in range(100):
        status = client.get(f"/api/jobs/{job['id']}").json()
        if status["status"] not in {"queued", "running"}:
            break
        time.sleep(0.02)
    assert status["status"] == "completed", status
    server.sessions.clear()
    restored = client.get(f"/api/workspaces/{key}").json()
    assert len(restored["record"]["transcript"]) == 2
    assert restored["record"]["evidence"][0]["tool"] == "explain_library"
    server.store.put("jobs", "interrupted", {"status": "running"})
    server.store.interrupt_jobs()
    assert server.store.get("jobs", "interrupted")["status"] == "interrupted"


def test_cancellation_preserves_completed_file_and_blocks_next_tool(client, monkeypatch):
    import threading

    key = client.post("/api/workspaces", json={"portfolio": "Motor"}).json()["id"]
    entered, release = threading.Event(), threading.Event()
    original_ask = server.AnalystSession.ask

    def fake_ask(self, prompt, model, **kwargs):
        count = 0

        def local_chat(_):
            nonlocal count
            count += 1
            if count == 2:
                entered.set()
                assert release.wait(5)
            return {
                "message": {
                    "tool_calls": [
                        {"function": {"name": "create_artifact", "arguments": {"artifact": "report"}}}
                    ]
                }
            }

        return original_ask(self, prompt, model, chat=local_chat, **kwargs)

    monkeypatch.setattr(server.AnalystSession, "ask", fake_ask)
    job = client.post(f"/api/workspaces/{key}/chat", json={"model": "test", "prompt": "Make a report"}).json()
    assert entered.wait(5)
    try:
        assert client.post(f"/api/jobs/{job['id']}/cancel").json()["status"] == "cancelling"
    finally:
        release.set()
    for _ in range(100):
        status = client.get(f"/api/jobs/{job['id']}").json()
        if status["status"] == "cancelled":
            break
        time.sleep(0.02)
    assert status["status"] == "cancelled"
    server.sessions.clear()
    restored = client.get(f"/api/workspaces/{key}").json()
    assert len(restored["record"]["files"]) == 1
    assert len(restored["record"]["evidence"]) == 1
    assert client.get(f"/api/workspaces/{key}/files/file_1").status_code == 200


def test_direct_documentation_and_local_feedback_need_no_model(client, monkeypatch):
    def no_model(*args, **kwargs):
        raise AssertionError("Documentation should not use the model")

    monkeypatch.setattr(server.AnalystSession, "ask", no_model)
    key = client.post("/api/workspaces", json={"portfolio": "Motor"}).json()["id"]
    response = client.post(f"/api/workspaces/{key}/explain", json={})
    assert response.status_code == 200
    assert "run_reserving(triangle: Triangle" in response.json()["answer"]
    assert "[T1]" in response.json()["answer"]
    server.sessions.clear()
    restored = client.get(f"/api/workspaces/{key}").json()
    assert len(restored["record"]["transcript"]) == 2
    saved = client.post(
        f"/api/workspaces/{key}/feedback", json={"kind": "helpful", "message": "Keep this direct explanation"}
    )
    assert saved.status_code == 201
    item = server.store.get("feedback", saved.json()["id"])
    assert item["workspace_id"] == key and item["evidence_ids"] == ["T1"]
    assert item["status"] == "new"
    assert (
        client.post(f"/api/workspaces/{key}/feedback", json={"kind": "problem", "message": " "}).status_code
        == 422
    )
