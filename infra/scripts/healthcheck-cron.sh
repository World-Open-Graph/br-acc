#!/usr/bin/env bash
set -euo pipefail

# Simple uptime monitor — checks /health every 5 minutes via cron.
# On failure, sends alert via webhook (configure ALERT_WEBHOOK_URL).
# Usage: sudo bash infra/scripts/healthcheck-cron.sh

DEPLOY_DIR="${DEPLOY_DIR:-/opt/bracc}"
HEALTH_SCRIPT="${DEPLOY_DIR}/infra/scripts/_healthcheck.sh"
CRON_ENTRY="*/5 * * * * ${HEALTH_SCRIPT} >> /var/log/bracc-health.log 2>&1"

# Create the actual health check script
cat > "$HEALTH_SCRIPT" << 'SCRIPT'
#!/usr/bin/env bash
DOMAIN="${DOMAIN:-localhost}"
ALERT_WEBHOOK_URL="${ALERT_WEBHOOK_URL:-}"
HEALTH_URL="https://${DOMAIN}/health"

if curl -sf -k --max-time 10 "$HEALTH_URL" > /dev/null 2>&1; then
    exit 0
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Health check failed: $HEALTH_URL"

if [ -n "$ALERT_WEBHOOK_URL" ]; then
    curl -sf -X POST "$ALERT_WEBHOOK_URL" \
        -H "Content-Type: application/json" \
        -d "{\"text\":\"BR-ACC health check failed at $(date '+%Y-%m-%d %H:%M:%S') — ${HEALTH_URL}\"}" \
        > /dev/null 2>&1 || true
fi
SCRIPT
chmod +x "$HEALTH_SCRIPT"

if crontab -l 2>/dev/null | grep -qF "_healthcheck.sh"; then
    echo "Health check cron already installed."
    exit 0
fi

(crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
echo "Installed health check cron (every 5 min)."
echo "Set ALERT_WEBHOOK_URL env var for notifications."
echo "Logs: /var/log/bracc-health.log"
