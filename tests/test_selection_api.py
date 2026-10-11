import csv
import io
import json
import sys
import threading
import time
import zipfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

import server
from actuarial_library.workspace import WorkspaceStore


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "store", WorkspaceStore(tmp_path / "workspace.sqlite3"))
    monkeypatch.setattr(server, "sessions", {})
    monkeypatch.setattr(server, "active", {})
    with TestClient(server.app) as test_client:
        yield test_client


def create_workspace(client):
    response = client.post("/api/workspaces", json={"portfolio": "Liability"})
    assert response.status_code == 200, response.text
    return response.json()


def choose(client, key, *, origin, method="paid_cl", note="Reviewed selection.", expected_revision=0, manual_ultimate=None):
    return client.post(
        f"/api/workspaces/{key}/selections",
        json={
            "origin": origin,
            "method": method,
            "note": note,
            "manual_ultimate": manual_ultimate,
            "expected_revision": expected_revision,
        },
    )


def test_selection_save_revision_and_baseline_scenario_artifact_immutability(client):
    initial = create_workspace(client)
    key = initial["id"]
    root = f"/api/workspaces/{key}"
    baseline = initial["analysis"]
    observations = client.get(root + "/observations?basis=paid&development=1").json()
    observed = next(row for row in observations if row["status"] == "Used")
    scenario = client.post(
        root + "/tools",
        json={
            "name": "compare_scenario",
            "arguments": {
                "basis": "paid",
                "exclude_origin": observed["origin"],
                "exclude_development": 1,
                "reason": "Compare an explicit selection with an unchanged scenario.",
            },
        },
    )
    assert scenario.status_code == 200
    before_selection = client.get(root).json()
    scenario_ids = [item["id"] for item in before_selection["scenarios"]]

    report = client.post(root + "/tools", json={"name": "create_artifact", "arguments": {"artifact": "report"}})
    assert report.status_code == 200
    before_files = client.get(root).json()["record"]["files"]

    response = choose(client, key, origin=observed["origin"])
    assert response.status_code == 200, response.text
    updated = response.json()
    assert updated["analysis"] == baseline
    assert [item["id"] for item in updated["scenarios"]] == scenario_ids
    assert updated["record"]["files"] == before_files
    assert updated["selection"]["revision"] == 1
    assert updated["selection"]["source_run"] == "baseline"
    assert updated["selection"]["authorship"] == {
        "actor": "local-user",
        "role": "analyst",
        "action": "reserve_selection",
    }
    assert updated["selection"]["analysis"]["config"]["selections"][observed["origin"]] == "paid_cl"
    assert updated["selection_history"] == [updated["selection"]]

    server.sessions.clear()
    restored = client.get(root).json()
    assert restored["selection"] == updated["selection"]
    assert restored["selection_history"] == [updated["selection"]]
    assert restored["analysis"] == baseline


def test_two_origin_partial_clear_then_manual_selection(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    first, second = workspace["origins"][-2:]

    first_choice = choose(client, key, origin=first, expected_revision=0)
    assert first_choice.status_code == 200, first_choice.text
    second_choice = choose(client, key, origin=second, expected_revision=1)
    assert second_choice.status_code == 200, second_choice.text
    assert second_choice.json()["selection"]["revision"] == 2

    cleared = choose(client, key, origin=first, method="clear", note="Clear the first origin.", expected_revision=2)
    assert cleared.status_code == 200, cleared.text
    assert cleared.json()["selection"]["revision"] == 3
    cleared_analysis = cleared.json()["selection"]["analysis"]
    assert first not in cleared_analysis["config"]["selections"]
    assert cleared_analysis["results"]
    assert not any(row["origin"] == first and row["selected"] for row in cleared_analysis["results"])

    paid = next(row["paid"] for row in workspace["analysis"]["results"] if row["origin"] == first)
    manual = choose(
        client,
        key,
        origin=first,
        method="manual",
        note="Set a documented manual ultimate.",
        manual_ultimate=paid + 25,
        expected_revision=3,
    )
    assert manual.status_code == 200, manual.text
    assert manual.json()["selection"]["revision"] == 4
    result = manual.json()["selection"]["analysis"]
    assert result["config"]["selections"][first] == "manual"
    assert result["config"]["selections"][second] == "paid_cl"
    manual_row = next(row for row in result["results"] if row["origin"] == first and row["method"] == "manual")
    assert manual_row["outstanding"] == pytest.approx(25)
    assert manual_row["selected"]


def test_clear_removes_only_current_origin_warning_and_keeps_historical_revision(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    origin = workspace["origins"][-1]
    baseline_warnings = workspace["analysis"]["warnings"]
    negative = choose(client, key, origin=origin, method="manual", manual_ultimate=-25.5)
    assert negative.status_code == 200
    historical = negative.json()["selection"]
    assert any(f"{origin} has negative" in warning for warning in historical["analysis"]["warnings"])

    cleared = choose(client, key, origin=origin, method="clear", note="Remove signed choice.", expected_revision=1)
    assert cleared.status_code == 200
    current = cleared.json()["selection"]
    assert not any(f"{origin} has negative" in warning for warning in current["analysis"]["warnings"])
    assert any(f"{origin} has negative" in warning for warning in cleared.json()["selection_history"][0]["analysis"]["warnings"])
    assert all(warning in current["analysis"]["warnings"] for warning in baseline_warnings)


def test_selection_optimistic_revision_conflict_and_unknown_revision(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    origin = workspace["origins"][-1]
    assert choose(client, key, origin=origin, expected_revision=0).status_code == 200
    conflict = choose(client, key, origin=origin, expected_revision=0)
    assert conflict.status_code == 409
    assert client.get(f"/api/workspaces/{key}/export?selection_revision=9").status_code == 404


def test_selection_payload_validation_and_unknown_origin(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    root = f"/api/workspaces/{key}/selections"
    origin = workspace["origins"][-1]
    assert client.post(root, json={"origin": origin, "method": "paid_cl"}).status_code == 422
    assert choose(client, key, origin="not-an-origin").status_code == 422
    assert choose(client, key, origin=origin, method="invented").status_code == 422
    assert choose(client, key, origin=origin, method="clear", manual_ultimate=100).status_code == 422
    assert choose(client, key, origin=origin, method="manual").status_code == 422
    assert choose(client, key, origin=origin, expected_revision=True).status_code == 422
    assert choose(
        client,
        key,
        origin=origin,
        method="manual",
        manual_ultimate=True,
    ).status_code == 422
    nonfinite = client.post(
        root,
        content=(
            '{"origin":"' + origin + '","method":"manual","note":"reason",'
            '"manual_ultimate":Infinity,"expected_revision":0}'
        ),
        headers={"Content-Type": "application/json"},
    )
    assert nonfinite.status_code == 422
    assert choose(client, key, origin=origin, note=" ").status_code == 422
    assert client.post(root, json={"origin": origin, "method": "paid_cl", "note": "ok", "expected_revision": -1}).status_code == 422
    assert client.post(
        root,
        json={
            "origin": origin,
            "method": "paid_cl",
            "note": "Reviewed selection.",
            "expected_revision": 0,
        },
        headers={"Origin": "https://untrusted.example"},
    ).status_code == 403


def test_oversized_integer_manual_ultimate_is_controlled_422_without_state_change(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    before = client.get(f"/api/workspaces/{key}").json()
    response = choose(
        client,
        key,
        origin=workspace["origins"][-1],
        method="manual",
        manual_ultimate=10**400,
    )
    assert response.status_code == 422
    after = client.get(f"/api/workspaces/{key}").json()
    assert after["analysis"] == before["analysis"]
    assert after["selection"] is None
    assert after["selection_history"] == []


def test_unavailable_saved_method_cannot_be_selected(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    response = choose(client, key, origin=workspace["origins"][0], method="frequency_severity")
    assert response.status_code == 422
    assert response.json()["detail"].lower().find("unavailable") >= 0


def test_selection_is_rejected_while_model_job_is_active(client, monkeypatch):
    workspace = create_workspace(client)
    key = workspace["id"]
    entered, release = threading.Event(), threading.Event()

    def slow_answer(self, prompt, model, **kwargs):
        entered.set()
        assert release.wait(5)
        return "Completed synthetic task."

    monkeypatch.setattr(server.AnalystSession, "ask", slow_answer)
    job = client.post(f"/api/workspaces/{key}/chat", json={"model": "test", "prompt": "wait"}).json()
    assert entered.wait(5)
    try:
        blocked = choose(client, key, origin=workspace["origins"][-1])
        assert blocked.status_code == 409
    finally:
        release.set()
    for _ in range(100):
        status = client.get(f"/api/jobs/{job['id']}").json()
        if status["status"] not in {"queued", "running"}:
            break
        time.sleep(0.02)
    assert status["status"] == "completed"


def test_failed_checkpoint_write_does_not_publish_selection(client, monkeypatch):
    workspace = create_workspace(client)
    key = workspace["id"]
    session = server.sessions[key]
    original_put = server.store.put

    def fail_session_write(table, identifier, value):
        if table == "sessions":
            raise OSError("synthetic checkpoint write failure")
        return original_put(table, identifier, value)

    monkeypatch.setattr(server.store, "put", fail_session_write)
    response = choose(client, key, origin=workspace["origins"][-1])
    assert response.status_code == 500
    assert getattr(session, "selection", None) is None
    assert getattr(session, "selection_history", []) == []
    assert client.get(f"/api/workspaces/{key}").json()["selection"] is None


def test_workspace_reload_restores_saved_analysis_without_recalculation(client, monkeypatch):
    workspace = create_workspace(client)
    key = workspace["id"]
    selected = choose(client, key, origin=workspace["origins"][-1])
    assert selected.status_code == 200
    before = selected.json()["selection"]
    server.sessions.clear()

    def no_recalculation(*args, **kwargs):
        raise AssertionError("Reload must restore the saved analysis, not recalculate it.")

    monkeypatch.setattr("actuarial_library.agent.run_reserving", no_recalculation)
    restored = client.get(f"/api/workspaces/{key}")
    assert restored.status_code == 200
    assert restored.json()["selection"] == before
    assert restored.json()["analysis"] == workspace["analysis"]


def test_export_uses_exact_selection_revision_and_includes_provenance(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    first, second = workspace["origins"][-2:]
    one = choose(client, key, origin=first)
    assert one.status_code == 200
    two = choose(client, key, origin=second, expected_revision=1)
    assert two.status_code == 200

    root = f"/api/workspaces/{key}/export"
    assert client.get(root + "?scenario=scenario_1&selection_revision=1").status_code == 422
    response = client.get(root + "?selection_revision=1")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        analysis = json.loads(archive.read("analysis.json"))
        csv = archive.read("results.csv").decode()
    assert analysis["metadata"]["selection_revision"] == 1
    assert analysis["metadata"]["selection_action_id"] == one.json()["selection"]["action_id"]
    assert analysis["metadata"]["source_run"] == "baseline"
    assert analysis["config"]["selections"].get(second) is None
    assert analysis["config"]["selections"][first] == "paid_cl"
    assert "selection_revision" in csv and "selection_action_id" in csv and "source_run" in csv
    assert client.get(root).status_code == 200  # Unversioned export remains the saved baseline.


def test_selection_export_preserves_each_origin_note_and_escapes_formula_note_once(client):
    workspace = create_workspace(client)
    key = workspace["id"]
    first, second = workspace["origins"][-2:]
    first_note = "=SUM(1,2)"
    second_note = "Reviewed separately."
    assert choose(client, key, origin=first, note=first_note).status_code == 200
    saved = choose(client, key, origin=second, note=second_note, expected_revision=1)
    assert saved.status_code == 200

    response = client.get(f"/api/workspaces/{key}/export?selection_revision=2")
    assert response.status_code == 200
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        analysis = json.loads(archive.read("analysis.json"))
        rows = list(csv.DictReader(io.StringIO(archive.read("results.csv").decode())))
    by_origin = {row["origin"]: row for row in rows if row["selected"] == "true"}
    assert by_origin[first]["selection_note"] == "'" + first_note
    assert by_origin[second]["selection_note"] == second_note
    assert by_origin[first]["selection_action_note"] == second_note
    assert by_origin[first]["selection_note"].count("'") == 1
    json_rows = {row["origin"]: row for row in analysis["results"] if row["selected"]}
    assert json_rows[first]["selection_note"] == first_note
    assert json_rows[second]["selection_note"] == second_note
    assert analysis["metadata"]["selection_action_note"] == second_note
