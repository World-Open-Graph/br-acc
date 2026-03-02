# Reproducibility

## Quick Local Demo (Deterministic)

```bash
cp .env.example .env
make bootstrap-demo
```

Expected results:
- `http://localhost:8000/health` returns `{"status":"ok"}`.
- Neo4j Browser is available at `http://localhost:7474`.
- Demo graph seed is loaded via `infra/scripts/seed-dev.sh`.

## One-Script End-to-End Orchestration

```bash
# Demo profile
bash scripts/bootstrap_public_demo.sh --profile demo

# Full profile (orchestrates docker + ETL loop)
bash scripts/bootstrap_public_demo.sh --profile full --pipelines cnpj,tse,transparencia,sanctions --download

# Heavy one-command full ingestion (all implemented pipelines from contract)
make bootstrap-all

# Noninteractive heavy run (CI/automation)
make bootstrap-all-noninteractive
```

Notes:
- `full` profile runtime depends on external data source availability and your machine resources.
- Some pipelines require credentials, API keys, or source-specific access preconditions.
- `bootstrap-all` uses Dockerized ETL (no host `uv` required), prompts for reset by default, and writes run evidence to `audit-results/bootstrap-all/<UTC_STAMP>/summary.{json,md}`.
- `bootstrap-all` defaults to full historical attempts and can be very long-running.

## BYO-Data Ingestion

Use ETL directly:

```bash
cd etl
uv sync
uv run bracc-etl sources
uv run bracc-etl run --source cnpj --neo4j-password "$NEO4J_PASSWORD" --data-dir ../data
```

## What This Does Not Reproduce Automatically

- Production-scale graph counters (see `docs/reference_metrics.md` for reference production snapshot).
- Guaranteed success for every external source in every run (blocked/failing sources are explicitly reported).
- Private/institutional modules outside public boundary.
