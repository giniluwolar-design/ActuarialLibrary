"""Additive, local SQLite evidence graph for saved actuarial workspace runs.

The graph stores references and small evidence payloads. Private claim blobs are
never copied into it. Node and edge revisions are immutable once written.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import sqlite3
import uuid
from pathlib import Path

_PRIVATE_CLASSES = {"artifact/private", "source/private", "claims/private", "tool/invocation"}
GRAPH_MIGRATION_VERSION = "evidence-graph-v4-frequency-severity-lineage"
_EDGE_PAIRS = {
    "derived_from": {
        ("triangle/cell", "data/source"),
        ("calc/result", "calc/factor"),
        ("calc/result", "triangle/cell"),
        ("calc/result", "assumption/config"),
        ("calc/result", "assumption/parameter"),
        ("calc/factor", "triangle/cell"),
        ("calc/factor", "assumption/config"),
        ("calc/factor", "assumption/parameter"),
        ("calc/result", "data/source"),
        ("calc/factor", "data/source"),
        ("assumption/parameter", "triangle/cell"),
        ("assumption/parameter", "calc/factor"),
        ("assumption/parameter", "assumption/parameter"),
    },
    "used_observation": {("calc/factor", "triangle/cell")},
    "excludes": {("assumption/exclusion", "triangle/cell")},
    "based_on": {("calc/result", "calc/result")},
    "has_control": {("calc/result", "control/check")},
    "produced": {("tool/invocation", "artifact/reference"), ("tool/invocation", "calc/result")},
    "cites": set(),  # narrative or judgement source may cite any typed evidence node
    "explains": {("narrative/explanation", "calc/result")},
    "supersedes": set(),  # restricted to identical node classes during validation
    "responds_to": {("tool/invocation", "transcript/turn")},
}


def _canonical(value):
    """Versioned, stable JSON encoding; rejects NaN and infinity."""
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _digest(value):
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _json(value):
    return json.loads(value) if value else None


class EvidenceGraphStore:
    """Store immutable graph revisions beside workspace tables in a SQLite file."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS evidence_graph_nodes (
                    workspace_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    node_class TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    data_version TEXT NOT NULL,
                    config_hash TEXT NOT NULL,
                    local_key TEXT NOT NULL,
                    label TEXT NOT NULL,
                    authorship TEXT NOT NULL,
                    evidential_role TEXT NOT NULL,
                    state TEXT,
                    reason_code TEXT,
                    content_sha256 TEXT NOT NULL,
                    summary_json TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    private INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (workspace_id, node_id, revision),
                    UNIQUE (workspace_id, run_id, node_class, local_key, revision)
                );
                CREATE INDEX IF NOT EXISTS evidence_graph_node_lookup
                    ON evidence_graph_nodes(workspace_id, run_id, node_class, local_key, revision);
                CREATE TABLE IF NOT EXISTS evidence_graph_edges (
                    workspace_id TEXT NOT NULL,
                    edge_id TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    edge_type TEXT NOT NULL,
                    source_node_id TEXT NOT NULL,
                    source_revision INTEGER NOT NULL,
                    target_node_id TEXT NOT NULL,
                    target_revision INTEGER NOT NULL,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (workspace_id, edge_id),
                    UNIQUE (workspace_id, run_id, edge_type, source_node_id, source_revision,
                            target_node_id, target_revision, metadata_json),
                    FOREIGN KEY (workspace_id, source_node_id, source_revision)
                        REFERENCES evidence_graph_nodes(workspace_id, node_id, revision),
                    FOREIGN KEY (workspace_id, target_node_id, target_revision)
                        REFERENCES evidence_graph_nodes(workspace_id, node_id, revision)
                );
                CREATE INDEX IF NOT EXISTS evidence_graph_edge_source
                    ON evidence_graph_edges(workspace_id, source_node_id, source_revision, edge_id);
                CREATE INDEX IF NOT EXISTS evidence_graph_edge_target
                    ON evidence_graph_edges(workspace_id, target_node_id, target_revision, edge_id);
                CREATE TABLE IF NOT EXISTS evidence_graph_legacy_t (
                    workspace_id TEXT NOT NULL,
                    legacy_id TEXT NOT NULL,
                    node_id TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 1,
                    PRIMARY KEY (workspace_id, legacy_id),
                    FOREIGN KEY (workspace_id, node_id, revision)
                        REFERENCES evidence_graph_nodes(workspace_id, node_id, revision)
                );
                CREATE TABLE IF NOT EXISTS evidence_graph_migrations (
                    workspace_id TEXT PRIMARY KEY,
                    migration_version TEXT NOT NULL,
                    snapshot_hash TEXT NOT NULL
                );
                """
            )

    def connect(self):
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys = ON")
        return db

    def _new_node(self, db, workspace_id, node):
        node_class = node.get("node_class", node.get("class"))
        if not node_class:
            raise ValueError("node_class is required")
        run_id = str(node.get("run_id", "baseline"))
        local_key = str(node.get("local_key", node.get("label", node_class)))
        label = str(node.get("label", local_key))
        payload = node.get("payload", {})
        if not isinstance(payload, dict):
            raise TypeError("Node payload must be an object")
        content_sha256 = node.get("content_sha256") or _digest(payload)
        data_version = str(node.get("data_version", "unknown"))
        config_hash = str(node.get("config_hash", "unknown"))
        evidential_role = str(node.get("evidential_role", "calculation_evidence"))
        authorship = node.get(
            "authorship", {"actor": "unknown", "role": "migration", "action": "legacy_backfill", "created_at": "unknown"}
        )
        if not isinstance(authorship, dict) or authorship.get("role") not in {"analyst", "tool", "model", "migration"}:
            raise ValueError("authorship.role must be analyst, tool, model, or migration")
        if evidential_role not in {"calculation_evidence", "human_judgement", "model_explanation", "import_provenance", "execution_record"}:
            raise ValueError("Unknown evidential_role")
        if node_class == "tool/invocation" and evidential_role != "execution_record":
            raise ValueError("tool/invocation nodes must be execution records")
        if node_class == "judgement/selection" and (authorship.get("role") != "analyst" or not authorship.get("action")):
            raise ValueError("Selections require an analyst authorship action id")
        state = node.get("state")
        reason_code = node.get("reason_code")
        private = bool(node.get("private", node_class in _PRIVATE_CLASSES))
        summary = node.get("summary", {})
        supplied_identity = node.get("node_id")
        identity = supplied_identity or str(uuid.uuid4())
        existing = db.execute(
            "SELECT * FROM evidence_graph_nodes "
            "WHERE workspace_id=? AND run_id=? AND node_class=? AND local_key=? "
            "ORDER BY revision DESC LIMIT 1",
            (workspace_id, run_id, node_class, local_key),
        ).fetchone()
        unchanged = bool(
            existing
            and existing["content_sha256"] == content_sha256
            and existing["data_version"] == data_version
            and existing["config_hash"] == config_hash
            and existing["label"] == label
            and existing["authorship"] == _canonical(authorship)
            and existing["evidential_role"] == evidential_role
            and existing["state"] == state
            and existing["reason_code"] == reason_code
            and existing["summary_json"] == _canonical(summary)
            and existing["payload_json"] == _canonical(payload)
            and bool(existing["private"]) == private
            and (supplied_identity is None or existing["node_id"] == identity)
        )
        if unchanged:
            return self._node_record(
                db.execute(
                    "SELECT * FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?",
                    (workspace_id, existing["node_id"], existing["revision"]),
                ).fetchone()
            )
        if existing:
            identity = existing["node_id"]
            revision = existing["revision"] + 1
        else:
            revision = int(node.get("revision", 1))
        db.execute(
            """INSERT INTO evidence_graph_nodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                workspace_id,
                identity,
                revision,
                node_class,
                run_id,
                data_version,
                config_hash,
                local_key,
                label,
                _canonical(authorship),
                evidential_role,
                state,
                reason_code,
                content_sha256,
                _canonical(summary),
                _canonical(payload),
                int(private),
            ),
        )
        return self._node_record(
            db.execute(
                "SELECT * FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?",
                (workspace_id, identity, revision),
            ).fetchone()
        )

    @staticmethod
    def _node_record(row):
        return {
            "workspace_id": row["workspace_id"],
            "node_id": row["node_id"],
            "revision": row["revision"],
            "node_class": row["node_class"],
            "run_id": row["run_id"],
            "data_version": row["data_version"],
            "config_hash": row["config_hash"],
            "local_key": row["local_key"],
            "label": row["label"],
            "authorship": _json(row["authorship"]),
            "evidential_role": row["evidential_role"],
            "state": row["state"],
            "reason_code": row["reason_code"],
            "content_sha256": row["content_sha256"],
            "summary": _json(row["summary_json"]),
            "private": bool(row["private"]),
        }

    def write_node(self, workspace_id, node):
        """Write an immutable node revision; a changed payload creates revision + 1."""
        with self.connect() as db:
            return self._new_node(db, workspace_id, node)

    def _write_edge(self, db, workspace_id, edge, run_id=None):
        edge_type = edge.get("type", edge.get("edge_type"))
        if edge_type not in _EDGE_PAIRS:
            raise ValueError(f"Unknown edge type: {edge_type}")
        source_id = edge.get("source_node_id")
        target_id = edge.get("target_node_id")
        source_revision = int(edge.get("source_revision", 1))
        target_revision = int(edge.get("target_revision", 1))
        source = db.execute(
            "SELECT node_class FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?",
            (workspace_id, source_id, source_revision),
        ).fetchone()
        target = db.execute(
            "SELECT node_class FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?",
            (workspace_id, target_id, target_revision),
        ).fetchone()
        if source is None or target is None:
            raise ValueError("Both edge endpoint revisions must exist in this workspace")
        pair = (source["node_class"], target["node_class"])
        permitted = pair in _EDGE_PAIRS[edge_type]
        if edge_type == "cites":
            permitted = source["node_class"] in {"narrative/explanation", "judgement/selection"}
        elif edge_type == "supersedes":
            permitted = source["node_class"] == target["node_class"]
        if not permitted:
            raise ValueError(f"Invalid {edge_type} endpoint classes: {pair}")
        if edge_type == "explains" and pair != ("narrative/explanation", "calc/result"):
            raise ValueError("Explains edges must point from an explanation to a result")
        if edge_type == "cites" and source["node_class"].startswith("calc/"):
            raise ValueError("Calculation nodes cannot cite as narrative")
        metadata = edge.get("metadata", {})
        metadata_json = _canonical(metadata)
        if len(metadata_json.encode("utf-8")) > 4096:
            raise ValueError("Edge metadata exceeds the 4 KB graph limit")
        edge_id = edge.get("edge_id") or str(uuid.uuid4())
        selected_run = str(run_id if run_id is not None else edge.get("run_id", "baseline"))
        existing = db.execute(
            """SELECT edge_id FROM evidence_graph_edges WHERE workspace_id=? AND run_id=? AND edge_type=?
               AND source_node_id=? AND source_revision=? AND target_node_id=? AND target_revision=?
               AND metadata_json=?""",
            (workspace_id, selected_run, edge_type, source_id, source_revision, target_id, target_revision, metadata_json),
        ).fetchone()
        if existing:
            edge_id = existing["edge_id"]
        else:
            db.execute(
                "INSERT INTO evidence_graph_edges VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (workspace_id, edge_id, selected_run, edge_type, source_id, source_revision, target_id, target_revision, metadata_json),
            )
        return {
            "workspace_id": workspace_id,
            "edge_id": edge_id,
            "run_id": selected_run,
            "type": edge_type,
            "source_node_id": source_id,
            "source_revision": source_revision,
            "target_node_id": target_id,
            "target_revision": target_revision,
            "metadata": metadata,
        }

    def write_edge(self, workspace_id, edge):
        """Write an edge after validating its type and both pinned endpoint revisions."""
        with self.connect() as db:
            return self._write_edge(db, workspace_id, edge)

    @staticmethod
    def _result_dict(result):
        return result if isinstance(result, dict) else {}

    def ensure_workspace(self, workspace_id, snapshot):
        """Atomically backfill saved baseline/scenario evidence, preserving prior revisions."""
        if not isinstance(snapshot, dict) or "baseline" not in snapshot or "triangle" not in snapshot:
            raise ValueError("Expected an encode_session snapshot with triangle and baseline")
        triangle = snapshot["triangle"]
        triangle_fingerprint = {key: value for key, value in triangle.items() if key != "claims"}
        data_version = _digest(triangle_fingerprint)
        config = snapshot.get("config", {})
        config_hash = _digest(config)
        artifact_fingerprints = {}
        for key, artifact in snapshot.get("artifacts", {}).items():
            content = artifact.get("content", "")
            try:
                artifact_hash = hashlib.sha256(base64.b64decode(content, validate=True)).hexdigest()
            except (ValueError, TypeError):
                artifact_hash = "unknown"
            artifact_fingerprints[str(key)] = {"metadata": {field: value for field, value in artifact.items() if field != "content"}, "content_sha256": artifact_hash}
        snapshot_hash = _digest({
            "triangle": triangle_fingerprint,
            "config": config,
            "baseline": snapshot.get("baseline"),
            "scenarios": snapshot.get("scenarios", {}),
            "evidence": snapshot.get("evidence", []),
            "artifacts": artifact_fingerprints,
        })
        with self.connect() as db:
            db.execute("BEGIN IMMEDIATE")
            marker = db.execute("SELECT migration_version, snapshot_hash FROM evidence_graph_migrations WHERE workspace_id=?", (workspace_id,)).fetchone()
            if marker and marker["migration_version"] == GRAPH_MIGRATION_VERSION and marker["snapshot_hash"] == snapshot_hash:
                return
            built = {}
            source = self._new_node(
                db,
                workspace_id,
                {
                    "node_class": "data/source",
                    "run_id": "baseline",
                    "data_version": data_version,
                    "config_hash": config_hash,
                    "local_key": "triangle-source",
                    "label": "Triangle source",
                    "evidential_role": "calculation_evidence",
                    "payload": {"metadata": triangle.get("metadata", {}), "valuation": triangle.get("valuation"), "grain": triangle.get("grain"), "origins": triangle.get("origins", [])},
                    "summary": {"availability": "observed", "kind": "aggregate_triangle"},
                },
            )
            built[("baseline", "source")] = source
            cells = {}
            origins = triangle.get("origins", [])
            states = triangle.get("states", [])
            for basis in ("paid", "incurred", "count"):
                matrix = triangle.get(basis, [])
                for i, origin in enumerate(origins):
                    for j in range(len(matrix[i]) if i < len(matrix) else 0):
                        availability = states[i][j] if i < len(states) and j < len(states[i]) else "missing"
                        value = matrix[i][j]
                        cell_key = f"{basis}:{origin}:{j + 1}"
                        cell = self._new_node(
                            db,
                            workspace_id,
                            {
                                "node_class": "triangle/cell",
                                "run_id": "baseline",
                                "data_version": data_version,
                                "config_hash": config_hash,
                                "local_key": cell_key,
                                "label": f"{basis} {origin} age {j + 1}",
                                "evidential_role": "calculation_evidence",
                                "state": availability,
                                "reason_code": "not_yet_observed" if availability == "future" else "coverage_missing" if availability == "missing" else None,
                                "payload": {"basis": basis, "origin": origin, "origin_year": triangle.get("origin_years", [None] * len(origins))[i], "development": j + 1, "value": value, "availability": availability, "validation": "valid" if availability == "observed" else "unavailable-blocked"},
                                "summary": {"availability": availability, "validation": "valid" if availability == "observed" else "unavailable-blocked", "basis": basis, "origin": origin, "development": j + 1},
                            },
                        )
                        cells[(basis, origin, j + 1)] = cell
                        self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": cell["node_id"], "source_revision": cell["revision"], "target_node_id": source["node_id"], "target_revision": source["revision"]}, "baseline")

            assumption = self._new_node(
                db,
                workspace_id,
                {"node_class": "assumption/config", "run_id": "baseline", "data_version": data_version, "config_hash": config_hash, "local_key": "analysis-config", "label": "Analysis configuration", "evidential_role": "calculation_evidence", "payload": config, "summary": {"availability": "observed", "validation": "valid"}},
            )
            built[("baseline", "config")] = assumption
            runs = [("baseline", self._result_dict(snapshot.get("baseline")))]
            runs.extend((str(run_id), self._result_dict(result)) for run_id, result in snapshot.get("scenarios", {}).items())
            for run_id, result in runs:
                run_config = result.get("config", config)
                run_config_hash = _digest(run_config)
                if run_id != "baseline":
                    run_assumption = self._new_node(db, workspace_id, {"node_class": "assumption/config", "run_id": run_id, "data_version": data_version, "config_hash": run_config_hash, "local_key": "analysis-config", "label": f"{run_id} configuration", "evidential_role": "calculation_evidence", "payload": run_config, "summary": {"availability": "observed", "validation": "valid"}})
                    built[(run_id, "config")] = run_assumption
                else:
                    run_assumption = assumption
                exclusions = []
                for basis in ("paid", "incurred", "count"):
                    basis_config = run_config.get(basis, {})
                    if not isinstance(basis_config, dict):
                        continue
                    for excluded_origin, excluded_age in basis_config.get("excluded", []):
                        exclusion_key = f"{basis}:{excluded_origin}:{excluded_age}"
                        exclusion = self._new_node(db, workspace_id, {
                            "node_class": "assumption/exclusion",
                            "run_id": run_id,
                            "data_version": data_version,
                            "config_hash": run_config_hash,
                            "local_key": exclusion_key,
                            "label": f"Exclude {basis} {excluded_origin} age {excluded_age}",
                            "evidential_role": "import_provenance",
                            "payload": {"basis": basis, "origin": excluded_origin, "development": excluded_age, "rationale": basis_config.get("rationale", "")},
                            "summary": {"availability": "observed", "validation": "valid"},
                        })
                        exclusions.append((basis, excluded_origin, excluded_age, exclusion))
                        excluded_cell = cells.get((basis, excluded_origin, excluded_age))
                        if excluded_cell:
                            self._write_edge(db, workspace_id, {"type": "excludes", "source_node_id": exclusion["node_id"], "source_revision": exclusion["revision"], "target_node_id": excluded_cell["node_id"], "target_revision": excluded_cell["revision"], "metadata": {"scenario_run_id": run_id, "cell_role": "denominator"}}, run_id)
                            numerator_cell = cells.get((basis, excluded_origin, excluded_age + 1))
                            if numerator_cell and numerator_cell["state"] == "observed":
                                self._write_edge(db, workspace_id, {"type": "excludes", "source_node_id": exclusion["node_id"], "source_revision": exclusion["revision"], "target_node_id": numerator_cell["node_id"], "target_revision": numerator_cell["revision"], "metadata": {"scenario_run_id": run_id, "cell_role": "numerator"}}, run_id)
                result_nodes = {}
                factor_nodes = {}
                factor_rows = result.get("factors", [])
                for factor_row in factor_rows:
                    basis = factor_row.get("basis")
                    age = factor_row.get("development")
                    factor_key = f"{basis}:{age}"
                    factor = self._new_node(
                        db,
                        workspace_id,
                        {"node_class": "calc/factor", "run_id": run_id, "data_version": data_version, "config_hash": run_config_hash, "local_key": factor_key, "label": f"{basis} age {age}", "evidential_role": "calculation_evidence", "state": "observed" if factor_row.get("selected") is not None else "missing", "reason_code": None if factor_row.get("selected") is not None else "factor_unavailable", "payload": factor_row, "summary": {"availability": "observed" if factor_row.get("selected") is not None else "missing", "validation": "valid" if factor_row.get("selected") is not None else "unavailable-blocked", "basis": basis, "development": age, "lineage_version": GRAPH_MIGRATION_VERSION}},
                    )
                    self._supersede_previous(db, workspace_id, factor, run_id)
                    factor_nodes[factor_key] = factor
                    self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": factor["node_id"], "source_revision": factor["revision"], "target_node_id": run_assumption["node_id"], "target_revision": run_assumption["revision"]}, run_id)
                    origins_used = {x.strip() for x in (factor_row.get("origins_used") or "").split(",") if x.strip()}
                    for origin in origins:
                        cell = cells.get((basis, origin, age))
                        if cell is None:
                            continue
                        next_cell = cells.get((basis, origin, age + 1))
                        cell_data = self._payload_for(db, workspace_id, cell)
                        next_data = self._payload_for(db, workspace_id, next_cell) if next_cell else None
                        valid_pair = (
                            cell["state"] == "observed"
                            and next_data is not None
                            and next_data.get("availability") == "observed"
                            and cell_data.get("value") is not None
                            and cell_data["value"] > 0
                        )
                        if origin in origins_used:
                            membership = "included"
                        elif (origin, age) in {
                            (item[0], item[1])
                            for item in (run_config.get(basis, {}).get("excluded", []) if isinstance(run_config.get(basis, {}), dict) else [])
                            if len(item) == 2
                        }:
                            membership = "excluded"
                        elif valid_pair:
                            membership = "outside-window"
                        else:
                            continue
                        if not valid_pair:
                            continue
                        common_metadata = {"fitting_membership": membership, "scenario_run_id": run_id}
                        for cell_role, endpoint in (("denominator", cell), ("numerator", next_cell)):
                            self._write_edge(db, workspace_id, {"type": "used_observation", "source_node_id": factor["node_id"], "source_revision": factor["revision"], "target_node_id": endpoint["node_id"], "target_revision": endpoint["revision"], "metadata": {**common_metadata, "cell_role": cell_role}}, run_id)

                history_nodes = {}
                for history_row in result.get("history", []):
                    target_origin = str(history_row.get("target", "unknown"))
                    year = str(history_row.get("year", "unknown"))
                    history_key = f"frequency-severity-history:{target_origin}:{year}"
                    history_node = self._new_node(db, workspace_id, {
                        "node_class": "assumption/parameter",
                        "run_id": run_id,
                        "data_version": data_version,
                        "config_hash": run_config_hash,
                        "local_key": history_key,
                        "label": f"{target_origin} calibration {year}",
                        "evidential_role": "calculation_evidence",
                        "state": "observed",
                        "payload": history_row,
                        "summary": {"availability": "observed", "validation": "valid", "parameter": "frequency_severity_calibration", "target": target_origin, "year": year, "lineage_version": GRAPH_MIGRATION_VERSION},
                    })
                    self._supersede_previous(db, workspace_id, history_node, run_id)
                    history_nodes[(target_origin, year)] = history_node

                fs_config = run_config.get("frequency_severity", {})
                if not isinstance(fs_config, dict):
                    fs_config = {}
                origin_years = triangle.get("origin_years", [])
                history_lineage_controls = {}
                for (target_origin, year), history_node in history_nodes.items():
                    source_origins = [
                        origin for index, origin in enumerate(origins)
                        if index < len(origin_years) and str(origin_years[index]) == year
                    ]
                    missing_components = []
                    for component, basis, config_key in (
                        ("historical_ultimate", "incurred", "historical_ultimates"),
                        ("historical_count", "count", "historical_counts"),
                    ):
                        overrides = fs_config.get(config_key, {})
                        if not isinstance(overrides, dict):
                            overrides = {}
                        if not source_origins:
                            missing_components.append(component)
                            continue
                        for source_origin in source_origins:
                            if source_origin in overrides:
                                parameter_node = self._new_node(db, workspace_id, {
                                    "node_class": "assumption/parameter", "run_id": run_id, "data_version": data_version,
                                    "config_hash": run_config_hash, "local_key": f"frequency-severity:{component}:{source_origin}",
                                    "label": f"{source_origin} {component.replace('_', ' ')}", "evidential_role": "calculation_evidence",
                                    "state": "observed", "payload": {"parameter": component, "origin": source_origin, "year": year, "value": overrides[source_origin], "source": "frequency_severity_config"},
                                    "summary": {"availability": "observed", "validation": "valid", "parameter": component, "origin": source_origin},
                                })
                                self._write_edge(db, workspace_id, {
                                    "type": "derived_from", "source_node_id": history_node["node_id"], "source_revision": history_node["revision"],
                                    "target_node_id": parameter_node["node_id"], "target_revision": parameter_node["revision"],
                                    "metadata": {"component": component, "origin": source_origin, "year": year, "source": "manual_override"},
                                }, run_id)
                                continue

                            source_index = origins.index(source_origin)
                            latest_age = len(origins) - source_index
                            latest_cell = cells.get((basis, source_origin, latest_age))
                            if latest_cell is None or latest_cell["state"] != "observed":
                                missing_components.append(f"{component}:{source_origin}:latest_cell")
                                continue
                            self._write_edge(db, workspace_id, {
                                "type": "derived_from", "source_node_id": history_node["node_id"], "source_revision": history_node["revision"],
                                "target_node_id": latest_cell["node_id"], "target_revision": latest_cell["revision"],
                                "metadata": {"component": component, "origin": source_origin, "year": year, "cell_role": "latest_incurred" if basis == "incurred" else "latest_count"},
                            }, run_id)
                            expected_ages = set(range(latest_age, len(origins) + 1))
                            linked_ages = set()
                            for factor_key, factor in factor_nodes.items():
                                factor_basis, factor_age = factor_key.rsplit(":", 1)
                                age = int(factor_age)
                                if factor_basis == basis and age in expected_ages:
                                    self._write_edge(db, workspace_id, {
                                        "type": "derived_from", "source_node_id": history_node["node_id"], "source_revision": history_node["revision"],
                                        "target_node_id": factor["node_id"], "target_revision": factor["revision"],
                                        "metadata": {"component": component, "origin": source_origin, "year": year, "evidence_role": "historical_development_factor"},
                                    }, run_id)
                                    linked_ages.add(age)
                            if linked_ages != expected_ages:
                                missing_components.append(f"{component}:{source_origin}:factors")
                    if missing_components:
                        blocker = self._new_node(db, workspace_id, {
                            "node_class": "control/check", "run_id": run_id, "data_version": data_version,
                            "config_hash": run_config_hash, "local_key": f"history:{target_origin}:{year}:lineage-unknown",
                            "label": f"{target_origin} calibration {year} source lineage unavailable", "evidential_role": "calculation_evidence",
                            "state": "missing", "reason_code": "legacy_lineage_unavailable",
                            "payload": {"target": target_origin, "year": year, "missing_components": missing_components},
                            "summary": {"availability": "missing", "validation": "unavailable-blocked", "reason_code": "legacy_lineage_unavailable"},
                        })
                        history_lineage_controls.setdefault(target_origin, []).append(blocker)

                for row in result.get("results", []):
                    origin, method = str(row.get("origin", "unknown")), str(row.get("method", "unknown"))
                    key = f"{origin}:{method}"
                    state = "observed" if row.get("ultimate") is not None else "missing"
                    reason_code = None if state == "observed" else self._reason_code(row.get("reason"))
                    result_node = self._new_node(
                        db,
                        workspace_id,
                        {"node_class": "calc/result", "run_id": run_id, "data_version": data_version, "config_hash": run_config_hash, "local_key": key, "label": f"{origin} {method}", "evidential_role": "calculation_evidence", "state": state, "reason_code": reason_code, "payload": row, "summary": {"origin": origin, "method": method, "ultimate": row.get("ultimate"), "outstanding": row.get("outstanding"), "availability": state, "validation": "valid" if state == "observed" else "unavailable-blocked", "reason_code": reason_code, "lineage_version": GRAPH_MIGRATION_VERSION}},
                    )
                    self._supersede_previous(db, workspace_id, result_node, run_id)
                    result_nodes[key] = result_node
                    self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": run_assumption["node_id"], "target_revision": run_assumption["revision"]}, run_id)
                    applicable = {method.split("_", 1)[0]} if method.startswith(("paid_", "incurred_")) else set()
                    origin_index = origins.index(origin) if origin in origins else len(origins)
                    latest_age = len(origins) - origin_index
                    for basis, row_field, role in (("paid", "paid", "latest_paid"), ("incurred", "incurred", "latest_incurred")):
                        latest_cell = cells.get((basis, origin, latest_age))
                        if row.get(row_field) is not None and latest_cell is not None:
                            self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": latest_cell["node_id"], "target_revision": latest_cell["revision"], "metadata": {"cell_role": role, "scenario_run_id": run_id}}, run_id)
                    for factor_key, factor in factor_nodes.items():
                        factor_basis, factor_age = factor_key.rsplit(":", 1)
                        age_is_applicable = int(factor_age) >= latest_age
                        if factor_basis in applicable and age_is_applicable:
                            self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": factor["node_id"], "target_revision": factor["revision"]}, run_id)
                    if method == "frequency_severity":
                        target_years = {year.strip() for year in str(row.get("history_years", "")).split(",") if year.strip()}
                        linked_history = 0
                        for (target_origin, year), history_node in history_nodes.items():
                            if target_origin == origin and year in target_years:
                                self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": history_node["node_id"], "target_revision": history_node["revision"]}, run_id)
                                linked_history += 1
                        for blocker in history_lineage_controls.get(origin, []):
                            self._write_edge(db, workspace_id, {
                                "type": "has_control", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"],
                                "target_node_id": blocker["node_id"], "target_revision": blocker["revision"],
                            }, run_id)
                        fs_config = run_config.get("frequency_severity", {})
                        count_mode = fs_config.get("count_mode", "developed") if isinstance(fs_config, dict) else "unknown"
                        if count_mode == "developed":
                            latest_count = cells.get(("count", origin, latest_age))
                            if latest_count and row.get("expected_count") is not None:
                                self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": latest_count["node_id"], "target_revision": latest_count["revision"], "metadata": {"cell_role": "developed_count_base", "scenario_run_id": run_id}}, run_id)
                            for factor_key, factor in factor_nodes.items():
                                factor_basis, factor_age = factor_key.rsplit(":", 1)
                                if factor_basis == "count" and int(factor_age) >= latest_age:
                                    self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": factor["node_id"], "target_revision": factor["revision"], "metadata": {"evidence_role": "developed_count"}}, run_id)
                        elif count_mode == "reported":
                            latest_count = cells.get(("count", origin, latest_age))
                            if latest_count and row.get("expected_count") is not None:
                                self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": latest_count["node_id"], "target_revision": latest_count["revision"], "metadata": {"cell_role": "reported_count", "scenario_run_id": run_id}}, run_id)
                        elif count_mode in {"manual", "exposure"}:
                            count_values = fs_config.get("expected_counts", {}) if count_mode == "manual" else {"exposure": fs_config.get("exposures", {}).get(origin), "frequency": fs_config.get("frequencies", {}).get(origin)}
                            if count_mode == "manual":
                                count_values = {"expected_count": count_values.get(origin)}
                            for parameter, value in count_values.items():
                                if value is None:
                                    continue
                                parameter_node = self._new_node(db, workspace_id, {
                                    "node_class": "assumption/parameter", "run_id": run_id, "data_version": data_version,
                                    "config_hash": run_config_hash, "local_key": f"frequency-severity:{origin}:{parameter}",
                                    "label": f"{origin} {parameter.replace('_', ' ')}", "evidential_role": "calculation_evidence",
                                    "state": "observed", "payload": {"parameter": parameter, "origin": origin, "value": value, "count_mode": count_mode},
                                    "summary": {"availability": "observed", "validation": "valid", "parameter": parameter, "origin": origin},
                                })
                                self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": parameter_node["node_id"], "target_revision": parameter_node["revision"]}, run_id)
                        if row.get("severity") is not None and not linked_history:
                            unknown = self._new_node(db, workspace_id, {
                                "node_class": "control/check", "run_id": run_id, "data_version": data_version,
                                "config_hash": run_config_hash, "local_key": f"result:{key}:history-lineage-unknown",
                                "label": f"{origin} calibration lineage unavailable", "evidential_role": "calculation_evidence",
                                "state": "missing", "reason_code": "legacy_lineage_unavailable",
                                "payload": {"result_key": key, "reason": "Stored result has calibration output but no matching saved history rows."},
                                "summary": {"availability": "missing", "validation": "unavailable-blocked", "reason_code": "legacy_lineage_unavailable"},
                            })
                            self._write_edge(db, workspace_id, {"type": "has_control", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": unknown["node_id"], "target_revision": unknown["revision"]}, run_id)
                    elif method in {"paid_bf", "incurred_bf"} and row.get("prior_source") == "manual" and row.get("prior") is not None:
                        prior_node = self._new_node(db, workspace_id, {
                            "node_class": "assumption/parameter", "run_id": run_id, "data_version": data_version,
                            "config_hash": run_config_hash, "local_key": f"manual-prior:{origin}",
                            "label": f"{origin} manual expected ultimate prior", "evidential_role": "calculation_evidence",
                            "state": "observed", "payload": {"parameter": "expected_ultimate_prior", "origin": origin, "value": row.get("prior"), "source": "manual"},
                            "summary": {"availability": "observed", "validation": "valid", "parameter": "expected_ultimate_prior", "origin": origin},
                        })
                        self._write_edge(db, workspace_id, {"type": "derived_from", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": prior_node["node_id"], "target_revision": prior_node["revision"]}, run_id)
                    reason = row.get("reason")
                    if reason:
                        control_key = f"result:{key}:unavailable"
                        control = self._new_node(db, workspace_id, {"node_class": "control/check", "run_id": run_id, "data_version": data_version, "config_hash": run_config_hash, "local_key": control_key, "label": f"{origin} {method} availability", "evidential_role": "calculation_evidence", "state": "missing" if state == "missing" else "observed", "reason_code": reason_code or "warning", "payload": {"message": reason, "result_key": key}, "summary": {"availability": "missing" if state == "missing" else "observed", "validation": "unavailable-blocked" if state == "missing" else "valid", "reason_code": reason_code or "warning"}})
                        self._write_edge(db, workspace_id, {"type": "has_control", "source_node_id": result_node["node_id"], "source_revision": result_node["revision"], "target_node_id": control["node_id"], "target_revision": control["revision"]}, run_id)

                for row in result.get("results", []):
                    if row.get("method") in {"paid_bf", "incurred_bf"} and row.get("prior_source") == "frequency_severity":
                        fs_result = result_nodes.get(f"{row.get('origin', 'unknown')}:frequency_severity")
                        bf_result = result_nodes.get(f"{row.get('origin', 'unknown')}:{row.get('method')}")
                        if fs_result and bf_result:
                            self._write_edge(db, workspace_id, {"type": "based_on", "source_node_id": bf_result["node_id"], "source_revision": bf_result["revision"], "target_node_id": fs_result["node_id"], "target_revision": fs_result["revision"], "metadata": {"evidence_role": "expected_ultimate_prior"}}, run_id)

                for index, warning in enumerate(result.get("warnings", [])):
                    control = self._new_node(db, workspace_id, {"node_class": "control/check", "run_id": run_id, "data_version": data_version, "config_hash": run_config_hash, "local_key": f"warning:{index}", "label": str(warning)[:160], "evidential_role": "calculation_evidence", "state": "observed", "reason_code": "warning", "payload": {"message": warning}, "summary": {"availability": "observed", "validation": "valid", "reason_code": "warning"}})
                if run_id != "baseline":
                    base = db.execute("SELECT node_id, MAX(revision) AS revision, local_key FROM evidence_graph_nodes WHERE workspace_id=? AND run_id='baseline' AND node_class='calc/result' GROUP BY local_key ORDER BY local_key", (workspace_id,)).fetchall()
                    for baseline_node in base:
                        current = result_nodes.get(baseline_node["local_key"])
                        if current:
                            self._write_edge(db, workspace_id, {"type": "based_on", "source_node_id": current["node_id"], "source_revision": current["revision"], "target_node_id": baseline_node["node_id"], "target_revision": baseline_node["revision"]}, run_id)

            for record in snapshot.get("evidence", []):
                legacy_id = str(record.get("id", ""))
                if not legacy_id.startswith("T") or not legacy_id[1:].isdigit():
                    continue
                invocation = self._new_node(db, workspace_id, {"node_class": "tool/invocation", "run_id": "baseline", "data_version": data_version, "config_hash": config_hash, "local_key": f"legacy:{legacy_id}", "label": legacy_id, "evidential_role": "execution_record", "authorship": {"actor": "unknown", "role": "migration", "action": "legacy_backfill", "created_at": "unknown"}, "payload": record, "summary": {"availability": "observed", "validation": "valid", "legacy_id": legacy_id}})
                db.execute("INSERT OR IGNORE INTO evidence_graph_legacy_t (workspace_id, legacy_id, node_id, revision) VALUES (?, ?, ?, ?)", (workspace_id, legacy_id, invocation["node_id"], invocation["revision"]))
            for key, artifact in snapshot.get("artifacts", {}).items():
                # Keep only a reference and non-sensitive manifest fields; never store decoded blob bytes.
                content = artifact.get("content", "")
                try:
                    digest = hashlib.sha256(base64.b64decode(content, validate=True)).hexdigest()
                except (ValueError, TypeError):
                    digest = "unknown"
                self._new_node(db, workspace_id, {"node_class": "artifact/private", "run_id": "baseline", "data_version": data_version, "config_hash": config_hash, "local_key": str(key), "label": "Private artifact", "evidential_role": "import_provenance", "private": True, "payload": {"content_sha256": digest, "blob_included": False}, "summary": {"availability": "observed", "validation": "valid", "private": True}})
            db.execute(
                "INSERT INTO evidence_graph_migrations VALUES (?, ?, ?) "
                "ON CONFLICT(workspace_id) DO UPDATE SET migration_version=excluded.migration_version, snapshot_hash=excluded.snapshot_hash",
                (workspace_id, GRAPH_MIGRATION_VERSION, snapshot_hash),
            )

    def _supersede_previous(self, db, workspace_id, node, run_id):
        if node["revision"] <= 1:
            return
        self._write_edge(db, workspace_id, {
            "type": "supersedes",
            "source_node_id": node["node_id"],
            "source_revision": node["revision"],
            "target_node_id": node["node_id"],
            "target_revision": node["revision"] - 1,
            "metadata": {"migration_version": GRAPH_MIGRATION_VERSION},
        }, run_id)

    @staticmethod
    def _reason_code(reason):
        if not reason:
            return "unavailable"
        lowered = str(reason).lower()
        if "missing" in lowered or "unavailable" in lowered:
            return "required_input_unavailable"
        if "factor" in lowered or "development" in lowered:
            return "factor_unavailable"
        return "calculation_blocked"

    @staticmethod
    def _payload_for(db, workspace_id, node):
        if node is None:
            return None
        row = db.execute("SELECT payload_json FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?", (workspace_id, node["node_id"], node["revision"])).fetchone()
        return _json(row["payload_json"]) if row else None

    def legacy_node_id(self, workspace_id, legacy_id):
        with self.connect() as db:
            row = db.execute("SELECT node_id FROM evidence_graph_legacy_t WHERE workspace_id=? AND legacy_id=?", (workspace_id, legacy_id)).fetchone()
        if row is None:
            raise KeyError((workspace_id, legacy_id))
        return row["node_id"]

    def node(self, workspace_id, node_id, revision=1):
        with self.connect() as db:
            row = db.execute("SELECT * FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?", (workspace_id, node_id, revision)).fetchone()
        if row is None:
            raise KeyError((node_id, revision))
        return self._node_record(row)

    @staticmethod
    def _node_stub(row):
        summary = _json(row["summary_json"])
        label = row["label"]
        if len(label) > 96:
            label = label[:93] + "..."
        return {"node_id": row["node_id"], "revision": row["revision"], "node_class": row["node_class"], "run_id": row["run_id"], "label": label, "evidential_role": row["evidential_role"], "state": row["state"] or summary.get("availability"), "reason_code": row["reason_code"] or summary.get("reason_code"), "content_sha256": row["content_sha256"]}

    def payload(self, workspace_id, node_id, revision=1):
        with self.connect() as db:
            row = db.execute("SELECT payload_json FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?", (workspace_id, node_id, revision)).fetchone()
        if row is None:
            raise KeyError((node_id, revision))
        return _json(row["payload_json"])

    def summary(self, workspace_id, run_id="baseline", node_limit=50, node_cursor=None):
        if not isinstance(node_limit, int) or isinstance(node_limit, bool) or not 1 <= node_limit <= 200:
            raise ValueError("node_limit must be an integer from 1 through 200")
        with self.connect() as db:
            rows = db.execute("SELECT * FROM evidence_graph_nodes WHERE workspace_id=? AND run_id=? ORDER BY node_class, local_key, revision", (workspace_id, run_id)).fetchall()
            scenario_rows = db.execute("SELECT DISTINCT run_id FROM evidence_graph_nodes WHERE workspace_id=? AND run_id!='baseline' ORDER BY run_id", (workspace_id,)).fetchall()
        latest = {}
        for row in rows:
            latest[(row["node_class"], row["local_key"])] = row
        factor_rows = sorted(
            (row for row in latest.values() if row["node_class"] == "calc/factor"),
            key=lambda row: row["node_id"],
        )
        factor_snapshot = _digest([[row["node_id"], row["revision"]] for row in factor_rows])
        after_node_id = ""
        if node_cursor:
            try:
                decoded = json.loads(base64.urlsafe_b64decode(node_cursor.encode() + b"=" * (-len(node_cursor) % 4)))
            except (ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise ValueError("Malformed summary cursor") from exc
            if (
                not isinstance(decoded, dict)
                or decoded.get("workspace_id") != workspace_id
                or decoded.get("run_id") != run_id
                or decoded.get("snapshot") != factor_snapshot
                or not isinstance(decoded.get("last_node_id"), str)
            ):
                raise ValueError("Summary cursor is incompatible with this pinned snapshot")
            after_node_id = decoded["last_node_id"]
        remaining_factors = [row for row in factor_rows if row["node_id"] > after_node_id]
        factor_page = remaining_factors[:node_limit]
        has_more_nodes = len(remaining_factors) > len(factor_page)
        next_node_cursor = None
        if has_more_nodes and factor_page:
            encoded = _canonical({"workspace_id": workspace_id, "run_id": run_id, "snapshot": factor_snapshot, "last_node_id": factor_page[-1]["node_id"]}).encode()
            next_node_cursor = base64.urlsafe_b64encode(encoded).decode().rstrip("=")
        nodes = []
        headline = []
        for row in latest.values():
            stub = self._node_stub(row)
            if row["node_class"] in {"data/source", "assumption/config"} and not row["private"]:
                nodes.append(stub)
            if row["node_class"] == "calc/result":
                summary = _json(row["summary_json"])
                headline.append({"origin": summary.get("origin"), "method": summary.get("method"), "ultimate": summary.get("ultimate"), "outstanding": summary.get("outstanding"), "result_node_id": row["node_id"], "revision": row["revision"], "state": stub["state"], "reason_code": stub["reason_code"]})
        nodes.extend(self._node_stub(row) for row in factor_page)
        scenarios = [{"run_id": row["run_id"], "label": row["run_id"]} for row in scenario_rows]
        node_counts = {}
        for row in rows:
            node_counts[row["node_class"]] = node_counts.get(row["node_class"], 0) + 1
        return {"workspace_id": workspace_id, "run_id": run_id, "nodes": nodes, "headline": headline, "scenarios": scenarios, "node_pagination": {"has_more": has_more_nodes, "next_cursor": next_node_cursor, "node_limit": node_limit}, "counts": {"nodes": len(rows), "summary_nodes": len(nodes), "factor_nodes": len(factor_rows), "results": len(headline), "by_class": node_counts}}

    def adjacency(self, workspace_id, node_id, revision=1, limit=200, cursor=None):
        if not isinstance(limit, int) or not 1 <= limit <= 2000:
            raise ValueError("limit must be an integer from 1 through 2000")
        watermark = None
        with self.connect() as db:
            if db.execute("SELECT 1 FROM evidence_graph_nodes WHERE workspace_id=? AND node_id=? AND revision=?", (workspace_id, node_id, revision)).fetchone() is None:
                raise KeyError((node_id, revision))
            if cursor:
                try:
                    decoded = json.loads(base64.urlsafe_b64decode(cursor.encode() + b"=" * (-len(cursor) % 4)))
                except (ValueError, binascii.Error, json.JSONDecodeError, UnicodeDecodeError) as exc:
                    raise ValueError("Malformed adjacency cursor") from exc
                if not isinstance(decoded, dict) or decoded.get("node_id") != node_id or decoded.get("revision") != revision or not isinstance(decoded.get("watermark"), int) or not isinstance(decoded.get("last_edge_id"), str):
                    raise ValueError("Adjacency cursor is incompatible with this pinned snapshot")
                watermark = decoded["watermark"]
            else:
                watermark = db.execute("SELECT COALESCE(MAX(rowid), 0) AS watermark FROM evidence_graph_edges WHERE workspace_id=?", (workspace_id,)).fetchone()["watermark"]
            edges = db.execute(
                """SELECT e.*, s.label AS source_label, s.node_class AS source_class,
                          t.label AS target_label, t.node_class AS target_class
                   FROM evidence_graph_edges e
                   JOIN evidence_graph_nodes s ON s.workspace_id=e.workspace_id AND s.node_id=e.source_node_id AND s.revision=e.source_revision
                   JOIN evidence_graph_nodes t ON t.workspace_id=e.workspace_id AND t.node_id=e.target_node_id AND t.revision=e.target_revision
                   WHERE e.workspace_id=? AND e.rowid<=? AND ((e.source_node_id=? AND e.source_revision=?) OR (e.target_node_id=? AND e.target_revision=?))
                   ORDER BY e.edge_id""",
                (workspace_id, watermark, node_id, revision, node_id, revision),
            ).fetchall()
        snapshot = _digest([row["edge_id"] for row in edges])
        after = ""
        if cursor:
            if decoded.get("snapshot") != snapshot:
                raise ValueError("Adjacency cursor is incompatible with this pinned snapshot")
            after = decoded["last_edge_id"]
        remaining = [row for row in edges if row["edge_id"] > after]
        page = remaining[:limit]

        def make_items(edge_rows):
            items = []
            for row in edge_rows:
                outgoing = row["source_node_id"] == node_id and row["source_revision"] == revision
                label = row["target_label"] if outgoing else row["source_label"]
                if len(label) > 96:
                    label = label[:93] + "..."
                items.append({"edge_id": row["edge_id"], "type": row["edge_type"], "direction": "outgoing" if outgoing else "incoming", "node_id": row["target_node_id"] if outgoing else row["source_node_id"], "revision": row["target_revision"] if outgoing else row["source_revision"], "label": label, "node_class": row["target_class"] if outgoing else row["source_class"], "metadata": _json(row["metadata_json"])})
            return items

        while page:
            has_more = len(remaining) > len(page)
            next_cursor = None
            if has_more:
                body = _canonical({"node_id": node_id, "revision": revision, "snapshot": snapshot, "watermark": watermark, "last_edge_id": page[-1]["edge_id"]}).encode()
                next_cursor = base64.urlsafe_b64encode(body).decode().rstrip("=")
            items = make_items(page)
            response = {"items": items, "next_cursor": next_cursor, "has_more": has_more}
            if len(_canonical(response).encode("utf-8")) <= 50_000:
                return response
            page.pop()
        return {"items": [], "next_cursor": None, "has_more": bool(remaining)}

    def export_review(self, workspace_id, run_id="baseline"):
        with self.connect() as db:
            nodes = db.execute("SELECT * FROM evidence_graph_nodes WHERE workspace_id=? AND run_id=? ORDER BY node_id, revision", (workspace_id, run_id)).fetchall()
            edges = db.execute("SELECT * FROM evidence_graph_edges WHERE workspace_id=? AND run_id=? ORDER BY edge_id", (workspace_id, run_id)).fetchall()
        exported_nodes = []
        excluded_classes = set()
        excluded_payload_count = 0
        for row in nodes:
            if row["private"]:
                excluded_classes.add(row["node_class"])
                excluded_payload_count += 1
                continue
            exported_nodes.append({**self._node_record(row), "payload": _json(row["payload_json"])})
        exported_keys = {(node["node_id"], node["revision"]) for node in exported_nodes}
        exported_edges = []
        for row in edges:
            if (row["source_node_id"], row["source_revision"]) not in exported_keys or (row["target_node_id"], row["target_revision"]) not in exported_keys:
                continue
            exported_edges.append({"edge_id": row["edge_id"], "type": row["edge_type"], "source_node_id": row["source_node_id"], "source_revision": row["source_revision"], "target_node_id": row["target_node_id"], "target_revision": row["target_revision"], "metadata": _json(row["metadata_json"])})
        return {"manifest": {"export_policy": "analyst_local_review", "workspace_id": workspace_id, "run_id": run_id, "included": {"metadata": True, "edges": True, "blob_references": False}, "included_classes": sorted({node["node_class"] for node in exported_nodes}), "excluded_classes": sorted(excluded_classes), "excluded_payloads": excluded_payload_count}, "nodes": exported_nodes, "edges": exported_edges}
