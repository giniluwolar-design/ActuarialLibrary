# Delivery lessons and agentic architecture

## Known project state — 18 September 2026

This is a handover baseline from the build history and repository inspection, not a new end-to-end certification. Recheck current files and runtime before making capability claims.

- Modular Python library under `src/actuarial_library/`; Polars/NumPy/Pydantic; validation, triangle building, reserving, review, exploration, exports, synthetic examples, and tests exist.
- `app.py` is the legacy Streamlit interface. The architectural direction is a separate browser client and Python API so that UI changes do not replace calculation code.
- `server.py` and `web/` are an incomplete API/client transition. The current routes use regenerated demo data and default analysis assumptions; chat creates a fresh session per request. Durable runs, full uploads, persistent chat, and usable artifact delivery are not complete there. The new API was not successfully started and verified in the preceding session.
- Local Ollama/Gemma integration has bounded, typed, allowlisted tool calls for explanations, evidence inspection, scenarios, and artifacts. It does not execute model-generated Python or shell commands. Existing explanations use controlled notes, not comprehensive retrieval from current repository/API documentation.
- Current agent artifacts include Markdown reports and synthetic CSV test packages. Word, PowerPoint, per-analysis formula Excel, bootstrap, EIOPA/DNB adapters, and an MCP server remain future work.
- Existing worked Excel and local numerical tests have verification evidence in repository docs. Cross-platform CI configuration is not evidence of actual successful cross-platform runs. Native Excel changed-input recalculation remained limited by the machine's view-only license.
- Recent import failure: the running Streamlit process loaded an older installed package missing `export_google_sheets_package`. Updating source, reinstalling, and rerunning a page are distinct from restarting a process with cached imports. Successful local import/tests alone do not prove the served app is repaired. Verify the live runtime after restart.

## Lessons that should change implementation decisions

1. **Explain actual capabilities.** Real local-model trials produced incorrect terminology (BF expanded as “Best Fit”), wrong currency, confused API signatures, and claims of report charts that were absent. Grounding is necessary but not sufficient. Use current typed tool schemas and documentation, structured evidence, and evaluations for narrative accuracy; produce numerical report content deterministically.
2. **Make long work visible.** Local inference can take minutes due to model loading, prompt processing, token generation, and repeated tool rounds. Local does not mean instant or exempt from HTTP deadlines. Use progress events, cancellation, bounded work, and timing diagnostics; avoid merely increasing a timeout indefinitely.
3. **Persist meaningful state.** Chat history alone is insufficient. Save data version, valuation, assumptions, scenarios, results, tool evidence, artifacts, and job status. Resume an interrupted job without repeating side effects. Define whether a scenario branches from the baseline or another scenario explicitly.
4. **Test the delivery path.** A CSV ZIP is not a Google Sheets integration. A library export is not proof of a browser download. A prebuilt educational XLSX is not an export of the active portfolio. Exercise representative import → calculate → investigate → export paths and name what was actually tested.
5. **Keep product claims proportional.** Modern styling, a framework replacement, or an API scaffold does not establish production readiness. Security, operational reliability, releases, and user acceptance require separate evidence. Preserve working components while finishing the transition.

## Proposed architecture, not yet implemented in full

Treat “agentic operating system” as a domain workbench with durable execution. Build a thin orchestration layer around reliable tools; avoid writing a general-purpose OS or introducing multiple agents without a measured need.

| Component | Responsibility |
| --- | --- |
| Visual workspace | Agent dialogue plus data/control/factor/result panels, visible progress, evidence and downloads |
| Task orchestration | Typed jobs, state transitions, checkpoints, cancellation, bounded retries, review points and resumable execution |
| Tool registry | Validated inputs, documented semantics, controlled outputs and capability discovery |
| Actuarial library | Deterministic validation, calculations and independently checked statistical methods |
| Run/artifact store | Versioned inputs, assumptions, results, explanations, file content and provenance |
| Knowledge layer | Current API/schema/method documentation with traceable references and explicit unavailable answers |
| Model adapters | Measured local or authorized hosted models; provider-independent task/tool contracts |

Use one agent initially for choosing and explaining tool calls. Keep routine data validation, calculations, reconciliation, and report assembly in explicit code. An existing orchestration framework such as LangGraph is a candidate for checkpointed execution and review interruptions; adoption should solve an observed need rather than force a rewrite. MCP supplies a tool connection interface, not the full execution, storage, or governance layer.

For confidential customer use, design the deployment boundary explicitly: local or customer-controlled services, identity and permissions when shared, scoped tools, data minimization, retention, and inspectable logs. Local execution and open source alone are not a security assurance. Do not enable hosted tracing or cloud model fallback silently. Treat imported text and retrieved documents as data, not instructions granting extra tool privileges.

## Reduce development back-and-forth

Separate the agent that helps build software from the analyst agent used by customers. They may share documentation, but should not share unrestricted capabilities or production data by default.

For each build increment maintain a durable objective, acceptance examples, decisions, known gaps, and evidence of completion. Have the coding agent implement and exercise a bounded user journey, then present an inspectable result. The founder should spend time on actuarial decisions and product acceptance, not repeatedly re-explaining context or diagnosing installation details.

First suggested increment: one complete reserving task that survives a refresh or process restart, shows progress, explains one documented API accurately, compares a labelled exclusion scenario, and delivers a report tied to its run. Then broaden reporting and add data adapters/MCP. This is a recommendation, not a newly approved implementation scope.

Representative acceptance requests:

- “How does `run_reserving` work?” → real signature, required inputs, outputs, assumptions, limitations, and a runnable example matching the installed version.
- “Exclude 2020 at paid development 1→2 and compare.” → preserved baseline, explicit rationale, recorded scenario, reconciled impact, unchanged final selection unless requested.
- “Why did reserves increase?” → require comparable earlier results; separate measured movement, assumption effect, and unverified business explanation.
- “Create a report.” → existing downloadable file containing the selected run's actual values and correctly described contents.
- Interrupted local inference → visible incomplete status and bounded retry/resume; no invented success or duplicate artifacts.

## Learning resources checked 18 September 2026

- [LangGraph Essentials — Python](https://academy.langchain.com/courses/langgraph-essentials-python): free, roughly one hour; execution structure, memory, and human review interruptions.
- [Introduction to LangGraph — Python](https://academy.langchain.com/courses/intro-to-langgraph): longer video course; focus on state/memory and streaming/human-in-the-loop modules.
- [Building effective agents — Anthropic](https://www.anthropic.com/engineering/building-effective-agents): when fixed workflows or agent-directed decisions fit; start with simple composable patterns.
- [Demystifying evals for AI agents — Anthropic](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents): evaluate observable outcomes and failure cases, not just a plausible demonstration.

These are learning resources, not commitments to their hosted services or a required model vendor.

## Browser increment — 18 September 2026, later session

The browser transition now has a local SQLite checkpoint store, workspace IDs, immutable saved result payloads, persistent transcript/evidence/artifacts, asynchronous Ollama jobs with polled progress and cooperative cancellation, and actual file/ZIP download routes. The working surface includes paid/incurred/count triangles, clickable observation evidence, method comparison by origin, and separate explained scenarios. API workflow tests cover checkpoint restoration and download contents. See `docs/application-architecture.md` for the current implementation and limits; the earlier handover bullets above describe the preceding state.

The browser remains a synthetic-data, single-user local prototype. Uploads and final selections remain in Streamlit. Interrupted model calls are marked rather than replayed automatically. Saved evidence is available to a follow-up. Local SQLite is not encrypted or a formal audit store; run one server worker. The launcher explicitly imports the checkout source to avoid stale installed-library surprises.
