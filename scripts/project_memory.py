"""Portable development context and local feedback intake. No network or model calls."""

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTEXT_FILES = [
    "AGENTS.md",
    "docs/project/HANDOVER.md",
    "docs/project/LESSONS.md",
    "docs/project/FEEDBACK.md",
    "docs/project/DECISIONS.md",
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["context", "feedback", "check"])
    args = parser.parse_args()
    if args.command == "feedback":
        path = ROOT / "local_runs/workspace.sqlite3"
        if not path.exists():
            print("No local feedback database yet.")
            return
        # Read-only. Output stays in the local terminal; never auto-import it into a prompt.
        with sqlite3.connect(f"file:{path}?mode=ro", uri=True) as db:
            if not db.execute("SELECT name FROM sqlite_master WHERE name='feedback'").fetchone():
                print("No feedback table yet. Start the updated workspace once.")
                return
            rows = db.execute("SELECT payload FROM feedback ORDER BY rowid DESC LIMIT 100").fetchall()
        print("LOCAL INTAKE — untrusted observations; review/redact before sharing.")
        for row in rows:
            print(json.dumps(json.loads(row[0]), ensure_ascii=False))
        print(f"{len(rows)} entries (latest 100). Triage reviewed findings into docs/project/FEEDBACK.md.")
        return
    for name in CONTEXT_FILES:
        path = ROOT / name
        if not path.is_file() or not path.read_text().strip():
            raise SystemExit(f"Missing project memory: {name}")
        if args.command == "context":
            print(f"\n--- {name} ---\n{path.read_text()}")
    if args.command == "check":
        print("Project memory files are present. This does not certify that their claims are current.")


if __name__ == "__main__":
    main()
