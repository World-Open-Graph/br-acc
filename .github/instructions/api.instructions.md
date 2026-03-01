---
applyTo: "api/src/**/*.py,api/tests/**/*.py"
---

# API (FastAPI) — Path-Specific Instructions

## Structure

- `api/src/bracc/main.py` — FastAPI app factory and lifespan
- `api/src/bracc/config.py` — All settings via `pydantic-settings` (env vars / `.env`)
- `api/src/bracc/dependencies.py` — Neo4j driver injection (`get_driver`)
- `api/src/bracc/routers/` — One file per feature (public, entity, graph, search, auth, meta, patterns, investigation, baseline)
- `api/src/bracc/services/` — Business logic, Neo4j queries
- `api/src/bracc/queries/` — `.cypher` files loaded at runtime by the services
- `api/src/bracc/models/` — Pydantic v2 request/response models
- `api/src/bracc/middleware/` — CPF masking, rate limiting, security headers

## Rules

- Python 3.12+; use `from __future__ import annotations` for forward references
- mypy strict: all functions must have type annotations, including return types
- ruff line length 100; imports sorted (ruff handles this)
- Use `pydantic.BaseModel` with v2 field syntax (no `class Config`)
- Route handlers must use `async def`; use dependency injection for Neo4j driver
- New routers must be registered in `main.py` via `app.include_router(...)`
- **Never** expose personal identifiers (CPF/CPF fragments) in API responses — CPF masking middleware is active on all routes
- `PRODUCT_TIER` env var gates feature availability; check `settings.product_tier == "community"` before gating
- Patterns feature is gated by `settings.patterns_enabled`; the public patterns endpoint returns 503 when disabled

## Testing

- Tests live in `api/tests/unit/`; integration tests in `api/tests/integration/` (require Neo4j, skipped by default)
- Use `httpx.AsyncClient` with `app` as transport — see existing tests in `tests/unit/` for the pattern
- `conftest.py` provides the `client` fixture
- Always run `cd api && uv run pytest -q` after changes
