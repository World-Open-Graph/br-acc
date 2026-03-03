.PHONY: dev stop api etl frontend lint type-check test test-api test-etl test-frontend test-integration-api test-integration-etl test-integration check seed clean download-cnpj download-tse download-transparencia download-sanctions download-all etl-cnpj etl-cnpj-stream etl-tse etl-transparencia etl-sanctions etl-all link-persons bootstrap-demo bootstrap-full bootstrap-all bootstrap-all-noninteractive bootstrap-all-report check-public-claims check-source-urls check-pipeline-contracts check-pipeline-inputs generate-pipeline-status generate-source-summary generate-reference-metrics

# ── Development ─────────────────────────────────────────
setup-env:
	bash scripts/init_env.sh

dev:
	docker compose up -d

stop:
	docker compose down

# ── API ─────────────────────────────────────────────────
api:
	cd api && uv run uvicorn bracc.main:app --reload --host 0.0.0.0 --port 8000

# ── ETL ─────────────────────────────────────────────────
etl:
	cd etl && uv run bracc-etl --help

seed:
	bash infra/scripts/seed-dev.sh

# ── CNPJ Data ──────────────────────────────────────────
download-cnpj:
	cd etl && uv run python scripts/download_cnpj.py --reference-only
	cd etl && uv run python scripts/download_cnpj.py --files 1

download-cnpj-all:
	cd etl && uv run python scripts/download_cnpj.py --files 10

etl-cnpj:
	cd etl && uv run bracc-etl run --source cnpj --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data

etl-cnpj-dev:
	cd etl && uv run bracc-etl run --source cnpj --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data --limit 10000

etl-cnpj-stream:
	cd etl && uv run bracc-etl run --source cnpj --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data --streaming

# ── TSE Data ──────────────────────────────────────────
download-tse:
	cd etl && uv run python scripts/download_tse.py --years 2024

etl-tse:
	cd etl && uv run bracc-etl run --source tse --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data

etl-tse-dev:
	cd etl && uv run bracc-etl run --source tse --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data --limit 10000

# ── Transparencia Data ────────────────────────────────
download-transparencia:
	cd etl && uv run python scripts/download_transparencia.py --year 2025

etl-transparencia:
	cd etl && uv run bracc-etl run --source transparencia --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data

etl-transparencia-dev:
	cd etl && uv run bracc-etl run --source transparencia --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data --limit 10000

# ── Sanctions Data ────────────────────────────────────
download-sanctions:
	cd etl && uv run python scripts/download_sanctions.py

etl-sanctions:
	cd etl && uv run bracc-etl run --source sanctions --neo4j-password "$${NEO4J_PASSWORD}" --data-dir ../data

# ── All Data ──────────────────────────────────────────
download-all: download-cnpj download-tse download-transparencia download-sanctions

etl-all: etl-cnpj etl-tse etl-transparencia etl-sanctions

# ── Entity Resolution ────────────────────────────────────
link-persons:
	docker compose exec neo4j cypher-shell -u neo4j -p "$${NEO4J_PASSWORD}" -f /scripts/link_persons.cypher

# ── Frontend ────────────────────────────────────────────
frontend:
	cd frontend && npm run dev

# ── Quality ─────────────────────────────────────────────
lint:
	cd api && uv run ruff check src/ tests/
	cd etl && uv run ruff check src/ tests/
	cd frontend && npm run lint

type-check:
	cd api && uv run mypy src/
	cd etl && uv run mypy src/
	cd frontend && npm run type-check

test-api:
	cd api && uv run pytest

test-etl:
	cd etl && uv run pytest

test-frontend:
	cd frontend && npm test

test: test-api test-etl test-frontend

# ── Integration tests ─────────────────────────────────
test-integration-api:
	cd api && uv run pytest -m integration

test-integration-etl:
	cd etl && uv run pytest -m integration

test-integration: test-integration-api test-integration-etl

# ── Full check (run before commit) ─────────────────────
check: lint type-check test
	@echo "All checks passed."

# ── Neutrality audit ───────────────────────────────────
neutrality:
	@! grep -rn \
		"suspicious\|corrupt\|criminal\|fraudulent\|illegal\|guilty\|CRITICAL\|HIGH.*severity\|MEDIUM.*severity\|LOW.*severity" \
		api/src/ etl/src/ frontend/src/ \
		--include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
		|| (echo "NEUTRALITY VIOLATION FOUND" && exit 1)
	@echo "Neutrality check passed."

# ── Bootstrap ─────────────────────────────────────────────
bootstrap-demo:
	bash scripts/bootstrap_public_demo.sh --profile demo

bootstrap-full:
	bash scripts/bootstrap_public_demo.sh --profile full

bootstrap-all:
	bash scripts/bootstrap_all_public.sh

bootstrap-all-noninteractive:
	bash scripts/bootstrap_all_public.sh --noninteractive --yes-reset

bootstrap-all-report:
	python3 scripts/run_bootstrap_all.py --repo-root . --report-latest

# ── Quality checks ────────────────────────────────────────
check-public-claims:
	python3 scripts/check_public_claims.py --repo-root .

check-source-urls:
	python3 scripts/check_source_urls.py --registry-path docs/source_registry_br_v1.csv --exceptions-path config/source_url_exceptions.yml --output audit-results/public-trust/latest/source-url-audit.json

check-pipeline-contracts:
	python3 scripts/check_pipeline_contracts.py

check-pipeline-inputs:
	python3 scripts/check_pipeline_inputs.py

# ── Generators ────────────────────────────────────────────
generate-pipeline-status:
	python3 scripts/generate_pipeline_status.py

generate-source-summary:
	python3 scripts/generate_data_sources_summary.py

generate-reference-metrics:
	python3 scripts/generate_reference_metrics.py

# ── Cleanup ─────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf frontend/dist
