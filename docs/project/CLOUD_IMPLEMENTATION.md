# Cloud implementation continuation

Founder instruction, 7 October 2026: implement the agreed Actuarial Workbench, retain a lead architect/orchestrator and lightweight project manager, delegate bounded implementation to cheaper Codex models, and continue from mobile while the local computer sleeps. Cloud preparation is development infrastructure; the actuarial app itself remains local-first.

## Current execution gate — 11 October 2026

GitHub connection permissions are verified (push/admin). The existing remote executor reports `environment_offline`; its earlier mortality/annuity commit `04f2460` is not published, and recovery is unverified. Preserve that task; recover its exact files before review or integration. The local foundation is separately available in draft PR #14. No cloud work is currently confirmed active and no phone push has been tested.

Official OpenAI documentation describes published Codex Cloud environments and reopening the same task on web/mobile: [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments). Check Settings > Codex Cloud > Environments for an available published environment. A new task starts separate state; it does not recover this unpublished commit. The documented default seven-day saved-state window is not proof that this executor's files are recoverable. Do not invent a local scheduled workaround or promise 24/7 execution.

## Start

Read AGENTS.md, the repository actuarial-platform skill, HANDOVER.md and LESSONS.md. Existing GitHub issues #1 and #4–#13 are the design map. The corrected Wave 2 contracts, rather than superseded drafts, govern implementation. Personal skills on a developer's computer do not automatically transfer to cloud tasks.

## Delivery order

1. Integrate saved reserving results with the Evidence Graph. Expand a result into real recorded assumptions, factors, source cells and controls; preserve historical results on restart. Verify graph/export boundaries and browser interaction.
2. Expose explicit human reserving selections, paid-pattern cash-flow projection, dated tail assumptions, labelled partial results and downloadable schedules. Add the quarterly 30 June 2026 synthetic reference case alongside the existing annual case.
3. Integrate injected EIOPA curve evidence and approved ACT/365F/log-linear discount-factor conventions. Missing/mismatched curves block the discounted view while retaining valid undiscounted rows. Test signed payments and actual trace downloads.
4. Integrate synthetic finite-horizon mortality/survival and regular/partner annuity factors. Calendar schedules, per-annual-benefit normalisation, explicit per-life weights, residual survival and trace downloads must meet the corrected contract. Actual AG caching/redistribution and whole-life closure retain their release gates.
5. Complete common navigation, typed Guided Run/Evidence Review tools, installation/documentation and release checks. Preserve Streamlit and dist/ until replacement paths are exercised.

## Working arrangement

The lead owns design, assignments, integration and final review. Cheaper workers receive explicit non-overlapping file ownership and acceptance checks; reserve stronger review for actuarial semantics, architecture, security and visual quality. The PM reports decided, implemented, verified, blocked and next, with dates and artifacts. Verification gaps are not automatically blockers.

Use Matt Pocock's implementation approach: red-green tests through the accepted public calculation/store/API seams, focused checks during work, full suite at the integration milestone, and separate standards/spec reviews. Existing contracts supply the agreed seams and independent fixtures. Keep commits bounded and reference the relevant issues. Do not restart broad design or create duplicate tickets.

Update HANDOVER.md after each milestone. Continue approved slices autonomously; ask the founder only for changes to product scope, actuarial conventions, privacy boundaries or release assumptions. Give concise Dutch progress updates in the cloud task at milestones and on real blockers. Completion requires numerical, API/download, model (where used) and visual evidence reported separately; passing specifications alone does not finish implementation.

## Execution and privacy

Cloud work uses repository source and seeded synthetic fixtures only. Private claim data, local runtime stores and credentials remain on the original computer and must never be uploaded. The in-app analyst retains typed deterministic tools with no shell/code execution and no cloud-model fallback.

Use an isolated cloud checkout and branch; open a reviewable pull request rather than silently merging or deploying. Repository publication is not an app deployment. A cloud task can continue while the original computer sleeps; a task that uses its local executor still requires it online. Do not claim phone push delivery or perpetual execution without verifying account notification settings and the actual cloud task.
