#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

echo "bootstrap-all runs full historical ingestion and may take many hours with high disk/network usage."

exec uv run python "${REPO_ROOT}/scripts/run_bootstrap_all.py" --repo-root "${REPO_ROOT}" "$@"
