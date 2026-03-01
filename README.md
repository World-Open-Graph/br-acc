# World Transparency Graph (WTG)

[![WTG Header](docs/brand/wtg-header.png)](docs/brand/wtg-header.png)

[![CI](https://github.com/brunoclz/world-transparency-graph/actions/workflows/ci.yml/badge.svg)](https://github.com/brunoclz/world-transparency-graph/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)

WTG is an open-source graph infrastructure for public data intelligence.

This repository contains the full code for the WTG public edition. The pattern engine is temporarily disabled pending validation.

## What it does

- Ingests public records with reproducible ETL pipelines.
- Loads normalized data into Neo4j.
- Exposes a public-safe API surface.
- Provides a React frontend for graph exploration.

Data patterns from public records are signals, not legal proof.

## Stack

- Graph DB: Neo4j 5 Community
- Backend: FastAPI (Python 3.12+, async)
- Frontend: Vite + React 19 + TypeScript
- ETL: Python (pandas, httpx)
- Infra: Docker Compose

## Quick start

```bash
cp .env.example .env
# set at least NEO4J_PASSWORD

make dev

export NEO4J_PASSWORD=your_password
make seed
```

- API: `http://localhost:8000/health`
- Frontend: `http://localhost:3000`
- Neo4j Browser: `http://localhost:7474`

## Public-safe defaults

Use these defaults for public deployments:

- `PRODUCT_TIER=community`
- `PUBLIC_MODE=true`
- `PUBLIC_ALLOW_PERSON=false`
- `PUBLIC_ALLOW_ENTITY_LOOKUP=false`
- `PUBLIC_ALLOW_INVESTIGATIONS=false`
- `PATTERNS_ENABLED=false`
- `VITE_PUBLIC_MODE=true`
- `VITE_PATTERNS_ENABLED=false`

## Development

```bash
# dependencies
cd api && uv sync --dev
cd ../etl && uv sync --dev
cd ../frontend && npm install

# quality
make check
make neutrality
```

## API surface

| Method | Route | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/public/meta` | Aggregated metrics and source health |
| GET | `/api/v1/public/graph/company/{cnpj_or_id}` | Public company subgraph |
| GET | `/api/v1/public/patterns/company/{cnpj_or_id}` | Returns `503` while pattern engine is disabled |

## Legal & Ethics

- [ETHICS.md](ETHICS.md)
- [LGPD.md](LGPD.md)
- [PRIVACY.md](PRIVACY.md)
- [TERMS.md](TERMS.md)
- [DISCLAIMER.md](DISCLAIMER.md)
- [SECURITY.md](SECURITY.md)
- [ABUSE_RESPONSE.md](ABUSE_RESPONSE.md)
- [docs/legal/legal-index.md](docs/legal/legal-index.md)

## License

[GNU Affero General Public License v3.0](LICENSE)
