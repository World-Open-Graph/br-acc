# AGENTS.md — BR/ACC Open Graph

Open-source graph infrastructure for Brazilian government public-data transparency: Neo4j 5 graph + FastAPI backend + React 19 frontend.

**Package managers:** `uv` (Python) · `npm` (frontend — always `npm ci`, never `npm install`)

---

## Non-negotiable rules (apply to every task)

1. **Neutrality** — never write `suspicious`, `corrupt`, `criminal`, `fraudulent`, `illegal`, or `guilty` in any source file under `api/src/`, `etl/src/`, or `frontend/src/`. Use "flagged", "under review", "irregularity" instead.
2. **No CPF/personal identifiers** — CPF numbers must never appear in API responses. The masking middleware on all routes must not be bypassed.
3. **No secrets in source** — use environment variables. See [.env.example](.env.example).

---

## Commands

| Scope       | Commands                                                                                                 |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| API         | `cd api && uv sync --extra dev && uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest -q` |
| ETL         | `cd etl && uv sync --extra dev && uv run ruff check src/ tests/ && uv run mypy src/ && uv run pytest -q` |
| Frontend    | `cd frontend && npm ci && npx eslint src/ && npx tsc --noEmit && npm test -- --run`                      |
| Local stack | `cp .env.example .env && cd infra && docker compose up -d`                                               |

---

## Repository layout

| Path         | Purpose                                                     |
| ------------ | ----------------------------------------------------------- |
| `api/`       | FastAPI app — routers, services, Cypher queries, middleware |
| `etl/`       | ETL pipelines and download scripts                          |
| `frontend/`  | Vite + React 19 SPA                                         |
| `infra/`     | Docker Compose, Caddy, Neo4j init                           |
| `scripts/`   | Validation and release gate scripts                         |
| `docs/`      | Legal pack, release docs, bilingual documentation           |
| `data/demo/` | Synthetic demo dataset only — no real personal data         |

---

## Subsystem guides

Read the guide for whichever subsystem you're touching:

- [.github/instructions/api.instructions.md](.github/instructions/api.instructions.md) — FastAPI architecture, Cypher-as-files, feature gating, testing
- [.github/instructions/etl.instructions.md](.github/instructions/etl.instructions.md) — pipeline base class, MERGE-only rule, entity resolution, testing
- [.github/instructions/frontend.instructions.md](.github/instructions/frontend.instructions.md) — React 19, Zustand, i18n, feature flags, testing

## Reference docs

- [agents_docs/build-and-test.md](agents_docs/build-and-test.md) — full build, test, Docker, integration test, and release gate commands
- [agents_docs/security-and-compliance.md](agents_docs/security-and-compliance.md) — env flags, CPF masking, neutrality, public boundary, LGPD
- [agents_docs/git-workflow.md](agents_docs/git-workflow.md) — commit format, PR checklist, release label taxonomy, versioning
