# BR/ACC Open Graph — Copilot Coding Agent Instructions

## Project Summary

BR/ACC Open Graph is an open-source graph infrastructure for Brazilian public-data intelligence (anti-corruption transparency). It ingests public Brazilian government records into a Neo4j graph and surfaces them via a FastAPI backend and a React frontend.

**Stack:** Neo4j 5 Community · FastAPI (Python 3.12+) · Vite + React 19 + TypeScript 5.7 · Python ETL pipelines · Docker Compose
**Package managers:** `uv` (Python) · `npm` (frontend)
**Tools validated in this environment:** uv 0.8.13 · Node 22 · Python 3.12

---

## Repository Layout

```
api/          FastAPI app — routers, services, Cypher queries, middleware
  src/bracc/    main.py (entrypoint), config.py, dependencies.py,
                routers/, services/, queries/, models/, middleware/
  tests/        unit/ and integration/ (integration skipped by default)
  pyproject.toml
etl/          ETL pipelines and downloaders
  src/bracc_etl/  pipelines/, transforms/, entity_resolution/, runner.py
  tests/        ~50 pipeline tests (unit only by default)
  pyproject.toml
frontend/     Vite + React 19 app
  src/          App.tsx, pages/, components/, hooks/, stores/, api/, actions/
  package.json, vite.config.ts, tsconfig.json, vitest.config.ts, eslint.config.js
infra/        docker-compose.yml, docker-compose.prod.yml, Caddyfile, neo4j/
scripts/      Validation and operational scripts (check_*, run_*, generate_*)
docs/         Legal pack, release docs, dataset matrix
.env.example  Environment variable reference — copy to .env before running
```

---

## Development Setup

Always run these before building or testing each sub-project:

```bash
# API
cd api && uv sync --extra dev

# ETL
cd etl && uv sync --extra dev

# Frontend
cd frontend && npm ci        # always use npm ci, NOT npm install
```

> **Note:** The README references `make check` and `make neutrality` but there is **no Makefile** in the repo. Use the individual commands below instead.

---

## CI Checks — All Must Pass Before Opening a PR

Run these from the repo root. All commands are validated and working.

### API

```bash
cd api
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest -q                  # ~214 tests, ~4s (integration tests excluded)
```

### ETL

```bash
cd etl
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest -q                  # ~952 tests, ~6s (integration tests excluded)
```

### Frontend

```bash
cd frontend
npm ci
npx eslint src/                   # warnings are OK; errors fail CI
npx tsc --noEmit
npm test -- --run                 # ~154 tests via Vitest, ~5s
```

### Neutrality (run from repo root, applies to all source)

```bash
! grep -rn \
  "suspicious\|corrupt\|criminal\|fraudulent\|illegal\|guilty" \
  api/src/ etl/src/ frontend/src/ \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
  || (echo "NEUTRALITY VIOLATION" && exit 1)
```

> **Critical:** This check is enforced in CI. Never use these words in any source file.

---

## Integration Tests

Integration tests require a live Neo4j 5 instance. They are **excluded by default** via `addopts = "-m 'not integration'"` in both `pyproject.toml` files. To run them:

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_PASSWORD=testpassword
cd api && uv run pytest -m integration
cd etl && uv run pytest -m integration
```

---

## Local Stack (Docker Compose)

```bash
cp .env.example .env              # set NEO4J_PASSWORD at minimum
cd infra && docker compose up -d  # starts neo4j, api, frontend
```

Services: API `http://localhost:8000` · Frontend `http://localhost:3000` · Neo4j Browser `http://localhost:7474`

---

## Key Configuration

- `api/src/bracc/config.py` — all settings via `pydantic-settings` (reads env vars or `.env`)
- `PRODUCT_TIER=community` must be set for API CI (set in CI `env:` block)
- Public-safe defaults for deployments: `PUBLIC_MODE=true`, `PUBLIC_ALLOW_PERSON=false`, `PUBLIC_ALLOW_ENTITY_LOOKUP=false`, `PUBLIC_ALLOW_INVESTIGATIONS=false`, `PATTERNS_ENABLED=false`
- `JWT_SECRET_KEY` must be ≥ 32 characters in production

---

## CI Workflows (`.github/workflows/`)

| File                                          | Triggers                                                                        |
| --------------------------------------------- | ------------------------------------------------------------------------------- |
| `ci.yml`                                      | Push/PR to `main` — runs api, etl, frontend, neutrality, integration (optional) |
| `security.yml`                                | Push/PR to `main` — gitleaks, bandit, pip-audit                                 |
| `deploy.yml`                                  | Release/manual trigger                                                          |
| `release-drafter.yml` + `publish-release.yml` | Release automation                                                              |

The `integration` job in CI only runs on `main` when `vars.ENABLE_INTEGRATION_TESTS == 'true'`.

---

## Code Style & Constraints

- **Python:** ruff (line length 100, py312 target); mypy strict; src layout (`src/bracc`, `src/bracc_etl`)
- **TypeScript:** strict tsc; ESLint with `eslint-plugin-react-hooks`
- **Never** add secrets, credentials, or private infra details to any file
- **Never** use the neutrality-banned words in source code (see Neutrality check above)
- Cypher queries for the API live in `api/src/bracc/queries/` as `.cypher` files and are loaded at runtime
- PR template requires exactly one `release:*` label and a public-safety checklist
