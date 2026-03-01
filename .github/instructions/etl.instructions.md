---
applyTo: "etl/src/**/*.py,etl/tests/**/*.py"
---

# ETL — Path-Specific Instructions

## Structure

- `etl/src/bracc_etl/runner.py` — CLI entry point (`bracc-etl` console script)
- `etl/src/bracc_etl/base.py` — Base pipeline class
- `etl/src/bracc_etl/pipelines/` — One pipeline file per data source (~50 sources)
- `etl/src/bracc_etl/transforms/` — Shared data transformation utilities
- `etl/src/bracc_etl/entity_resolution/` — Entity matching/deduplication logic
- `etl/src/bracc_etl/loader.py` — Neo4j loader helpers
- `etl/src/bracc_etl/linking_hooks.py` — Graph linking utilities
- `etl/scripts/` — Download scripts for each data source (download\_\*.py)

## Rules

- Python 3.12+; mypy strict (all functions typed, return types required)
- ruff line length 100
- Each pipeline class extends the base in `base.py`
- Pipelines receive raw data and produce Neo4j Cypher MERGE operations via the loader
- **Never** store personal data beyond what is required for transparency purposes
- Only use public-domain Brazilian government data sources
- `resolution` optional dependency group adds `splink` for entity resolution; `bigquery` group adds GCP deps for `download_cnpj_bq.py`

## Testing

- Tests in `etl/tests/` — one `test_*_pipeline.py` per pipeline
- Tests are unit tests using mocked HTTP responses and fixtures in `etl/tests/fixtures/`
- No Neo4j required for unit tests; integration tests (in `etl/tests/integration/`) are skipped by default
- Always run `cd etl && uv run pytest -q` after changes; ~952 tests, ~6s
