# First-commit manifest — 27 September 2026

**Produced by:** commit_manifest (bounded worker, read-only)
**Governed by:** `docs/project/review-2026-09-27-wave1-verdict.md` section "First-commit inventory verdict"
**Status:** verified proposal only — NO staging, commit or push executed

---

## 1. Live git state at build time

```
Tracked files:           5
Untracked non-ignored:   80
Working tree clean except: untracked paths
```

Tracked (5): `.openai/hosting.json`, `dist/app.js`, `dist/index.html`, `dist/style.css`, `dist/worker.js`

Untracked (80) — full list:

```
.github/workflows/tests.yml
.gitignore
.streamlit/config.toml
AGENTS.md
CLAUDE.md
CONTEXT.md
CONTRIBUTING.md
GEMINI.md
LICENSE
README.md
THIRD_PARTY.md
app.py
artifacts/workbook-authoring/build_workbook.mjs
constraints.txt
data/demo/claims.parquet
data/demo/coverage.csv
data/demo/invalid_claims.csv
docs/agentic-workflow.md
docs/agents/domain.md
docs/agents/issue-tracker.md
docs/agents/triage-labels.md
docs/api.md
docs/application-architecture.md
docs/benchmark.json
docs/contracts/annuity-factors-spec-v2.md
docs/contracts/evidence-graph-contract-v2.md
docs/data_dictionary.md
docs/methodology.md
docs/project/DECISIONS.md
docs/project/FEEDBACK.md
docs/project/HANDOVER.md
docs/project/LESSONS.md
docs/project/review-2026-09-25-wave1.md
docs/project/review-2026-09-27-wave1-verdict.md
docs/research-ag-mortality.md
docs/research-eiopa-rfr-2026q2.md
docs/research.md
docs/research/discounting-conventions-eiopa.md
docs/roadmap.md
docs/verification.md
docs/workspace-verification.md
examples/analyse_demo.py
examples/reserving_worked_example.xlsx
prototype/evidence-drilldown/app.js
prototype/evidence-drilldown/index.html
prototype/evidence-drilldown/README.md
prototype/evidence-drilldown/style.css
pyproject.toml
README.md
scripts/benchmark.py
scripts/check_local_agent.py
scripts/evaluate_local_agent.py
scripts/prepare_workbook.py
scripts/project_memory.py
scripts/run_workspace.py
server.py
skills/actuarial-platform/SKILL.md
skills/actuarial-platform/references/delivery-and-architecture.md
skills/actuarial-platform/references/domain-contract.md
src/actuarial_library/__init__.py
src/actuarial_library/agent.py
src/actuarial_library/agent_artifacts.py
src/actuarial_library/data.py
src/actuarial_library/demo.py
src/actuarial_library/exploration.py
src/actuarial_library/export.py
src/actuarial_library/local_inference.py
src/actuarial_library/models.py
src/actuarial_library/reserving.py
src/actuarial_library/review.py
src/actuarial_library/workspace.py
tests/test_agent.py
tests/test_app.py
tests/test_data.py
tests/test_exploration.py
tests/test_local_inference.py
tests/test_reserving.py
tests/test_workspace.py
web/app.js
web/index.html
web/styles.css
```

**Reconciliation:** 69 Category A + 11 Category C = 80 untracked entries ✓ matches `git ls-files --others --exclude-standard` (80). Old 63-file count is stale (7 new files appeared during this session: 4 prototype evidence-drilldown files, 2 docs/contracts, 1 docs/research).

---

## 2. Category A — approved for staging (69 files)

Subject to ordinary staged-content/secret review per verdict. Flagged items:

- `README.md` — contains incomplete prototype claims; review as-is, do not claim full integration
- `docs/` — same flag for docs with prototype references

```
.gitignore
.github/workflows/tests.yml
.streamlit/config.toml
AGENTS.md
CLAUDE.md
CONTEXT.md
CONTRIBUTING.md
GEMINI.md
LICENSE
README.md
THIRD_PARTY.md
app.py
server.py
constraints.txt
pyproject.toml
examples/analyse_demo.py
artifacts/workbook-authoring/build_workbook.mjs
scripts/benchmark.py
scripts/check_local_agent.py
scripts/evaluate_local_agent.py
scripts/prepare_workbook.py
scripts/project_memory.py
scripts/run_workspace.py
web/app.js
web/index.html
web/styles.css
skills/actuarial-platform/SKILL.md
skills/actuarial-platform/references/delivery-and-architecture.md
skills/actuarial-platform/references/domain-contract.md
src/actuarial_library/__init__.py
src/actuarial_library/agent.py
src/actuarial_library/agent_artifacts.py
src/actuarial_library/data.py
src/actuarial_library/demo.py
src/actuarial_library/exploration.py
src/actuarial_library/export.py
src/actuarial_library/local_inference.py
src/actuarial_library/models.py
src/actuarial_library/reserving.py
src/actuarial_library/review.py
src/actuarial_library/workspace.py
tests/test_agent.py
tests/test_app.py
tests/test_data.py
tests/test_exploration.py
tests/test_local_inference.py
tests/test_reserving.py
tests/test_workspace.py
docs/agentic-workflow.md
docs/agents/domain.md
docs/agents/issue-tracker.md
docs/agents/triage-labels.md
docs/api.md
docs/application-architecture.md
docs/contracts/annuity-factors-spec-v2.md
docs/contracts/evidence-graph-contract-v2.md
docs/data_dictionary.md
docs/methodology.md
docs/research-ag-mortality.md
docs/research-eiopa-rfr-2026q2.md
docs/research.md
docs/research/discounting-conventions-eiopa.md
docs/roadmap.md
docs/verification.md
docs/workspace-verification.md
prototype/evidence-drilldown/app.js
prototype/evidence-drilldown/index.html
prototype/evidence-drilldown/README.md
prototype/evidence-drilldown/style.css
```

---

## 3. Category B — excluded by .gitignore (verified with git check-ignore)

`.gitignore` verified — representative paths and outputs:

```
.gitignore:7:node_modules	artifacts/workbook-authoring/node_modules
  → .gitignore:7:node_modules	artifacts/workbook-authoring/node_modules
.gitignore:8:.scratch/	.scratch/
  → .gitignore:8:.scratch/	.scratch/
.gitignore:9:.env	.env
  → .gitignore:9:.env	.env
.gitignore:19:local_runs/	local_runs/workspace.sqlite3
  → .gitignore:19:local_runs/	local_runs/workspace.sqlite3
.gitignore:19:local_runs/	local_runs/workspace.sqlite3-wal
  → .gitignore:19:local_runs/	local_runs/workspace.sqlite3-wal
.gitignore:19:local_runs/	local_runs/workspace.sqlite3-shm
  → .gitignore:19:local_runs/	local_runs/workspace.sqlite3-shm
.gitignore:11:!.env.example	.env.example
  → NOT ignored (exception, correct)
```

Excluded groups (already ignored, verified): `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.ruff_cache/`, `build/`, `artifacts/previews/`, `artifacts/workbook_payload.json`, `artifacts/workbook_checks.json`, `local_runs/`, `data/private/`, `data/test_truth/`, `.DS_Store`.

Note: `artifacts/workbook-authoring/node_modules` is a symlink pointing to a machine-specific runtime cache — ignored by `node_modules` rule (no trailing slash needed; gitignore pattern matches symlink targets).

Note: `.scratch/`, `.env`, `.env.*` and SQLite main/WAL/SHM patterns are now fixed in `.gitignore` but those paths do not currently exist on disk (`.scratch/` is empty; no `.env` files; no WAL/SHM at build time) — the rules are in place for future protection.

---

## 4. Category C — decided per verdict (11 files)

### C1 demo data — approved by 27 Sep simulator match (3 files)
- `data/demo/claims.parquet`
- `data/demo/coverage.csv`
- `data/demo/invalid_claims.csv`
Verdict note: in-memory regeneration from repo default simulator matched all three tables on 27 Sep; no raw records printed.

### C2 curated workbook — retained, content review required (1 file)
- `examples/reserving_worked_example.xlsx` (3.1 MB)
Verdict note: README links it; authoring script depends on `@oai/artifact-tool`; regeneration not yet portable. ZIP integrity passed, no VBA/external links. Formula correctness and sensitive cell content require the documented content review before publication.

### C3 benchmark — dated evidence with environment context (1 file)
- `docs/benchmark.json` (4 KB)
Verdict note: generated by `scripts/benchmark.py`; keep as dated evidence; never describe as current performance guarantee.

### C4 docs/project memory — retained with sanitization todo (6 files)
- `docs/project/DECISIONS.md`
- `docs/project/FEEDBACK.md`
- `docs/project/HANDOVER.md`
- `docs/project/LESSONS.md`
- `docs/project/review-2026-09-25-wave1.md` (superseded draft)
- `docs/project/review-2026-09-27-wave1-verdict.md` (supersedes)
Sanitization todo before public push:
  - Strip machine-specific absolute paths
  - Strip session IDs (`ses_*`)
  - Strip usernames
  - Distinguish attribution from personal information
  - Mark Wave 1 drafts clearly as superseded by this review

### C5 tracked history — left unchanged (1 file)
- `.openai/hosting.json` (tracked, 91 B)
Verdict note: contains project_id/static keys; secret-pattern scan is not a deployment-ownership review. Leave tracked history unchanged; review whether old hosting binding belongs in public project before push; no history rewrite.

---

## 5. Staging command sequence (proposal — NOT executed)

```bash
# Step 1: .gitignore first (protects B paths before any add)
git add .gitignore

# Step 2: explicit Category A adds
git add \
  .github/workflows/tests.yml \
  .streamlit/config.toml \
  AGENTS.md \
  CLAUDE.md \
  CONTEXT.md \
  CONTRIBUTING.md \
  GEMINI.md \
  LICENSE \
  README.md \
  THIRD_PARTY.md \
  app.py \
  server.py \
  constraints.txt \
  pyproject.toml \
  examples/analyse_demo.py \
  artifacts/workbook-authoring/build_workbook.mjs \
  scripts/benchmark.py \
  scripts/check_local_agent.py \
  scripts/evaluate_local_agent.py \
  scripts/prepare_workbook.py \
  scripts/project_memory.py \
  scripts/run_workspace.py \
  web/app.js \
  web/index.html \
  web/styles.css \
  skills/actuarial-platform/SKILL.md \
  skills/actuarial-platform/references/delivery-and-architecture.md \
  skills/actuarial-platform/references/domain-contract.md \
  src/actuarial_library/__init__.py \
  src/actuarial_library/agent.py \
  src/actuarial_library/agent_artifacts.py \
  src/actuarial_library/data.py \
  src/actuarial_library/demo.py \
  src/actuarial_library/exploration.py \
  src/actuarial_library/export.py \
  src/actuarial_library/local_inference.py \
  src/actuarial_library/models.py \
  src/actuarial_library/reserving.py \
  src/actuarial_library/review.py \
  src/actuarial_library/workspace.py \
  tests/test_agent.py \
  tests/test_app.py \
  tests/test_data.py \
  tests/test_exploration.py \
  tests/test_local_inference.py \
  tests/test_reserving.py \
  tests/test_workspace.py \
  docs/agentic-workflow.md \
  docs/agents/domain.md \
  docs/agents/issue-tracker.md \
  docs/agents/triage-labels.md \
  docs/api.md \
  docs/application-architecture.md \
  docs/contracts/annuity-factors-spec-v2.md \
  docs/contracts/evidence-graph-contract-v2.md \
  docs/data_dictionary.md \
  docs/methodology.md \
  docs/research-ag-mortality.md \
  docs/research-eiopa-rfr-2026q2.md \
  docs/research.md \
  docs/research/discounting-conventions-eiopa.md \
  docs/roadmap.md \
  docs/verification.md \
  docs/workspace-verification.md \
  prototype/evidence-drilldown/app.js \
  prototype/evidence-drilldown/index.html \
  prototype/evidence-drilldown/README.md \
  prototype/evidence-drilldown/style.css
```

Category C files are **not** in this staging sequence — they require the decision-owner review noted in Section 4 before any add.

---

## 6. Pre-staging review checklist

- [ ] **Secret-pattern scan** — run `grep -lE '(password|secret|api[_-]?key|token|private.?key|bearer|auth=|credential|BEGIN.*PRIVATE)'` across all staged text files. Result: all matches are policy-language references (e.g. "never include credentials"), no actual secret values. Re-run at staging time.
- [ ] **Absolute machine path scan** — scan staged text files for personal machine paths. The original draft contained a local-runtime symlink path; the 7 October public preparation removed that path and private session/job identifiers. Recheck the actual staged inventory before push.
- [ ] **XLSX content review** — `examples/reserving_worked_example.xlsx` needs formula-correctness and sensitive-cell-content review before publication (Category C2, not yet staged).
- [ ] **Large-file sanity** — `examples/reserving_worked_example.xlsx` is 3.1 MB (largest file). No other file exceeds 500 KB. Verify git LFS or size policy if this becomes a concern.
- [ ] **Recount reconciliation** — manifest total (80) matches `git ls-files --others --exclude-standard` (80) ✓
- [ ] **`git check-ignore` verification** — all Category B representative paths verified ✓ (see Section 3)
- [ ] **Prototype claims flag** — README.md and docs with prototype references are in Category A but flagged for incomplete-claim review per verdict.
- [ ] **`docs/project/` sanitization** — machine paths, session IDs, usernames must be stripped before public push.

---

## 7. Explicit non-execution statement

**NO staging, commit, stash, or push was run.** This manifest is a verified proposal only. The wave does not authorize committing or pushing the unreviewed inventory. Category C items require decision-owner review before staging. Category A items require the pre-staging checklist to pass before `git add`. Pushing the unreviewed inventory is not authorized.

---

*Manifest built 27 September 2026 from live git state; old 63-file count superseded.*
