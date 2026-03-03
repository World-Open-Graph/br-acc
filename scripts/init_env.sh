#!/usr/bin/env bash
set -euo pipefail

# Directories relative to the script location
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up one level from scripts/ to get the root
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_EXAMPLE="$ROOT_DIR/.env.example"
ENV_FILE="$ROOT_DIR/.env"

# Check for required dependencies
if ! command -v openssl &> /dev/null; then
    echo "Error: 'openssl' is required but not installed."
    exit 1
fi

if [ -f "$ENV_FILE" ]; then
    echo "⚠️  $ENV_FILE already exists."
    # Use /dev/tty to ensure input comes from user even inside make
    read -p "Do you want to overwrite it? (y/N) " -n 1 -r < /dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Aborted."
        exit 1
    fi
fi

echo "Generating secure secrets..."
# Generate secure hex secrets
# JWT: 32 bytes (64 hex chars) - Meets the >= 32 chars requirement
JWT_SECRET=$(openssl rand -hex 32)
# Neo4j: 32 bytes (64 hex chars) - Strong database password
NEO4J_PASS=$(openssl rand -hex 32)

echo "Creating .env from .env.example..."

# Use sed to replace placeholders
# We use | as a delimiter to avoid conflicts
# We need to escape the values just in case, though hex shouldn't have special chars
# Since we are generating hex, basic sed substitution is safe

# Create temp file first to avoid partial writes
TEMP_ENV=$(mktemp)

# Read .env.example and perform replacements
sed -e "s|JWT_SECRET_KEY=change-me-generate-with-openssl-rand-hex-32|JWT_SECRET_KEY=${JWT_SECRET}|g" \
    -e "s|NEO4J_PASSWORD=changeme|NEO4J_PASSWORD=${NEO4J_PASS}|g" \
    "$ENV_EXAMPLE" > "$TEMP_ENV"

mv "$TEMP_ENV" "$ENV_FILE"

# Restrict permissions (read/write for owner only)
chmod 600 "$ENV_FILE"

echo "✅ .env created successfully with secure secrets."
echo "   JWT_SECRET_KEY:  [GENERATED] (64 chars)"
echo "   NEO4J_PASSWORD:  [GENERATED] (64 chars)"
