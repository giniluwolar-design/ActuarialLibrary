# Third-party software and research

The MIT license covers original project code and synthetic data only. It does not relicense dependencies, external papers or their datasets.

The independent benchmark uses `chainladder==0.8.26`, released under MPL-2.0. Its RAA sample is read from the installed package, not redistributed as an independently relicensed CSV. Keep that package's license and notices when redistributing it. Source: https://github.com/casact/chainladder-python and https://github.com/casact/chainladder-python/blob/master/LICENSE.

NumPy, Polars, Pydantic, Streamlit, Plotly and the test dependencies retain their distribution licenses. `constraints.txt` records versions; package metadata contains their notices. Research papers in `docs/research.md` are linked and paraphrased, not bundled.

The worked Excel file was authored with the available artifact tooling. It is a standalone Open XML workbook; end users do not need that authoring runtime. The authoring script is included for transparency, but rebuilding the workbook requires `@oai/artifact-tool`; it is not a runtime dependency of the Python library or app.
