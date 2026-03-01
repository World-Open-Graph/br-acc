.PHONY: install lint type-check test neutrality check dev dev-down seed

install:
	cd api && uv sync --extra dev
	cd etl && uv sync --extra dev
	cd frontend && npm ci

lint:
	cd api && uv run ruff check src/ tests/
	cd etl && uv run ruff check src/ tests/
	cd frontend && npx eslint src/

type-check:
	cd api && uv run mypy src/
	cd etl && uv run mypy src/
	cd frontend && npx tsc --noEmit

test:
	cd api && uv run pytest -q
	cd etl && uv run pytest -q
	cd frontend && npm test -- --run

neutrality:
	@! grep -rn \
	  'suspicious\|corrupt\|criminal\|fraudulent\|illegal\|guilty' \
	  api/src/ etl/src/ frontend/src/ \
	  --include='*.py' --include='*.ts' --include='*.tsx' --include='*.json' \
	  || (echo 'NEUTRALITY VIOLATION: banned words found in source' && exit 1)

check: lint type-check test neutrality

dev:
	cd infra && docker compose up

dev-down:
	cd infra && docker compose down

seed:
	bash infra/scripts/seed-dev.sh
