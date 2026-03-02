#!/usr/bin/env bash
# Seed Neo4j with development fixture data
# Usage: bash infra/scripts/seed-dev.sh
# Requires: Neo4j running on bolt://localhost:7687

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CYPHER_FILE="${SCRIPT_DIR}/seed-dev.cypher"
NEO4J_URI="${NEO4J_URI:-bolt://localhost:7687}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:?NEO4J_PASSWORD must be set}"

echo "Seeding Neo4j at ${NEO4J_URI}..."

export NEO4J_PASSWORD

if command -v cypher-shell &>/dev/null; then
  cypher-shell \
    -a "${NEO4J_URI}" \
    -u "${NEO4J_USER}" \
    --env NEO4J_PASSWORD \
    -f "${CYPHER_FILE}"
elif command -v docker &>/dev/null; then
  docker exec -i -e NEO4J_PASSWORD="${NEO4J_PASSWORD}" bracc-neo4j cypher-shell \
    -u "${NEO4J_USER}" \
    --env NEO4J_PASSWORD \
    < "${CYPHER_FILE}"
else
  echo "Error: cypher-shell not found and docker not available."
  echo "Install cypher-shell or run 'docker compose up -d' first."
  exit 1
fi

echo "Seed data loaded successfully."
