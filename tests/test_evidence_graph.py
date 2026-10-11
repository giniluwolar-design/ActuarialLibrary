import json

import pytest

from actuarial_library.evidence_graph import EvidenceGraphStore


def snapshot(scenarios=None):
    return {
        "triangle": {
            "origins": ["2022", "2023", "2024"],
            "origin_years": [2022, 2023, 2024],
            "grain": "Y",
            "valuation": "2024-12-31",
            "metadata": {"portfolio": "Synthetic", "claims_hash": "fixture-hash"},
            "states": [
                ["observed", "observed", "observed"],
                ["observed", "observed", "future"],
                ["observed", "future", "future"],
            ],
            "paid": [[100.0, 150.0, 180.0], [110.0, 165.0, None], [120.0, None, None]],
            "incurred": [[120.0, 170.0, 200.0], [130.0, 185.0, None], [140.0, None, None]],
            "count": [[2.0, 3.0, 4.0], [2.0, 0.0, None], [3.0, None, None]],
            "claims": "cHJpdmF0ZS1jbGFpbXMtYmxvYg==",
        },
        "config": {"paid": {"average": "volume"}, "incurred": {}, "count": {}},
        "baseline": {
            "results": [
                {"origin": "2022", "method": "paid_cl", "ultimate": 180.0, "outstanding": 0.0, "reason": ""},
                {"origin": "2023", "method": "paid_cl", "ultimate": 181.5, "outstanding": 71.5, "reason": ""},
                {"origin": "2024", "method": "paid_cl", "ultimate": None, "outstanding": None, "reason": "No valid factor."},
            ],
            "factors": [
                {"basis": "paid", "development": 1, "selected": 1.5, "origins_used": "2022, 2023", "pairs": 2},
                {"basis": "paid", "development": 2, "selected": 1.2, "origins_used": "2022", "pairs": 1},
                {"basis": "incurred", "development": 1, "selected": 1.4, "origins_used": "2022, 2023", "pairs": 2},
            ],
            "warnings": ["paid age 2: selected factor below one; inspect."],
            "config": {"paid": {"average": "volume"}, "incurred": {}, "count": {}},
            "metadata": {"version": "0.1", "valuation": "2024-12-31"},
        },
        "scenarios": scenarios or {},
        "evidence": [{"id": "T1", "tool": "inspect_data", "arguments": {}, "result": {"rows": 3}}],
        "artifacts": {"report": {"filename": "private.txt", "content": "c2VjcmV0"}},
    }


def test_materializes_result_factors_cells_and_scenario_scoped_membership(tmp_path):
    store = EvidenceGraphStore(tmp_path / "workspace.sqlite3")
    store.ensure_workspace("w1", snapshot())

    overview = store.summary("w1")
    result = next(row for row in overview["headline"] if row["origin"] == "2023")
    assert result["outstanding"] == 71.5
    result_node = store.node("w1", result["result_node_id"])
    assert result_node["node_class"] == "calc/result"
    unavailable = next(row for row in overview["headline"] if row["origin"] == "2024")
    assert unavailable["state"] == "missing"
    assert unavailable["reason_code"] == "factor_unavailable"

    source = next(node for node in overview["nodes"] if node["node_class"] == "data/source")
    related_cells = store.adjacency("w1", source["node_id"], limit=100)["items"]
    cells = [store.payload("w1", item["node_id"]) for item in related_cells if item["node_class"] == "triangle/cell"]
    assert any(cell["basis"] == "paid" and cell["origin"] == "2022" and cell["development"] == 1 for cell in cells)
    assert any(cell["basis"] == "paid" and cell["origin"] == "2022" and cell["development"] == 1 and cell["value"] == 100.0 for cell in cells)
    assert any(cell["basis"] == "count" and cell["origin"] == "2023" and cell["development"] == 2 and cell["value"] == 0.0 and cell["availability"] == "observed" for cell in cells)

    factor = next(node for node in overview["nodes"] if node["node_class"] == "calc/factor" and node["label"] == "paid age 1")
    adjacency = store.adjacency("w1", factor["node_id"])
    assert any(item["type"] == "used_observation" and item["direction"] == "outgoing" for item in adjacency["items"])
    membership = [item for item in adjacency["items"] if item["type"] == "used_observation"]
    assert all(item["metadata"]["fitting_membership"] == "included" for item in membership)

    legacy = store.node("w1", store.legacy_node_id("w1", "T1"))
    assert legacy["node_class"] == "tool/invocation"
    assert legacy["authorship"]["created_at"] == "unknown"
    assert store.payload("w1", legacy["node_id"]) == snapshot()["evidence"][0]


def test_idempotent_backfill_and_scenario_addition_preserve_baseline(tmp_path):
    path = tmp_path / "graph.sqlite3"
    store = EvidenceGraphStore(path)
    original = snapshot()
    store.ensure_workspace("w1", original)
    before = store.summary("w1")
    before_baseline = [n for n in before["nodes"] if n["run_id"] == "baseline"]
    store.ensure_workspace("w1", original)
    again = store.summary("w1")
    assert before["nodes"] == again["nodes"]

    scenario = json.loads(json.dumps(original["baseline"]))
    scenario["results"][0]["ultimate"] = 190.0
    scenario["config"] = {"paid": {"excluded": [["2022", 1]], "rationale": "Synthetic membership example."}}
    scenario["factors"][0]["origins_used"] = "2023"
    scenario["factors"][0]["pairs"] = 1
    original["scenarios"] = {"scenario_1": scenario}
    store.ensure_workspace("w1", original)
    after = store.summary("w1")
    assert [n for n in after["nodes"] if n["run_id"] == "baseline"] == before_baseline
    assert {item["run_id"] for item in after["scenarios"]} == {"scenario_1"}
    scenario_overview = store.summary("w1", "scenario_1")
    scenario_factor = next(n for n in scenario_overview["nodes"] if n["node_class"] == "calc/factor" and n["label"] == "paid age 1")
    scenario_edges = store.adjacency("w1", scenario_factor["node_id"])["items"]
    excluded_cell = next(item for item in scenario_edges if item["type"] == "used_observation" and item["metadata"]["fitting_membership"] == "excluded")
    assert store.payload("w1", excluded_cell["node_id"])["availability"] == "observed"
    exclusion_edges = store.adjacency("w1", excluded_cell["node_id"])["items"]
    assert any(item["type"] == "excludes" and item["node_class"] == "assumption/exclusion" for item in exclusion_edges)

    reopened = EvidenceGraphStore(path)
    assert reopened.summary("w1")["nodes"] == after["nodes"]


def test_legacy_ids_are_scoped_and_exports_exclude_private_payloads(tmp_path):
    store = EvidenceGraphStore(tmp_path / "graph.sqlite3")
    store.ensure_workspace("w1", snapshot())
    store.ensure_workspace("w2", snapshot())
    assert store.legacy_node_id("w1", "T1") != store.legacy_node_id("w2", "T1")

    invocation_id = store.legacy_node_id("w1", "T1")
    result_id = store.summary("w1")["headline"][0]["result_node_id"]
    store.write_edge("w1", {"type": "produced", "source_node_id": invocation_id, "source_revision": 1, "target_node_id": result_id, "target_revision": 1})

    export = store.export_review("w1")
    assert export["manifest"]["export_policy"] == "analyst_local_review"
    assert "artifact/private" in export["manifest"]["excluded_classes"]
    encoded = json.dumps(export)
    assert "private.txt" not in encoded
    assert "secret" not in encoded
    assert "T1" not in encoded
    assert export["manifest"]["included"]["metadata"] is True
    assert export["manifest"]["included"]["edges"] is True
    assert "calc/result" in export["manifest"]["included_classes"]
    exported_keys = {(node["node_id"], node["revision"]) for node in export["nodes"]}
    assert all((edge["source_node_id"], edge["source_revision"]) in exported_keys for edge in export["edges"])
    assert all((edge["target_node_id"], edge["target_revision"]) in exported_keys for edge in export["edges"])


def test_adjacency_pagination_is_stable_and_rejects_bad_cursors(tmp_path):
    store = EvidenceGraphStore(tmp_path / "graph.sqlite3")
    store.ensure_workspace("w1", snapshot())
    factor = next(n for n in store.summary("w1")["nodes"] if n["node_class"] == "calc/factor" and n["label"] == "paid age 1")
    first = store.adjacency("w1", factor["node_id"], limit=1)
    assert first["has_more"]
    second = store.adjacency("w1", factor["node_id"], limit=1, cursor=first["next_cursor"])
    assert first["items"][0]["edge_id"] < second["items"][0]["edge_id"]
    assert first["items"][0]["edge_id"] != second["items"][0]["edge_id"]

    # Concurrent additions do not alter the cursor's pinned edge set.
    extra = store.write_node("w1", {"node_class": "triangle/cell", "local_key": "late", "payload": {"value": 9}})
    store.write_edge("w1", {"type": "used_observation", "source_node_id": factor["node_id"], "source_revision": 1, "target_node_id": extra["node_id"], "target_revision": 1})
    cursor = first["next_cursor"]
    observed = [first["items"][0], second["items"][0]]
    while cursor:
        page = store.adjacency("w1", factor["node_id"], limit=1, cursor=cursor)
        observed.extend(page["items"])
        cursor = page["next_cursor"]
    assert extra["node_id"] not in [item["node_id"] for item in observed]
    with pytest.raises(ValueError):
        store.adjacency("w1", factor["node_id"], cursor="not-a-cursor")
    with pytest.raises(ValueError):
        store.adjacency("w1", factor["node_id"], cursor="W10")

    assert len(json.dumps(store.summary("w1")).encode()) <= 100_000
    assert len(json.dumps(store.adjacency("w1", factor["node_id"])["items"]).encode()) <= 50_000


def test_node_revisions_are_immutable_and_edge_types_validate_both_classes(tmp_path):
    store = EvidenceGraphStore(tmp_path / "graph.sqlite3")
    first = store.write_node(
        "w1",
        {"node_class": "calc/result", "run_id": "baseline", "local_key": "synthetic", "payload": {"value": 1}},
    )
    revised = store.write_node(
        "w1",
        {"node_id": first["node_id"], "node_class": "calc/result", "run_id": "baseline", "local_key": "synthetic", "payload": {"value": 2}},
    )
    assert revised["revision"] == 2
    assert store.payload("w1", first["node_id"], revision=1) == {"value": 1}
    relabelled = store.write_node(
        "w1",
        {"node_id": first["node_id"], "node_class": "calc/result", "run_id": "baseline", "local_key": "synthetic", "label": "Reviewed synthetic", "payload": {"value": 2}},
    )
    assert relabelled["revision"] == 3
    assert store.node("w1", first["node_id"], revision=2)["label"] == "synthetic"

    narrative = store.write_node("w1", {"node_class": "narrative/explanation", "local_key": "n", "payload": {}})
    with pytest.raises(ValueError):
        store.write_edge("w1", {"type": "derived_from", "source_node_id": first["node_id"], "source_revision": 1, "target_node_id": narrative["node_id"], "target_revision": 1})
    factor = store.write_node("w1", {"node_class": "calc/factor", "local_key": "f", "payload": {}})
    with pytest.raises(ValueError):
        store.write_edge("w1", {"type": "derived_from", "source_node_id": factor["node_id"], "source_revision": 1, "target_node_id": first["node_id"], "target_revision": 1})
    edge = store.write_edge("w1", {"type": "explains", "source_node_id": narrative["node_id"], "source_revision": 1, "target_node_id": first["node_id"], "target_revision": 1})
    assert edge["type"] == "explains"


def test_backfill_failure_rolls_back_nodes_edges_and_marker(tmp_path):
    store = EvidenceGraphStore(tmp_path / "graph.sqlite3")
    broken = snapshot()
    broken["evidence"] = [{"id": "T1", "tool": "inspect", "result": {"nonfinite": float("nan")}}]
    with pytest.raises(ValueError):
        store.ensure_workspace("w1", broken)
    assert store.summary("w1")["nodes"] == []
    with pytest.raises(KeyError):
        store.legacy_node_id("w1", "T1")


def test_large_summary_keeps_every_headline_and_pages_factor_stubs(tmp_path):
    store = EvidenceGraphStore(tmp_path / "large-quarterly.sqlite3")
    for origin_index in range(80):
        origin = f"{2000 + origin_index // 4}Q{origin_index % 4 + 1}"
        for method in ("paid_cl", "incurred_cl", "paid_bf", "incurred_bf", "frequency_severity"):
            key = f"{origin}:{method}"
            store.write_node(
                "large",
                {
                    "node_class": "calc/result",
                    "local_key": key,
                    "label": key,
                    "payload": {"origin": origin, "method": method, "ultimate": 1000.25, "outstanding": 400.125},
                    "summary": {"origin": origin, "method": method, "ultimate": 1000.25, "outstanding": 400.125, "availability": "observed"},
                },
            )
    for basis in ("paid", "incurred", "count"):
        for age in range(1, 81):
            store.write_node(
                "large",
                {"node_class": "calc/factor", "local_key": f"{basis}:{age}", "label": f"{basis} age {age}", "payload": {"selected": 1.02}},
            )

    first = store.summary("large", node_limit=50)
    assert len(first["headline"]) == 400
    assert first["node_pagination"]["has_more"]
    assert len(json.dumps(first, separators=(",", ":")).encode()) <= 100_000
    cursor = first["node_pagination"]["next_cursor"]
    factor_ids = [node["node_id"] for node in first["nodes"] if node["node_class"] == "calc/factor"]
    while cursor:
        page = store.summary("large", node_limit=50, node_cursor=cursor)
        factor_ids.extend(node["node_id"] for node in page["nodes"] if node["node_class"] == "calc/factor")
        cursor = page["node_pagination"]["next_cursor"]
    assert len(factor_ids) == 240
    assert len(set(factor_ids)) == 240


def test_default_adjacency_page_stays_within_l1_budget(tmp_path):
    store = EvidenceGraphStore(tmp_path / "large-adjacency.sqlite3")
    factor = store.write_node("large", {"node_class": "calc/factor", "local_key": "paid:1", "payload": {}})
    for index in range(200):
        cell = store.write_node(
            "large",
            {"node_class": "triangle/cell", "local_key": f"cell:{index}", "label": f"paid 2026Q{index % 4 + 1} age 1", "payload": {"value": float(index)}},
        )
        store.write_edge(
            "large",
            {"type": "used_observation", "source_node_id": factor["node_id"], "source_revision": 1, "target_node_id": cell["node_id"], "target_revision": 1, "metadata": {"fitting_membership": "included", "scenario_run_id": "baseline"}},
        )
    page = store.adjacency("large", factor["node_id"])
    all_items = []
    while page:
        assert len(json.dumps(page, separators=(",", ":")).encode()) <= 50_000
        all_items.extend(page["items"])
        if not page["next_cursor"]:
            break
        page = store.adjacency("large", factor["node_id"], cursor=page["next_cursor"])
    assert len(all_items) == 200
    assert len({item["edge_id"] for item in all_items}) == 200
