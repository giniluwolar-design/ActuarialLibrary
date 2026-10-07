# Public interface

```python
from actuarial_library import (
    AnalysisConfig, DevelopmentConfig, FrequencySeverityConfig,
    validate_claims, build_triangles, load_triangle,
    run_reserving, export_results,
)
```

`validate_claims(claims, coverage)` returns normalized data, normalized coverage and a findings table. `valid` indicates whether error-severity findings exist. `require_valid()` raises a concise error. The original input frames are not mutated.

`build_triangles(..., valuation, portfolio, currency='EUR', amount_basis='after_deductible', grain='Y', start_year=None)` selects one homogeneous group and ignores later valuations before checking history. `grain='Q'` selects quarterly periods. A Triangle exposes `frame(basis, incremental=False)`, `latest(basis)` and `trace(origin, development)`. Returned matrices contain NaN for missing/future values; exported JSON uses null.

`load_triangle(data, valuation=..., grain='Y', metadata={...})` adapts aggregate input with the explicit contract in the data dictionary. Include provenance, currency and amount basis in metadata for an aggregate analysis.

```python
config = AnalysisConfig(
    paid=DevelopmentConfig(average='volume', window=5,
        overrides={1: 1.8}, rationale='Selected after claim review'),
    frequency_severity=FrequencySeverityConfig(
        average='weighted', trend=0.025, count_mode='manual',
        expected_counts={'2025': 120}),
    priors={'2025': 600_000},
    selections={'2025': 'incurred_bf'},
    selection_notes={'2025': 'Young year; independent prior retained'},
)
result = run_reserving(triangle, config)
config_json = config.model_dump_json(indent=2)
restored = AnalysisConfig.model_validate_json(config_json)
payload = export_results(result)  # bytes, or pass a local path to save
```

Available final selection identifiers: `paid_cl`, `incurred_cl`, `paid_bf`, `incurred_bf`, `frequency_severity`, `manual`. Factor override/exclusion development ages are one-based. Manual ultimate selections require a numeric value in `manual_ultimates` and a nonempty `selection_notes` entry.

The export ZIP contains `results.csv`, `factors.csv`, `history.csv`, `analysis.json`. The JSON includes configuration and metadata plus the full result tables; it is safe data, never a pickle or executable payload. CSV text beginning with a spreadsheet formula prefix is escaped; JSON preserves original text. Source claims are not included.

The CLI `actuarial-demo --output data/demo --claims-per-portfolio 2000` creates reproducible synthetic input files. `python -m actuarial_library.demo` is equivalent. Values smaller than 20 claims per portfolio are rejected by the CLI because the example spans 20 origin years.
