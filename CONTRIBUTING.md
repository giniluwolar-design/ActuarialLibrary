# Contributing

Install the app/test extras using the constraints file. Run `python -m pytest -q` before submitting a change. Update methodology and tests whenever an actuarial assumption, data definition or numerical convention changes.

New methods belong in the library, not in the Streamlit UI. Provide a small hand-worked example, an independent reference where available, tests for zero/missing inputs and a clear explanation of limitations. Never silently floor negative reserves, fill missing historical observations, or change an input's amount basis.

Use fictitious data in issues, tests and screenshots. Do not commit client claims or exported local analysis packages. Keep proprietary data in `data/private/`, which is ignored by Git. Contributors should review files before committing; an ignore rule is not a data classification control.

The current unit of counting is one claim identifier within one portfolio. Changes to the counting unit, calendar grain or contract interpretation require an explicit data-contract revision.
