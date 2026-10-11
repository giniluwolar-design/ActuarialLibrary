import json
from datetime import date

import numpy as np
import pytest

from actuarial_library.agent import AnalystSession
from actuarial_library.evidence_graph import GRAPH_MIGRATION_VERSION, EvidenceGraphStore
from actuarial_library.models import AnalysisConfig, Triangle
from actuarial_library.workspace import encode_session


def annual_session(config=None):
    paid = np.array([[100.0, 200.0, 240.0], [120.0, 240.0, np.nan], [150.0, np.nan, np.nan]])
    incurred = paid + np.where(np.isfinite(paid), 10.0, 0.0)
    triangle = Triangle(
        origins=["2023", "2024", "2025"],
        origin_years=[2023, 2024, 2025],
        grain="Y",
        valuation=date(2025, 12, 31),
        paid=paid,
        incurred=incurred,
        count=np.array([[2.0, 3.0, 3.0], [2.0, 3.0, np.nan], [1.0, np.nan, np.nan]]),
        states=np.array([["observed", "observed", "observed"], ["observed", "observed", "future"], ["observed", "future", "future"]]),
        metadata={"portfolio": "Synthetic annual triangle"},
    )
    return encode_session(AnalystSession(triangle, config or AnalysisConfig()))


def quarterly_session():
    origins = [f"{year}Q{quarter}" for year in (2023, 2024, 2025) for quarter in range(1, 5)]
    origin_years = [int(origin[:4]) for origin in origins]
    n = len(origins)
    paid = np.full((n, n), np.nan)
    incurred = np.full((n, n), np.nan)
    count = np.full((n, n), np.nan)
    for index in range(n):
        for age_index in range(n - index):
            paid[index, age_index] = 100 + 2 * index + 20 * age_index
            incurred[index, age_index] = paid[index, age_index] + 10
            count[index, age_index] = 1 + age_index
    triangle = Triangle(
        origins=origins,
        origin_years=origin_years,
        grain="Q",
        valuation=date(2025, 12, 31),
        paid=paid,
        incurred=incurred,
        count=count,
        states=np.where(np.isfinite(paid), "observed", "future"),
        metadata={"portfolio": "Synthetic quarterly triangle"},
    )
    return encode_session(AnalystSession(triangle, AnalysisConfig()))


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
                {"origin": "2022", "method": "paid_cl", "ultimate": 180.0, "paid": 180.0, "incurred": 200.0, "outstanding": 0.0, "additional_reserve": -20.0, "reason": ""},
                {"origin": "2023", "method": "paid_cl", "ultimate": 181.5, "paid": 165.0, "incurred": 185.0, "outstanding": 71.5, "additional_reserve": -3.5, "reason": ""},
                {"origin": "2024", "method": "paid_cl", "ultimate": None, "paid": 120.0, "incurred": 140.0, "outstanding": None, "additional_reserve": None, "reason": "No valid factor."},
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


def test_factor_lineage_covers_both_pair_cells_and_results_cover_latest_basis_cells(tmp_path):
    store = EvidenceGraphStore(tmp_path / "lineage.sqlite3")
    fixture = snapshot()
    scenario = json.loads(json.dumps(fixture["baseline"]))
    scenario["config"] = {"paid": {"excluded": [["2022", 1]]}}
    scenario["factors"][0]["origins_used"] = "2023"
    scenario["factors"][1]["origins_used"] = ""
    fixture["scenarios"] = {"scenario_1": scenario}
    store.ensure_workspace("w1", fixture)

    scenario_factor = next(
        node for node in store.summary("w1", "scenario_1")["nodes"]
        if node["node_class"] == "calc/factor" and node["label"] == "paid age 1"
    )
    links = [
        item for item in store.adjacency("w1", scenario_factor["node_id"])["items"]
        if item["type"] == "used_observation"
    ]
    by_origin = {}
    for link in links:
        payload = store.payload("w1", link["node_id"])
        by_origin.setdefault(payload["origin"], {})[link["metadata"].get("cell_role")] = (
            payload,
            link["metadata"],
        )
    assert set(by_origin["2022"]) == {"denominator", "numerator"}
    assert {edge[1]["fitting_membership"] for edge in by_origin["2022"].values()} == {"excluded"}
    assert {edge[1]["scenario_run_id"] for edge in by_origin["2022"].values()} == {"scenario_1"}
    assert {edge[0]["development"] for edge in by_origin["2022"].values()} == {1, 2}
    assert {edge[1]["fitting_membership"] for edge in by_origin["2023"].values()} == {"included"}

    age_two = next(
        node for node in store.summary("w1", "scenario_1")["nodes"]
        if node["node_class"] == "calc/factor" and node["label"] == "paid age 2"
    )
    age_two_links = [
        item for item in store.adjacency("w1", age_two["node_id"])["items"]
        if item["type"] == "used_observation"
    ]
    assert {item["metadata"]["fitting_membership"] for item in age_two_links} == {"outside-window"}
    assert {store.payload("w1", item["node_id"])["development"] for item in age_two_links} == {2, 3}

    result = next(
        row for row in store.summary("w1", "scenario_1")["headline"]
        if row["origin"] == "2023" and row["method"] == "paid_cl"
    )
    result_links = store.adjacency("w1", result["result_node_id"])["items"]
    cells_by_role = {
        item["metadata"]["cell_role"]: store.payload("w1", item["node_id"])
        for item in result_links
        if item["type"] == "derived_from" and item["node_class"] == "triangle/cell"
    }
    assert cells_by_role["latest_paid"]["origin"] == "2023"
    assert cells_by_role["latest_paid"]["development"] == 2
    assert cells_by_role["latest_paid"]["value"] == 165.0
    assert cells_by_role["latest_incurred"]["origin"] == "2023"
    assert cells_by_role["latest_incurred"]["development"] == 2
    assert cells_by_role["latest_incurred"]["value"] == 185.0


def test_node_revision_changes_for_privacy_and_preserves_prior_metadata(tmp_path):
    store = EvidenceGraphStore(tmp_path / "metadata.sqlite3")
    base = {
        "node_class": "calc/result",
        "run_id": "baseline",
        "local_key": "privacy-check",
        "label": "Synthetic result",
        "payload": {"value": 1},
        "summary": {"value": 1},
        "state": "observed",
        "evidential_role": "calculation_evidence",
        "authorship": {"actor": "reviewer", "role": "analyst", "action": "create", "created_at": "fixture"},
        "private": False,
    }
    first = store.write_node("w1", base)
    second = store.write_node("w1", {**base, "private": True})
    assert second["revision"] == first["revision"] + 1
    assert first["private"] is False
    assert second["private"] is True
    exported = store.export_review("w1")
    exported_revisions = {(node["node_id"], node["revision"]) for node in exported["nodes"] if node["node_id"] == first["node_id"]}
    assert exported_revisions == {(first["node_id"], 1)}

    third = store.write_node("w1", {**base, "private": True, "state": "missing", "reason_code": "fixture_missing"})
    assert third["revision"] == second["revision"] + 1
    assert store.node("w1", first["node_id"], revision=1)["state"] == "observed"
    assert store.node("w1", first["node_id"], revision=2)["state"] == "observed"
    assert store.node("w1", first["node_id"], revision=3)["reason_code"] == "fixture_missing"


def test_frequency_severity_uses_saved_history_and_count_mode_not_blanket_factors(tmp_path):
    store = EvidenceGraphStore(tmp_path / "fs-lineage.sqlite3")
    fixture = snapshot()
    fixture["config"]["frequency_severity"] = {
        "count_mode": "manual",
        "expected_counts": {"2023": 5.0},
        "historical_ultimates": {"2022": 420.0},
        "historical_counts": {"2022": 2.0},
        "rationale": "Synthetic manual calibration inputs.",
    }
    baseline = fixture["baseline"]
    baseline["config"] = fixture["config"]
    baseline["history"] = [{"target": "2023", "year": 2022, "ultimate": 420.0, "count": 2.0, "trend_factor": 1.0, "trended_severity": 210.0}]
    baseline["factors"].append({"basis": "count", "development": 1, "selected": 1.5, "origins_used": "2022, 2023", "pairs": 2})
    baseline["results"].extend([
        {"origin": "2023", "method": "frequency_severity", "ultimate": 1050.0, "paid": 165.0, "incurred": 185.0, "outstanding": 885.0, "additional_reserve": 865.0, "expected_count": 5.0, "severity": 210.0, "prior_source": "frequency_severity", "prior": 1050.0, "history_years": "2022", "reason": ""},
        {"origin": "2023", "method": "paid_bf", "ultimate": 1000.0, "paid": 165.0, "incurred": 185.0, "outstanding": 835.0, "additional_reserve": 815.0, "expected_count": 5.0, "prior_source": "manual", "prior": 1000.0, "history_years": "2022", "reason": ""},
    ])
    store.ensure_workspace("w1", fixture)
    overview = store.summary("w1")
    fs_result = next(row for row in overview["headline"] if row["origin"] == "2023" and row["method"] == "frequency_severity")
    fs_edges = store.adjacency("w1", fs_result["result_node_id"])["items"]
    assert not any(item["node_class"] == "calc/factor" for item in fs_edges)
    history_edge = next(item for item in fs_edges if item["node_class"] == "assumption/parameter" and item["label"] == "2023 calibration 2022")
    history_payload = store.payload("w1", history_edge["node_id"])
    assert history_payload["ultimate"] == 420.0
    count_input = next(item for item in fs_edges if item["node_class"] == "assumption/parameter" and item["label"] == "2023 expected count")
    assert store.payload("w1", count_input["node_id"])["value"] == 5.0

    bf_result = next(row for row in overview["headline"] if row["origin"] == "2023" and row["method"] == "paid_bf")
    bf_edges = store.adjacency("w1", bf_result["result_node_id"])["items"]
    assert any(item["type"] == "derived_from" and item["node_class"] == "assumption/parameter" and item["label"] == "2023 manual expected ultimate prior" for item in bf_edges)


def test_prior_v3_marker_rebuilds_lineage_without_mutating_saved_results_or_history(tmp_path):
    path = tmp_path / "old-preview.sqlite3"
    store = EvidenceGraphStore(path)
    fixture = snapshot()
    fixture["config"]["frequency_severity"] = {
        "count_mode": "manual",
        "expected_counts": {"2023": 5.0},
        "historical_ultimates": {"2022": 420.0},
        "historical_counts": {"2022": 2.0},
        "rationale": "Synthetic old-preview migration fixture.",
    }
    baseline = fixture["baseline"]
    baseline["config"] = fixture["config"]
    baseline["history"] = [{"target": "2023", "year": 2022, "ultimate": 420.0, "count": 2.0, "trend_factor": 1.0, "trended_severity": 210.0}]
    baseline["factors"].append({"basis": "count", "development": 1, "selected": 1.5, "origins_used": "2022, 2023", "pairs": 2})
    baseline["results"].append({"origin": "2023", "method": "frequency_severity", "ultimate": 1050.0, "paid": 165.0, "incurred": 185.0, "outstanding": 885.0, "additional_reserve": 865.0, "expected_count": 5.0, "severity": 210.0, "prior_source": "frequency_severity", "prior": 1050.0, "history_years": "2022", "reason": ""})
    saved_baseline = json.loads(json.dumps(baseline))
    store.ensure_workspace("w1", fixture)

    overview = store.summary("w1")
    factor = next(node for node in overview["nodes"] if node["node_class"] == "calc/factor" and node["label"] == "incurred age 1")
    result_id = next(row["result_node_id"] for row in overview["headline"] if row["origin"] == "2023" and row["method"] == "frequency_severity")
    old_payload = store.payload("w1", result_id)
    store.write_edge("w1", {"type": "derived_from", "source_node_id": result_id, "source_revision": 1, "target_node_id": factor["node_id"], "target_revision": factor["revision"]})
    store.write_edge("w1", {"type": "derived_from", "source_node_id": result_id, "source_revision": 1, "target_node_id": next(node["node_id"] for node in overview["nodes"] if node["node_class"] == "calc/factor" and node["label"] == "count age 1"), "target_revision": 1})

    # Model the already-published graph v3 preview: same snapshot hash, old
    # marker, v3 result/factor revisions, and saved calibration rows without
    # actual input ancestors.
    with store.connect() as db:
        for node_class in ("calc/result", "calc/factor"):
            rows = db.execute("SELECT node_id, revision, summary_json FROM evidence_graph_nodes WHERE workspace_id=? AND node_class=?", ("w1", node_class)).fetchall()
            for row in rows:
                old_summary = json.loads(row["summary_json"])
                old_summary["lineage_version"] = "evidence-graph-v3-lineage"
                db.execute("UPDATE evidence_graph_nodes SET summary_json=? WHERE workspace_id=? AND node_id=? AND revision=?", (json.dumps(old_summary, sort_keys=True, separators=(",", ":")), "w1", row["node_id"], row["revision"]))
        rows = db.execute("SELECT node_id, revision, summary_json FROM evidence_graph_nodes WHERE workspace_id=? AND node_class='assumption/parameter'", ("w1",)).fetchall()
        for row in rows:
            old_summary = json.loads(row["summary_json"])
            if old_summary.get("parameter") == "frequency_severity_calibration":
                old_summary.pop("lineage_version", None)
                db.execute("UPDATE evidence_graph_nodes SET summary_json=? WHERE workspace_id=? AND node_id=? AND revision=?", (json.dumps(old_summary, sort_keys=True, separators=(",", ":")), "w1", row["node_id"], row["revision"]))
        db.execute("UPDATE evidence_graph_migrations SET migration_version='evidence-graph-v3-lineage' WHERE workspace_id='w1'")

    store.ensure_workspace("w1", fixture)
    current = store.node("w1", result_id, revision=2)
    assert current["summary"]["lineage_version"] == GRAPH_MIGRATION_VERSION
    assert store.node("w1", factor["node_id"], revision=2)["summary"]["lineage_version"] == GRAPH_MIGRATION_VERSION
    assert store.payload("w1", result_id, revision=2) == old_payload
    assert baseline == saved_baseline

    latest_edges = store.adjacency("w1", result_id, revision=2)["items"]
    assert not any(item["node_class"] == "calc/factor" for item in latest_edges)
    assert any(item["type"] == "supersedes" and item["node_id"] == result_id and item["revision"] == 1 for item in latest_edges)
    latest_history = next(item for item in latest_edges if item["node_class"] == "assumption/parameter" and item["label"] == "2023 calibration 2022")
    assert latest_history["revision"] == 2
    assert store.node("w1", latest_history["node_id"], revision=2)["summary"]["lineage_version"] == GRAPH_MIGRATION_VERSION
    assert any(item["type"] == "supersedes" and item["node_id"] == latest_history["node_id"] and item["revision"] == 1 for item in store.adjacency("w1", latest_history["node_id"], revision=2)["items"])
    old_edges = store.adjacency("w1", result_id, revision=1)["items"]
    assert {item["label"] for item in old_edges if item["node_class"] == "calc/factor"} >= {"incurred age 1", "count age 1"}
    refreshed_headline = store.summary("w1")["headline"]
    assert [(row["origin"], row["method"], row["ultimate"], row["outstanding"], row["result_node_id"]) for row in refreshed_headline] == [
        (row["origin"], row["method"], row["ultimate"], row["outstanding"], row["result_node_id"])
        for row in overview["headline"]
    ]
    with store.connect() as db:
        marker = db.execute("SELECT migration_version FROM evidence_graph_migrations WHERE workspace_id='w1'").fetchone()
    assert marker["migration_version"] == GRAPH_MIGRATION_VERSION
    store.ensure_workspace("w1", fixture)
    assert store.node("w1", result_id, revision=2)["summary"]["lineage_version"] == GRAPH_MIGRATION_VERSION
    with store.connect() as db:
        assert db.execute("SELECT COUNT(*) FROM evidence_graph_nodes WHERE workspace_id='w1' AND node_id=?", (result_id,)).fetchone()[0] == 2


def test_legacy_frequency_severity_without_saved_history_has_blocking_control(tmp_path):
    store = EvidenceGraphStore(tmp_path / "missing-history.sqlite3")
    fixture = snapshot()
    fixture["baseline"]["results"].append({
        "origin": "2023", "method": "frequency_severity", "ultimate": 1000.0,
        "paid": 165.0, "incurred": 185.0, "outstanding": 835.0,
        "additional_reserve": 815.0, "expected_count": 5.0, "severity": 200.0,
        "history_years": "2022", "prior_source": "frequency_severity", "prior": 1000.0,
    })
    store.ensure_workspace("w1", fixture)
    result = next(row for row in store.summary("w1")["headline"] if row["method"] == "frequency_severity")
    edges = store.adjacency("w1", result["result_node_id"])["items"]
    control = next(item for item in edges if item["type"] == "has_control" and item["node_class"] == "control/check")
    assert store.node("w1", control["node_id"])["reason_code"] == "legacy_lineage_unavailable"
    assert store.payload("w1", control["node_id"])["reason"] == "Stored result has calibration output but no matching saved history rows."
    assert not any(item["node_class"] == "calc/factor" for item in edges)


def test_developed_frequency_severity_traces_target_count_and_historical_calibration_inputs(tmp_path):
    store = EvidenceGraphStore(tmp_path / "annual-fs-lineage.sqlite3")
    saved = annual_session()
    store.ensure_workspace("w1", saved)
    overview = store.summary("w1")
    result = next(row for row in overview["headline"] if row["origin"] == "2025" and row["method"] == "frequency_severity")
    assert result["ultimate"] == pytest.approx(136.9047619047619)
    result_edges = store.adjacency("w1", result["result_node_id"])["items"]
    latest_count = next(item for item in result_edges if item["node_class"] == "triangle/cell" and item["metadata"].get("cell_role") == "developed_count_base")
    latest_count_payload = store.payload("w1", latest_count["node_id"])
    assert (latest_count_payload["origin"], latest_count_payload["basis"], latest_count_payload["development"], latest_count_payload["value"]) == ("2025", "count", 1, 1.0)
    assert {item["label"] for item in result_edges if item["node_class"] == "calc/factor" and item["metadata"].get("evidence_role") == "developed_count"} >= {"count age 1", "count age 2", "count age 3"}

    calibration_edges = [item for item in result_edges if item["node_class"] == "assumption/parameter" and item["label"].startswith("2025 calibration ")]
    calibrations = {str(store.payload("w1", node["node_id"])["year"]): node for node in calibration_edges}
    assert set(calibrations) == {"2023", "2024"}
    expected_by_year = {
        "2023": {"origin": "2023", "incurred": {3}, "count": {3}, "incurred_value": 250.0, "count_value": 3.0},
        "2024": {"origin": "2024", "incurred": {2, 3}, "count": {2, 3}, "incurred_value": 250.0, "count_value": 3.0},
    }
    for year, calibration in calibrations.items():
        ancestors = store.adjacency("w1", calibration["node_id"], revision=calibration["revision"])["items"]
        cells = [store.payload("w1", item["node_id"]) for item in ancestors if item["node_class"] == "triangle/cell"]
        factors = [item for item in ancestors if item["node_class"] == "calc/factor"]
        expected = expected_by_year[year]
        for basis, value_key in (("incurred", "incurred_value"), ("count", "count_value")):
            observed_basis_cells = [cell for cell in cells if cell["basis"] == basis]
            assert observed_basis_cells == [{
                "basis": basis, "origin": expected["origin"], "origin_year": int(year),
                "development": min(expected[basis]), "value": expected[value_key],
                "availability": "observed", "validation": "valid",
            }]
            ages = {int(item["label"].rsplit(" ", 1)[1]) for item in factors if item["label"].startswith(f"{basis} age")}
            assert ages == expected[basis]


def test_manual_frequency_severity_calibration_uses_parameter_nodes_not_factors(tmp_path):
    config = AnalysisConfig.model_validate({
        "frequency_severity": {
            "count_mode": "manual",
            "expected_counts": {"2025": 5.0},
            "historical_ultimates": {"2023": 250.0, "2024": 297.6190476190476},
            "historical_counts": {"2023": 3.0, "2024": 3.0},
            "rationale": "Synthetic manual calibration and target count.",
        },
    })
    store = EvidenceGraphStore(tmp_path / "manual-fs-lineage.sqlite3")
    store.ensure_workspace("w1", annual_session(config))
    overview = store.summary("w1")
    result = next(row for row in overview["headline"] if row["origin"] == "2025" and row["method"] == "frequency_severity")
    result_edges = store.adjacency("w1", result["result_node_id"])["items"]
    assert not any(item["node_class"] == "calc/factor" for item in result_edges)
    assert any(item["node_class"] == "assumption/parameter" and item["label"] == "2025 expected count" for item in result_edges)

    calibration = next(item for item in result_edges if item["node_class"] == "assumption/parameter" and item["label"] == "2025 calibration 2024")
    ancestors = store.adjacency("w1", calibration["node_id"])["items"]
    assert not any(item["node_class"] == "calc/factor" or item["node_class"] == "triangle/cell" for item in ancestors)
    assert {item["label"] for item in ancestors if item["node_class"] == "assumption/parameter"} == {
        "2024 historical ultimate", "2024 historical count",
    }


def test_incomplete_historical_source_map_blocks_frequency_severity_result(tmp_path):
    saved = annual_session()
    saved["triangle"].pop("origin_years")
    store = EvidenceGraphStore(tmp_path / "incomplete-history-lineage.sqlite3")
    store.ensure_workspace("w1", saved)
    result = next(row for row in store.summary("w1")["headline"] if row["origin"] == "2025" and row["method"] == "frequency_severity")
    edges = store.adjacency("w1", result["result_node_id"])["items"]
    blockers = [item for item in edges if item["type"] == "has_control" and item["node_class"] == "control/check"]
    assert blockers
    assert {store.node("w1", item["node_id"])["reason_code"] for item in blockers} == {"legacy_lineage_unavailable"}
    calibrations = [item for item in edges if item["node_class"] == "assumption/parameter" and "calibration" in item["label"]]
    assert calibrations
    for calibration in calibrations:
        ancestors = store.adjacency("w1", calibration["node_id"])["items"]
        assert not any(item["node_class"] in {"triangle/cell", "calc/factor"} for item in ancestors)


def test_quarterly_calibration_aggregates_all_origins_in_each_year(tmp_path):
    store = EvidenceGraphStore(tmp_path / "quarterly-fs-lineage.sqlite3")
    store.ensure_workspace("w1", quarterly_session())
    result = next(row for row in store.summary("w1")["headline"] if row["origin"] == "2025Q4" and row["method"] == "frequency_severity")
    result_edges = store.adjacency("w1", result["result_node_id"])["items"]
    calibration = next(item for item in result_edges if item["node_class"] == "assumption/parameter" and item["label"] == "2025Q4 calibration 2023")
    ancestors = store.adjacency("w1", calibration["node_id"])["items"]
    cells_by_basis = {basis: set() for basis in ("incurred", "count")}
    factor_ages_by_origin = {origin: {basis: set() for basis in ("incurred", "count")} for origin in ("2023Q1", "2023Q2", "2023Q3", "2023Q4")}
    for item in ancestors:
        metadata = item["metadata"]
        if item["node_class"] == "triangle/cell":
            payload = store.payload("w1", item["node_id"])
            if payload["basis"] in cells_by_basis:
                cells_by_basis[payload["basis"]].add(payload["origin"])
        elif item["node_class"] == "calc/factor" and metadata.get("origin") in factor_ages_by_origin:
            basis = metadata.get("component")
            if basis == "historical_ultimate":
                basis = "incurred"
            elif basis == "historical_count":
                basis = "count"
            if basis in factor_ages_by_origin[metadata["origin"]]:
                factor_ages_by_origin[metadata["origin"]][basis].add(int(item["label"].rsplit(" ", 1)[1]))

    expected_origins = {"2023Q1", "2023Q2", "2023Q3", "2023Q4"}
    assert cells_by_basis == {"incurred": expected_origins, "count": expected_origins}
    for index, origin in enumerate(("2023Q1", "2023Q2", "2023Q3", "2023Q4")):
        latest_age = 12 - index
        expected_ages = set(range(latest_age, 13))
        assert factor_ages_by_origin[origin] == {"incurred": expected_ages, "count": expected_ages}


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
