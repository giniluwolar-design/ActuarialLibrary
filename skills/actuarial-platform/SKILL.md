---
name: actuarial-platform
description: Build and evolve this open actuarial library and its agent-assisted workspace, preserving the founder's product vision, actuarial conventions, user experience preferences, and delivery lessons. Use for product, architecture, implementation, and release decisions on this platform.
---

# Actuarial platform

## Product intent

The founder works with insurers and pension administrators and observes fragmented spreadsheets, scripts, preparation, controls, documentation, and reporting. Vendor cost, opaque calculations, slow changes, and difficult second-line/auditor communication motivate this project. These are the founder's observations, not a claim about every vendor.

Build freely available, transparent actuarial tools with an agent that makes them usable by business specialists without programming. Potential distribution is a public repository and own website, promoted through LinkedIn; no channel or public deployment is yet decided. The immediate domain is non-life reserving. The broader ambition is an agent-assisted operating environment for these teams.

Success means less preparation and reconciliation, explainable results, easier review, and less vendor dependence. Raw calculation speed is only one component. AI can accelerate development; it does not establish actuarial correctness, security, or production readiness by itself. Free source code does not imply zero maintenance or deployment cost.

Communicate with the founder in Dutch unless they choose otherwise. Public library APIs, examples, documentation, and interface copy are English. Be candid and critical. Prefer completing useful work over repeated planning or permission questions within the authorized scope.

## Use the right context

- For reserving, data, exports, and test decisions, read [domain-contract.md](references/domain-contract.md).
- For architecture, agent behavior, product UX, or continuing implementation, read [delivery-and-architecture.md](references/delivery-and-architecture.md).
- Repository documentation and code describe implementation; these references preserve intent and lessons. Resolve conflicts using the latest user instruction and inspect current code. Dated state is not a live capability guarantee.

## Working approach

1. Translate the request into an observable user outcome. Reuse the existing library and preserve the separate cash-flow prototype unless integration is requested.
2. Inspect the relevant implementation, runtime, and tests. Distinguish requested, implemented, exercised, and verified capabilities.
3. Make a bounded change with explicit acceptance criteria. Keep actuarial calculations deterministic and separate from model-written explanations and UI.
4. Verify the actual user path as well as relevant numerical invariants. Report remaining gaps plainly; do not label scaffolding or a passing unit test as a finished production system.
5. Keep durable product decisions in these references and implementation details in repository docs. Update a lesson when new evidence changes it; do not turn a one-off workaround into a universal rule.

## Product boundaries

Keep the core workflow immediately legible: load data → inspect triangles and controls → estimate/select ultimate → explain and export. Put the AI analyst prominently in this workflow, with clear examples of asking questions, running tools, investigating assumptions, and creating real deliverables. Preserve visual, direct interaction alongside chat. Progressive disclosure should hide complexity, not evidence.

The founder wants a modern, visually engaging experience, development-factor triangles, observation exclusions with rationale, relevant inspection charts, and useful outlier flags. A chatbot added to a dense technical dashboard does not satisfy this intent.

Local-first operation is the current preference, including Gemma through Ollama. Do not silently introduce external processing of confidential data. Choose models based on measured task performance and hardware, not assumed capability from a name or local availability.

An agent may investigate, calculate, and propose labelled scenarios within the requested scope. Do not silently turn an exploratory exclusion into a final actuarial selection. Public publication, external communications, and customer deployment are separate from local implementation authorization.

A skill supplies reusable guidance. It does not itself create durable task execution, memory storage, scheduling, tool permissions, or an audit system. Recommend those components explicitly when proposing an agentic operating environment.
