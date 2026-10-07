# Actuarial Workbench

The shared language for a local-first professional actuarial environment whose tools expose their inputs, assumptions, calculations, evidence, and outputs for review.

## Language

**Actuarial Workbench**:
The user-facing environment in which an actuary finds, runs, inspects, explains, and exports multiple actuarial tools.
_Avoid_: Actuarial Library when referring to the complete user experience

**Actuarial Library**:
The deterministic, reusable calculation layer beneath the Actuarial Workbench.
_Avoid_: Workbench, app

**Actuarial Tool**:
A coherent professional workflow within the Actuarial Workbench, with its own data contract, calculations, controls, evidence, and outputs.
_Avoid_: Feature, page

**Reserving Engine**:
The Actuarial Tool for property and casualty reserve analysis, including data validation, triangles, assumptions, methods, selections, review evidence, and exports.
_Avoid_: Reserve calculator

**Reserving Cash-flow Projection**:
The future payment stream obtained by applying an explicit paid development pattern to a selected property and casualty reserve outcome.
_Avoid_: Incurred development, person-level cash-flow model

**Annuity-factor Engine**:
The Actuarial Tool that calculates actuarial present-value factors from explicit cash-flow timing, decrement assumptions, and discount curves.
_Avoid_: Cash-flow generator

**Evidence Graph**:
The navigable network behind a saved result, linking it to source data, assumptions, methods, intermediate values, controls, documents, explanations, and human judgements through named relationships.
_Avoid_: Dashboard, audit log

**Evidence Block**:
A visible item in the Evidence Graph representing one recorded result, input, assumption, calculation step, control, source passage, explanation, or judgement.
_Avoid_: Widget, card

**Guided Run**:
A way of using an Actuarial Tool in which the analyst orchestrates a deterministic model run and explains its recorded output.
_Avoid_: AI calculation

**Evidence Review**:
A way of using an Actuarial Tool in which the actuary directly traverses and evaluates the Evidence Graph for a saved run.
_Avoid_: Guided Run, dashboard view
