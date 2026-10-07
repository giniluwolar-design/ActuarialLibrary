# Product and architecture decisions

## D001 — separate development and actuarial operation

The coding agent may edit and test the repository. The in-app analyst only invokes typed actuarial tools. They share reviewed method documentation, not unrestricted privileges or customer data. Provider quota changes must not change this boundary.

## D002 — deterministic workflow with optional model interpretation

Keep calculations, validation, report assembly and known documentation actions in explicit code. One local model handles open-ended investigations. Use streaming, compact tool schemas, saved evidence, per-call and whole-task budgets, and cancellation. No automatic retry of completed scenario/artifact side effects.

Use the current SQLite job implementation while the app is single-user. Reconsider LangGraph when durable branching, resumable steps and explicit review interruptions justify a workflow framework. A framework will not make an oversized model fit in RAM. MCP would expose tools; it does not replace job persistence or memory.

## D003 — portable reviewed memory

Use AGENTS.md as entry point; HANDOVER.md for current state; FEEDBACK.md for requested outcomes; LESSONS.md for verified causes and prevention; DECISIONS.md for enduring tradeoffs. The actuarial skill remains the domain/product source. App feedback and failed jobs are local intake; only reviewed, non-sensitive lessons enter repository memory.

No hosted coding provider is connected automatically. Free hosted model quotas are an optional development fallback; private claims and app runtime data remain local. A later shared/customer deployment needs its own operating boundary.
