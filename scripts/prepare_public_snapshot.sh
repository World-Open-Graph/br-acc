#!/usr/bin/env bash
set -euo pipefail

SRC_ROOT="${1:-$(pwd)}"
OUT_DIR="${2:-/tmp/world-transparency-graph-public-$(date +%Y%m%d_%H%M%S)}"

mkdir -p "$OUT_DIR"

rsync -a \
  --exclude='**/.venv/***' \
  --exclude='**/__pycache__/***' \
  --exclude='**/.pytest_cache/***' \
  --exclude='**/.mypy_cache/***' \
  --exclude='**/.ruff_cache/***' \
  --exclude='frontend/node_modules/***' \
  --exclude='etl/data/***' \
  --exclude='**/dist/***' \
  --exclude='**/build/***' \
  --exclude='**/*.pyc' \
  --exclude='.env' \
  --exclude='api/.env' \
  --exclude='etl/.env' \
  --exclude='frontend/.env' \
  --include='api/' \
  --include='api/***' \
  --include='etl/' \
  --include='etl/***' \
  --include='frontend/' \
  --include='frontend/***' \
  --include='infra/' \
  --include='infra/***' \
  --include='docs/' \
  --include='docs/brand/' \
  --include='docs/brand/wtg-header.png' \
  --include='docs/demo/' \
  --include='docs/demo/***' \
  --include='docs/legal/' \
  --include='docs/legal/***' \
  --include='docs/release/' \
  --include='docs/release/public_boundary_matrix.csv' \
  --include='docs/release/public_endpoint_matrix.md' \
  --include='docs/release/public_repo_release_checklist.md' \
  --include='docs/data-sources.md' \
  --include='docs/source_registry_br_v1.csv' \
  --include='docs/source_onboarding_contract.md' \
  --include='.github/' \
  --include='.github/***' \
  --include='scripts/' \
  --include='scripts/check_public_privacy.py' \
  --include='scripts/check_compliance_pack.py' \
  --include='scripts/check_open_core_boundary.py' \
  --include='scripts/generate_demo_dataset.py' \
  --include='scripts/prepare_public_snapshot.sh' \
  --include='data/' \
  --include='data/demo/' \
  --include='data/demo/***' \
  --include='README.md' \
  --include='ETHICS.md' \
  --include='LGPD.md' \
  --include='PRIVACY.md' \
  --include='TERMS.md' \
  --include='DISCLAIMER.md' \
  --include='SECURITY.md' \
  --include='ABUSE_RESPONSE.md' \
  --include='LICENSE' \
  --include='.env.example' \
  --include='.gitignore' \
  --include='.gitleaksignore' \
  --exclude='*' \
  "$SRC_ROOT/" "$OUT_DIR/"

# Explicit removals for sensitive operational artifacts and disabled pattern engine.
rm -f "$OUT_DIR/CLAUDE.md"
rm -f "$OUT_DIR/.mcp.json"
rm -f "$OUT_DIR/docs/shadow_rollout_runbook.md"
rm -f "$OUT_DIR/docs/ingestion_priority_runbook.md"
rm -f "$OUT_DIR/docs/ops/storage_operations.md"
rm -f "$OUT_DIR/scripts/auto_finalize_pncp_backfill.sh"
rm -f "$OUT_DIR/api/src/icarus/services/pattern_service.py"
rm -f "$OUT_DIR/api/src/icarus/queries/pattern_"*.cypher
rm -f "$OUT_DIR/api/tests/unit/test_patterns.py"
rm -f "$OUT_DIR/api/tests/unit/test_patterns_new.py"

rm -rf "$OUT_DIR/audit-results"

python3 "$OUT_DIR/scripts/generate_demo_dataset.py" --output "$OUT_DIR/data/demo/synthetic_graph.json" >/dev/null
python3 "$OUT_DIR/scripts/check_public_privacy.py" --repo-root "$OUT_DIR"
python3 "$OUT_DIR/scripts/check_compliance_pack.py" --repo-root "$OUT_DIR"
python3 "$OUT_DIR/scripts/check_open_core_boundary.py" --repo-root "$OUT_DIR"

printf 'Public snapshot prepared at: %s\n' "$OUT_DIR"
