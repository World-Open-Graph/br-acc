#!/usr/bin/env python3
"""Ensure implemented pipelines in registry match runnable ETL pipelines."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path

PIPELINE_ENTRY_RE = re.compile(r'^\s*"([a-z0-9_]+)":\s*[A-Za-z_][A-Za-z0-9_]*,\s*$')


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_registry_implemented(path: Path) -> set[str]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    implemented = {
        (row.get("pipeline_id") or "").strip()
        for row in rows
        if parse_bool(row.get("in_universe_v1", ""))
        and (row.get("implementation_state") or "").strip() == "implemented"
    }
    implemented.discard("")
    return implemented


def parse_runner_pipelines(path: Path) -> set[str]:
    pipelines: set[str] = set()
    inside = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("PIPELINES: dict[str, type] = {"):
            inside = True
            continue
        if inside and line.strip() == "}":
            break
        if inside:
            match = PIPELINE_ENTRY_RE.match(line)
            if match:
                pipelines.add(match.group(1))
    return pipelines


def main() -> int:
    parser = argparse.ArgumentParser(description="Check implemented pipeline contracts")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--runner-path", default="etl/src/bracc_etl/runner.py")
    args = parser.parse_args()

    implemented = parse_registry_implemented(Path(args.registry_path))
    runner = parse_runner_pipelines(Path(args.runner_path))

    missing = sorted(implemented - runner)
    extra = sorted(runner - implemented)

    print(f"implemented={len(implemented)} runner={len(runner)}")

    if missing or extra:
        print("FAIL")
        if missing:
            print(f"- implemented_not_in_runner={missing}")
        if extra:
            print(f"- runner_not_marked_implemented={extra}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
