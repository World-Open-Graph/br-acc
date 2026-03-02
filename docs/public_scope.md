# Public Scope

This page defines the public boundary of `World-Open-Graph/br-acc`.

## Included In Public Repo

- FastAPI API (`api/`) and public-safe routers.
- ETL framework and pipeline modules (`etl/`).
- Frontend explorer (`frontend/`).
- Dockerized local infrastructure (`infra/`).
- Compliance and governance documents.
- Synthetic demo data under `data/demo/`.

## Not Included By Default

- A pre-populated production Neo4j database dump.
- Private/institutional operational modules.
- Guarantees that every external government portal is reachable at all times.

## Reproducibility Modes

| Mode | What you get | Command |
|---|---|---|
| `demo_local` | Deterministic local stack + seeded demo graph | `make bootstrap-demo` |
| `byo_ingestion` | Full ETL run path using your own data downloads | `make bootstrap-all` |
| `reference_production_snapshot` | Timestamped production counters for transparency | `docs/reference_metrics.md` |

## Transparency Notes

- Source availability and load status are tracked in `docs/source_registry_br_v1.csv`.
- Registry-backed summary is generated into `docs/data-sources.md`.
- URL reliability is audited by `scripts/check_source_urls.py`.
