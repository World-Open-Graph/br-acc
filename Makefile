.PHONY: dev stop seed bootstrap-demo bootstrap-full bootstrap-all bootstrap-all-noninteractive bootstrap-all-report check-public-claims check-source-urls check-pipeline-contracts check-pipeline-inputs generate-pipeline-status generate-source-summary generate-reference-metrics

dev:
	docker compose -f infra/docker-compose.yml up -d

stop:
	docker compose -f infra/docker-compose.yml down

seed:
	bash infra/scripts/seed-dev.sh

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

check-public-claims:
	python3 scripts/check_public_claims.py --repo-root .

check-source-urls:
	python3 scripts/check_source_urls.py --registry-path docs/source_registry_br_v1.csv --exceptions-path config/source_url_exceptions.yml --output audit-results/public-trust/latest/source-url-audit.json

check-pipeline-contracts:
	python3 scripts/check_pipeline_contracts.py

check-pipeline-inputs:
	python3 scripts/check_pipeline_inputs.py

generate-pipeline-status:
	python3 scripts/generate_pipeline_status.py --registry-path docs/source_registry_br_v1.csv --output docs/pipeline_status.md

generate-source-summary:
	python3 scripts/generate_data_sources_summary.py --registry-path docs/source_registry_br_v1.csv --docs-path docs/data-sources.md

generate-reference-metrics:
	python3 scripts/generate_reference_metrics.py --json-output audit-results/public-trust/latest/neo4j-reference-metrics.json --doc-output docs/reference_metrics.md
