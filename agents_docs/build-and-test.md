# Build and Test — BR/ACC Open Graph

All three sub-projects have independent dependency manifests. **Always sync before building or testing.** There is no `Makefile`; use the commands below directly.

---

## API

```bash
cd api
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest -q                  # ~214 tests, ~4 s
```

## ETL

```bash
cd etl
uv sync --extra dev
uv run ruff check src/ tests/
uv run mypy src/
uv run pytest -q                  # ~952 tests, ~6 s
```

## Frontend

```bash
cd frontend
npm ci                            # never npm install
npx eslint src/                   # 0 errors required; warnings OK
npx tsc --noEmit
npm test -- --run                 # ~154 Vitest tests, ~5 s
npm run build                     # tsc -b && vite build
npm run dev                       # dev server → http://localhost:5173
```

## Neutrality check (run from repo root)

Must pass before every commit — also enforced in CI:

```bash
! grep -rn \
  "suspicious\|corrupt\|criminal\|fraudulent\|illegal\|guilty" \
  api/src/ etl/src/ frontend/src/ \
  --include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
  || (echo "NEUTRALITY VIOLATION" && exit 1)
```

---

## Local stack (Docker Compose)

```bash
cp .env.example .env              # set NEO4J_PASSWORD at a minimum
cd infra && docker compose up -d
```

| Service       | URL                   |
| ------------- | --------------------- |
| API           | http://localhost:8000 |
| Frontend      | http://localhost:3000 |
| Neo4j Browser | http://localhost:7474 |

## Integration tests (require a live Neo4j instance)

Integration tests are excluded by default via `addopts = "-m 'not integration'"` in each `pyproject.toml`.

```bash
export NEO4J_URI=bolt://localhost:7687
export NEO4J_PASSWORD=testpassword
cd api && uv run pytest -m integration
cd etl && uv run pytest -m integration
```

---

## Release gates

A release tag may only be cut from `main` once all five gates are green:

1. CI workflow (`ci.yml`)
2. Security workflow (`security.yml`)
3. Public privacy gate — `scripts/check_public_privacy.py`
4. Compliance pack gate — `scripts/check_compliance_pack.py`
5. Public boundary gate — `scripts/check_open_core_boundary.py`

See [docs/release/release_policy.md](../docs/release/release_policy.md) for the full process.
