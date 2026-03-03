#!/usr/bin/env bash
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/bracc}"
COMPOSE_BASE="$DEPLOY_DIR/infra/docker-compose.prod.yml"
# When USE_GHCR_IMAGES=true, use override that pulls images from GHCR (set REGISTRY_IMAGE_PREFIX and optional REGISTRY_IMAGE_TAG)
if [ "${USE_GHCR_IMAGES:-false}" = "true" ]; then
  COMPOSE_FILE="${COMPOSE_BASE}:${DEPLOY_DIR}/infra/docker-compose.prod.images.yml"
else
  COMPOSE_FILE="$COMPOSE_BASE"
fi
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

log "Deploying BR-ACC..."

cd "$DEPLOY_DIR"

if [ "${USE_GHCR_IMAGES:-false}" = "true" ]; then
  if [ -z "${REGISTRY_IMAGE_PREFIX:-}" ]; then
    echo "Error: REGISTRY_IMAGE_PREFIX required when USE_GHCR_IMAGES=true (e.g. ghcr.io/owner/br-acc)" >&2
    exit 1
  fi
  REGISTRY_IMAGE_TAG="${REGISTRY_IMAGE_TAG:-latest}"
  export REGISTRY_IMAGE_PREFIX REGISTRY_IMAGE_TAG
  log "Using GHCR images: ${REGISTRY_IMAGE_PREFIX}_api:${REGISTRY_IMAGE_TAG} (and frontend)"
  log "Logging in to GHCR..."
  if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Would run: echo \$GHCR_TOKEN | docker login ghcr.io -u USER --password-stdin"
  else
    echo "${GHCR_TOKEN:?Set GHCR_TOKEN for GHCR login}" | docker login ghcr.io -u "${GHCR_USER:?Set GHCR_USER for GHCR login}" --password-stdin
  fi
  log "Pulling images..."
  if [ "$DRY_RUN" = true ]; then
    log "[DRY RUN] Would run: docker compose pull"
  else
    docker compose -f "$COMPOSE_BASE" -f "$DEPLOY_DIR/infra/docker-compose.prod.images.yml" pull api frontend
  fi
else
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
fi

log "Starting services..."
if [ "$DRY_RUN" = true ]; then
  log "[DRY RUN] Would run: docker compose up -d"
else
  if [ "${USE_GHCR_IMAGES:-false}" = "true" ]; then
    docker compose -f "$COMPOSE_BASE" -f "$DEPLOY_DIR/infra/docker-compose.prod.images.yml" up -d
  else
    docker compose -f "$COMPOSE_FILE" up -d
  fi
fi

log "Waiting for health check..."
if [ "$DRY_RUN" = false ]; then
    sleep 15
    HEALTH_URL="https://${DOMAIN}/health"
    if curl -sf -k "$HEALTH_URL" > /dev/null 2>&1; then
        log "Health check passed ($HEALTH_URL)."
    else
        log "Health check failed ($HEALTH_URL)!"
        if [ "${USE_GHCR_IMAGES:-false}" = "true" ]; then
          docker compose -f "$COMPOSE_BASE" -f "$DEPLOY_DIR/infra/docker-compose.prod.images.yml" logs --tail=50
        else
          docker compose -f "$COMPOSE_FILE" logs --tail=50
        fi
        exit 1
    fi
fi

log "Deploy complete."
