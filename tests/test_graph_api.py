"""Saved-checkpoint Evidence Graph routes and download contract."""

import base64
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
pytest.importorskip("fastapi")
pytest.importorskip("httpx")
from fastapi.testclient import TestClient

import server
from actuarial_library.evidence_graph import EvidenceGraphStore
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
    return response.json()["id"]


def test_graph_exposes_saved_result_factor_and_observation_links(client):
    key = create_workspace(client)
    root = f"/api/workspaces/{key}/graph"
    summary_response = client.get(root)
    assert summary_response.status_code == 200, summary_response.text
    summary = summary_response.json()
    assert summary["run_id"] == "baseline"
    result = max(
        (item for item in summary["headline"] if item["method"] == "paid_cl"),
        key=lambda item: int(item["origin"]),
    )
    result_response = client.get(root + f"/nodes/{result['result_node_id']}")
    assert result_response.status_code == 200
    assert result_response.json()["node_class"] == "calc/result"

    result_edges = client.get(root + f"/nodes/{result['result_node_id']}/adjacency").json()["items"]
    factors = [edge for edge in result_edges if edge["type"] == "derived_from" and edge["node_class"] == "calc/factor"]
    observation = None
    for factor_ref in factors:
        factor = client.get(root + f"/nodes/{factor_ref['node_id']}").json()
        assert factor["node_class"] == "calc/factor"
        factor_edges = client.get(root + f"/nodes/{factor_ref['node_id']}/adjacency").json()["items"]
        observation = next((edge for edge in factor_edges if edge["type"] == "used_observation"), None)
        if observation:
            break
    assert observation is not None
    cell = client.get(root + f"/nodes/{observation['node_id']}/payload").json()
    assert cell["availability"] == "observed"
    assert cell["basis"] == "paid"


def test_graph_uses_saved_checkpoint_and_survives_session_cache_restart(client):
    key = create_workspace(client)
    path = f"/api/workspaces/{key}/graph"
    before = client.get(path).json()
    server.sessions.clear()
    after = client.get(path).json()
    assert after == before


def test_scenario_fitting_membership_is_saved_and_run_scoped(client):
    key = create_workspace(client)
    root = f"/api/workspaces/{key}"
    observations = client.get(root + "/observations?basis=paid&development=1").json()
    selected = next(item for item in observations if item["status"] == "Used")
    changed = client.post(
        root + "/tools",
        json={
            "name": "compare_scenario",
            "arguments": {
                "basis": "paid",
                "exclude_origin": selected["origin"],
                "exclude_development": selected["development"],
                "reason": "Inspect the synthetic fitting membership.",
            },
        },
    )
    assert changed.status_code == 200, changed.text
    graph_root = root + "/graph?run=scenario_1"
    scenario = client.get(graph_root).json()
    assert scenario["run_id"] == "scenario_1"
    factor_stub = next(item for item in scenario["nodes"] if item["node_class"] == "calc/factor" and item["label"] == "paid age 1")
    adjacency = client.get(root + f"/graph/nodes/{factor_stub['node_id']}/adjacency").json()
    excluded = next(item for item in adjacency["items"] if item["type"] == "used_observation" and item["metadata"]["fitting_membership"] == "excluded")
    cell = client.get(root + f"/graph/nodes/{excluded['node_id']}/payload").json()
    assert cell["availability"] == "observed"


def test_export_is_an_actual_private_payload_filtered_json_download(client):
    key = create_workspace(client)
    checkpoint = server.store.get("sessions", key)
    checkpoint["artifacts"] = {
        "fixture": {
            "filename": "private-fixture.txt",
            "mime": "text/plain",
            "content": base64.b64encode(b"private synthetic payload").decode("ascii"),
        }
    }
    server.store.put("sessions", key, checkpoint)

    response = client.get(f"/api/workspaces/{key}/graph/export?run=baseline")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/json")
    assert "attachment" in response.headers["content-disposition"]
    assert ".json" in response.headers["content-disposition"]
    exported = response.json()
    assert exported["manifest"]["export_policy"] == "analyst_local_review"
    assert "artifact/private" in exported["manifest"]["excluded_classes"]
    assert "private-fixture.txt" not in json.dumps(exported)
    assert "private synthetic payload" not in response.text


def test_missing_graph_workspace_node_and_run_and_invalid_pagination(client):
    missing = "0" * 32
    assert client.get(f"/api/workspaces/{missing}/graph").status_code == 404
    key = create_workspace(client)
    root = f"/api/workspaces/{key}/graph"
    assert client.get(root + "?run=not-saved").status_code == 404
    assert client.get(root + "/nodes/not-a-node").status_code == 404
    result = client.get(root).json()["headline"][0]
    node_id = result["result_node_id"]
    assert client.get(root + f"/nodes/{node_id}/adjacency?limit=0").status_code == 422
    assert client.get(root + f"/nodes/{node_id}/adjacency?cursor=not-a-cursor").status_code == 400
    assert client.get(root + "?node_cursor=not-a-cursor").status_code == 400


def test_graph_routes_keep_the_existing_local_origin_boundary(client):
    key = create_workspace(client)
    response = client.get(
        f"/api/workspaces/{key}/graph",
        headers={"Origin": "https://untrusted.example"},
    )
    assert response.status_code == 403


def test_large_graph_summary_pages_factor_stubs_without_dropping_headlines(client):
    key = create_workspace(client)
    graph = EvidenceGraphStore(server.store.path)
    for index in range(55):
        graph.write_node(
            key,
            {"node_class": "calc/factor", "run_id": "baseline", "local_key": f"extra:{index}", "label": f"extra factor {index}", "payload": {"selected": 1.01}},
        )
    path = f"/api/workspaces/{key}/graph?node_limit=20"
    first = client.get(path).json()
    assert first["node_pagination"]["has_more"]
    all_factors = [node["node_id"] for node in first["nodes"] if node["node_class"] == "calc/factor"]
    cursor = first["node_pagination"]["next_cursor"]
    headline_ids = {row["result_node_id"] for row in first["headline"]}
    while cursor:
        response = client.get(path + "&node_cursor=" + cursor)
        assert response.status_code == 200, response.text
        page = response.json()
        assert {row["result_node_id"] for row in page["headline"]} == headline_ids
        all_factors.extend(node["node_id"] for node in page["nodes"] if node["node_class"] == "calc/factor")
        cursor = page["node_pagination"]["next_cursor"]
    assert len(all_factors) == first["counts"]["factor_nodes"]
    assert len(set(all_factors)) == len(all_factors)
