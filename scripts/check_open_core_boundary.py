#!/usr/bin/env python3
"""Validate public edition scope and language rules."""

from __future__ import annotations

import argparse
from pathlib import Path

FORBIDDEN_PATH_GLOBS = (
    "api/src/icarus/services/pattern_service.py",
    "api/src/icarus/queries/pattern_*.cypher",
    "scripts/auto_finalize_pncp_backfill.sh",
    "docs/shadow_rollout_runbook.md",
    "docs/ingestion_priority_runbook.md",
    "docs/ops/storage_operations.md",
    "CLAUDE.md",
    ".mcp.json",
)

FORBIDDEN_IMPORT_TOKENS = (
    "from icarus.services.pattern_service import",
)

PUBLIC_SURFACE_GLOBS = (
    "api/src/icarus/routers/*.py",
    "api/src/icarus/main.py",
)

def check_forbidden_paths(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for pattern in FORBIDDEN_PATH_GLOBS:
        for path in repo_root.glob(pattern):
            if path.is_file():
                rel = path.relative_to(repo_root)
                errors.append(f"forbidden file present in public tree: {rel}")
    return errors


def check_forbidden_imports(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for pattern in PUBLIC_SURFACE_GLOBS:
        for path in sorted(repo_root.glob(pattern)):
            if not path.is_file():
                continue
            content = path.read_text(encoding="utf-8")
            for token in FORBIDDEN_IMPORT_TOKENS:
                if token in content:
                    rel = path.relative_to(repo_root)
                    errors.append(f"forbidden import token in {rel}: {token}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate public edition scope")
    parser.add_argument("--repo-root", default=".", help="Path to repository root")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    errors = [
        *check_forbidden_paths(repo_root),
        *check_forbidden_imports(repo_root),
    ]
    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
