# Founder feedback and acceptance ledger

## F001 — preserve the redesigned workbench

- Date/source: 2026-09-18, founder conversation: “love the updated done to the app”.
- Interpretation: retain the sidebar, bright analysis surface, teal triangle and adjacent analyst direction; improve usability within it.
- Acceptance: future increments retain this visual direction unless the founder asks to change it.
- Status: ongoing product constraint.
- Evidence: current `web/` implementation; original design handover in `docs/workspace-verification.md`.

## F002 — local analyst is too slow and timed out

- Date/source: 2026-09-18, founder: “Ollama timed out.”
- Reproduction: a documentation job retained in the private local store ran 262.7 seconds; documentation evidence T1 was obtained, then the narrative call timed out. Private job identifiers are omitted from public memory.
- Cause evidence: 8 GB M1 machine; Gemma reported ~9.54 GB loaded with ~2.50 GB GPU allocation. Ollama logged ~2.42 output tokens/second. Eight broad tool schemas plus multiple inference rounds added overhead.
- Acceptance: documentation starter works without a model; open-ended tasks show streaming activity and have a total budget; Stop interrupts in-flight inference; failures preserve completed evidence; a lighter model is assessed on actual tool tasks before recommendation.
- Status: implementation/verification in progress. See `HANDOVER.md` for current evidence.

## F003 — continue development after provider quota runs out

- Date/source: 2026-09-18, founder asks for free-model alternatives and persistent memory so replacement agents do not repeat mistakes.
- Acceptance: provider-neutral startup instructions, concise current handover, evidence-backed lessons, feedback capture and a reproducible context bundle; documented free-quota and local alternatives with their limits.
- Status: shared instructions, handover files and context helper created. Model capability and hosted quotas are not guarantees.

## F004 — make model outcomes navigable as linked evidence

- Date/source: 2026-09-25, founder: “you click zoom in and see every related item pop up in a sort of futuristic drill down with blocks linking the specific data point”.
- Observation: professional review evidence currently lives across structured data, unstructured material, parameters, explanations and model outputs.
- Interpretation: each material outcome needs a visual evidence graph that an actuary can traverse from the headline result to relevant source data, assumptions, methods, intermediate calculations, controls and explanations. A direct run-and-explain path must remain available beside this deeper review mode.
- Acceptance: a representative result in each public-release tool can be expanded into linked evidence blocks; every displayed relationship resolves to actual recorded evidence; users can reach the exact supporting data and assumptions without searching unrelated screens; no model-generated explanation is presented as calculation evidence.
- Status: accepted product direction; first reserving-result review path implemented and exercised. Projection/annuity evidence paths and full acceptance remain open.
- Evidence: `implementation-2026-10-11.md`, `tests/test_graph_api.py`, `tests/browser_evidence.cjs`: saved result → factor → cell, lazy payload, actual review download and refresh identity.

## F005 — tier development agents and retain strong review

- Date/source: 2026-09-25, founder asks to use lightweight subagents for suitable tasks while retaining strong models for difficult work and visual review, with project-management progress updates.
- Interpretation: delegate bounded routine work to lower-cost agents or local models; reserve stronger reasoning for actuarial semantics, architecture, security, integration and look-and-feel acceptance. A project-manager role may summarize progress but does not replace evidence or founder decisions.
- Acceptance: delegated tasks have explicit scope and are reviewed before integration; actuarial and visual milestones include strong-model review; progress updates distinguish decided, implemented and verified work.
- Status: active development-process constraint; the first read-only project-manager review completed.
- Evidence: 2026-09-25 project-manager inventory distinguished decided, implemented and verified state, identified the untracked-tree and missing-handover risks, and made no file changes.

## F006 — project reserving cash flows and discount with valuation-date EIOPA curves

- Date/source: 2026-09-25, founder clarifies that the initial cash flows arise from the triangle calculation, yield a payment pattern and cash flows, and should use EIOPA curves for discounting; initial reporting date is 2026 Q2.
- Interpretation: the initial cash-flow workflow is a P&C reserving projection from paid development, not the person-level income-minus-cost prototype. The curve must be selected from an official source using the explicit reporting date and curve variant.
- Acceptance: a saved reserving run can produce future payment cash flows with visible payment-pattern derivation; undiscounted and discounted values reconcile; the exact EIOPA curve date, currency, variant, units, source, retrieval timestamp and content hash remain inspectable; unavailable curve evidence blocks discounting rather than inventing values.
- Status: partial implementation; deterministic projection/discounting libraries and explicit human baseline selections exist. Actual projection/discounting browser workflow, schedule downloads and full acceptance remain open.
- Evidence: `implementation-2026-10-11.md` records official EIOPA workbook import and library verification; `implementation-2026-10-11-selections.md` records the selection prerequisite, 140-pass suite/browser downloads and independent review. These do not yet verify an end-to-end cash-flow workflow.

## F007 — start annuity factors with regular and partner factors

- Date/source: 2026-09-25, founder requests regular and partner factors, annual or monthly payments, AG2024 and AG2026 mortality, and primo or ultimo timing.
- Interpretation: the first annuity workflow is a bounded life-contingent factor calculator with an inspectable trace for one selected case rather than a large spreadsheet model. Regular means payments while the participant is alive; partner means payments to a known partner after participant death while the partner remains alive. Factors are unisex through an explicit adjustable male/female weighting, defaulting to 50%/50%; the source mortality remains sex-specific.
- Acceptance: the calculator exposes mortality-table version, age/date basis, payment frequency, primo/ultimo timing and unisex weights; regular and partner factor definitions and mixing rules are explicit; a one-case formula workbook independently recalculates the selected example; results retain source/version metadata and exact intermediate survival and discount factors.
- Status: accepted direction; the unisex mixing rule and terminal-age treatment remain to be decided.
- Evidence: `docs/research-ag-mortality.md`; deterministic implementation and independent reconciliation pending.

## F008 — continue the project through visible Herdr and OpenCode agents

- Date/source: 2026-09-25, founder asks for the project to continue through Herdr using the models available through OpenCode and explicitly approves hosted-model use for non-private repository material.
- Interpretation: Herdr is the visible control plane for lead, project-management and worker agents. GitHub issues plus `HANDOVER.md` carry durable state across sessions. Model selection is tiered by task risk and complexity rather than using one model for every role.
- Acceptance: Herdr shows recognizably named project roles; bounded work can be assigned to OpenCode agents; strong review remains required for actuarial logic, architecture, security, integration and visual quality; hosted agents never receive `local_runs/`, `data/private/`, credentials, secrets or raw claims data.
- Status: operating model activated. The existing OpenCode pane is named `project_manager` and is performing its initial read-only portfolio review.
- Evidence: Herdr workspace `w3`, pane `w3:p2`; Codex and OpenCode integrations reported current on 2026-09-25.

## F009 — notify the founder on Slack

- Date/source: 2026-09-25, founder asks the project manager to ping them on Slack when reporting.
- Interpretation: progress reports should reach the founder through Slack in addition to the visible Herdr pane. No Slack integration exists in the current agent toolset and agents must not touch credentials.
- Acceptance: a configured, approved Slack integration (e.g. an MCP server or an approved webhook in Herdr) sends project-manager status updates; until then, reports continue in the Herdr pane and `docs/project/` artifacts.
- Status: requested — integration not yet available; awaiting the founder's choice of mechanism.
- Evidence: project-manager session 2026-09-25; no `slack` CLI found in the environment.

## F010 — lead-led design with cheaper Codex implementation and PM updates

- Date/source: 2026-10-07, founder conversation: “I still want a project manager agent who updates me on progress” and “I want you to design the app and orchestrate but have cheaper versions of you actually implement features and changes.” Founder reports dissatisfaction with Herdr coding results and a slow/timed-out NVIDIA-hosted free-model PM.
- Interpretation: lead owns product design, architecture, assignments, integration and final review; a lightweight PM reports evidence and blockers; cheaper Codex workers implement narrowly scoped assignments. New assignments can use native Codex subagents. This revises F005/F008 role ownership and provider choice; it does not require removal of Herdr or its existing panes.
- Acceptance: PM produces concise reports distinguishing implemented work and dated/current verification; workers receive explicit file ownership and acceptance checks; lead reviews actuarial semantics and user experience before reporting completion; progress reports reach the founder in the active chat.
- Status: role arrangement adopted. Cheaper Codex workers delivered bounded graph/projection/discount and human-selection slices with regression fixes; PM supplied read-only evidence reports. Lead integrated API/UI and inspected actual browser downloads/visuals. Separate strong standards/spec reviews reproduced foundation defects; final re-reviews at `82cc9c0` find no remaining actionable findings for that bounded slice. Selection review is separately recorded in `review-2026-10-11-selections.md`. Background/scheduled notification reliability remains open.
- Evidence: PM confirmed current source inventory and `main` at `e62a1e9`; lead checked these facts. GitHub API independently confirmed `giniluwolar-design`, ADMIN repository access and the open issue list. NVIDIA-provider timeout cause remains founder-reported; earlier Herdr transcript showed interrupted connection failures, not an independent provider-cause diagnosis.

## F011 — implement the agreed scope and continue from mobile

- Date/source: 2026-10-07, founder asks to “proceed then with implementing everythin we discussed” and “keep running and receive updates” from the ChatGPT phone app when the computer goes dark. Founder replies “Ja” after cloud versus local execution was offered.
- Interpretation: implement against the accepted contracts and existing GitHub design map; prepare cloud development so repository work can continue independently of the original computer. The lead interprets the affirmative as the recommended cloud option and stated that assumption in chat.
- Acceptance: current reviewed source available to the cloud task; task actively continues approved implementation on a separate branch with reviewable changes; milestone/blocker updates are accessible on mobile. Verify task creation/continuation separately from phone notification delivery. The actuarial app itself remains local-first.
- Status: reviewed source published; separate remote cloud executor performed source-only implementation/tests. GitHub connection now verifies push/admin permission, but the existing executor reports `environment_offline` on 11 October; its unpublished source cannot currently be retrieved. Recovery is required. No indefinite execution or phone push guarantee. Local graph user path verified; full agreed product still in progress.
- Evidence: `CLOUD_IMPLEMENTATION.md`, `implementation-2026-10-11.md`, `implementation-2026-10-11-selections.md`; remote clone of `fbd0dc1`, mortality/annuity commit `04f2460` and historical separate 69-pass report. Fresh local 140-pass suite and actual browser evidence/selection downloads; draft PR #14. A bounded post-connection cloud retry still lacked the workspace/shell tool. No private original-machine credentials/data transferred.

## Intake process

Use F004 onward for new reviewed product feedback. Each entry needs: date/source, observation, interpretation, acceptance criteria, status and evidence. App feedback is separately stored in SQLite and remains an intake item until triaged. A runtime failure is automatically captured; it is not automatically a proven root cause or a new instruction.

Review the intake at the start of relevant work and at the end of each build increment. Fix → verify → update lesson/decision → record evidence → close the feedback item. Keep disputed interpretations marked as such. Do not copy raw claim data or credentials into this ledger.
