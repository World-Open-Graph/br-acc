COMPOSE = docker compose -f infra/docker-compose.yml --env-file .env

.PHONY: dev down logs seed check neutrality

dev:
	$(COMPOSE) up -d --build

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f

seed:
	set -a && . ./.env && set +a && bash infra/scripts/seed-dev.sh

check:
	cd api && bash ../scripts/ci/python_quality.sh
	cd etl && bash ../scripts/ci/python_quality.sh
	cd frontend && bash ../scripts/ci/frontend_quality.sh

neutrality:
	@! grep -rn \
		"suspicious\|corrupt\|criminal\|fraudulent\|illegal\|guilty" \
		api/src/ etl/src/ frontend/src/ \
		--include="*.py" --include="*.ts" --include="*.tsx" --include="*.json" \
		|| (echo "NEUTRALITY VIOLATION: banned words found in source" && exit 1)
