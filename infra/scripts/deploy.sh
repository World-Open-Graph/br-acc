#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/bracc}"
COMPOSE_FILE="$DEPLOY_DIR/infra/docker-compose.prod.yml"
DRY_RUN=false

for arg in "$@"; do
    case $arg in
        --dry-run) DRY_RUN=true ;;
    esac
done

# DOMAIN required for real deploys (health check needs it)
if [ "$DRY_RUN" = false ] && [ -z "${DOMAIN:-}" ]; then
    echo "Error: DOMAIN env var required — set to your production domain" >&2
    exit 1
fi
DOMAIN="${DOMAIN:-localhost}"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Deploying BRACC..."

cd "$DEPLOY_DIR"

log "Pulling latest changes..."
if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Would run: git pull origin main"
else
    git pull origin main
fi

log "Building containers..."
if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Would run: docker compose build"
else
    docker compose -f "$COMPOSE_FILE" build
fi

log "Starting services..."
if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Would run: docker compose up -d"
else
    docker compose -f "$COMPOSE_FILE" up -d
fi

log "Waiting for health check..."
if [ "$DRY_RUN" = false ]; then
    sleep 15
    HEALTH_URL="https://${DOMAIN}/health"
    if curl -sf "$HEALTH_URL" > /dev/null 2>&1; then
        log "Health check passed ($HEALTH_URL)."
    else
        log "Health check failed ($HEALTH_URL)!"
        docker compose -f "$COMPOSE_FILE" logs --tail=50
        exit 1
    fi
fi

log "Deploy complete."
