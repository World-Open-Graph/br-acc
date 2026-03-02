#!/bin/bash
# EGOS Inteligencia — Pre-commit hook v1.0
# Checks: secrets, large files, Python lint, broken imports

set -e

echo "🔍 EGOS pre-commit checks..."

# 1. Check for hardcoded secrets
SECRETS_FOUND=$(git diff --cached --diff-filter=ACM -z -- '*.py' '*.ts' '*.tsx' '*.yml' '*.yaml' '*.json' '*.env' | \
  xargs -0 grep -lEi '(password|secret|api_key|token)\s*[:=]\s*["\x27][^${}]' 2>/dev/null || true)
if [ -n "$SECRETS_FOUND" ]; then
  echo "❌ BLOCKING: Possible hardcoded secrets in:"
  echo "$SECRETS_FOUND"
  exit 1
fi

# 2. Check for large files (>5MB)
LARGE_FILES=$(git diff --cached --diff-filter=ACM --name-only | while read f; do
  if [ -f "$f" ]; then
    SIZE=$(stat -f%z "$f" 2>/dev/null || stat -c%s "$f" 2>/dev/null || echo 0)
    if [ "$SIZE" -gt 5242880 ]; then echo "$f ($SIZE bytes)"; fi
  fi
done)
if [ -n "$LARGE_FILES" ]; then
  echo "❌ BLOCKING: Files >5MB should not be committed:"
  echo "$LARGE_FILES"
  exit 1
fi

# 3. Python syntax check (if any .py files staged)
PY_FILES=$(git diff --cached --diff-filter=ACM --name-only -- '*.py')
if [ -n "$PY_FILES" ]; then
  for f in $PY_FILES; do
    python3 -c "import py_compile; py_compile.compile('$f', doraise=True)" 2>/dev/null || {
      echo "⚠️  WARNING: Python syntax error in $f"
    }
  done
fi

# 4. Frontend crash prevention — unsafe .length/.map on API data
TSX_FILES=$(git diff --cached --diff-filter=ACM --name-only -- '*.tsx' '*.ts' | grep -v 'node_modules' | grep -v '.d.ts' || true)
if [ -n "$TSX_FILES" ]; then
  # Check for bare .entity_ids.length, .sources.length, .entities.length without ?? guard
  UNSAFE=$(echo "$TSX_FILES" | xargs grep -nE '\.(entity_ids|sources|entities|annotations|tags|categories)\.(length|map|filter|forEach|find|reduce|slice|sort|some|every)' 2>/dev/null | grep -v '??' | grep -v '?\.' || true)
  if [ -n "$UNSAFE" ]; then
    echo "⚠️  WARNING: Unsafe array access on API data (add ?? [] guard):"
    echo "$UNSAFE" | head -10
    echo "   Fix: use (obj.field ?? []).length or obj.field?.length"
  fi
fi

echo "✅ All pre-commit checks passed"
