#!/usr/bin/env python3
"""Validate that implemented pipelines have documented input contracts."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

VALID_STATUS_BUCKETS = {
    "implemented_loaded",
    "implemented_partial",
    "blocked_external",
    "not_built",
}

VALID_SOURCE_FORMATS = {
    "api_json",
    "file_batch",
    "bigquery_table",
    "web_portal",
    "unknown",
}


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_implemented_pipeline_ids(registry_path: Path) -> set[str]:
    rows = list(csv.DictReader(registry_path.open(encoding="utf-8", newline="")))
    pipeline_ids = {
        (row.get("pipeline_id") or "").strip()
        for row in rows
        if parse_bool(row.get("in_universe_v1", ""))
        and (row.get("implementation_state") or "").strip() == "implemented"
    }
    pipeline_ids.discard("")
    return pipeline_ids


def parse_status_table(status_doc: Path) -> dict[str, dict[str, str]]:
    table_rows: dict[str, dict[str, str]] = {}
    for raw in status_doc.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|---") or "Pipeline ID" in line:
            continue
        cols = [col.strip() for col in line.strip("|").split("|")]
        if len(cols) < 7:
            continue
        pipeline_id = cols[1]
        table_rows[pipeline_id] = {
            "source_id": cols[0],
            "pipeline_id": cols[1],
            "status_bucket": cols[2],
            "load_state": cols[3],
            "source_format": cols[4],
            "required_input": cols[5],
            "known_blockers": cols[6],
        }
    return table_rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Check pipeline input contracts")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--status-doc", default="docs/pipeline_status.md")
    args = parser.parse_args()

    implemented = parse_implemented_pipeline_ids(Path(args.registry_path))
    table = parse_status_table(Path(args.status_doc))

    errors: list[str] = []

    for pipeline_id in sorted(implemented):
        row = table.get(pipeline_id)
        if not row:
            errors.append(f"missing pipeline in docs/pipeline_status.md: {pipeline_id}")
            continue

        status_bucket = row["status_bucket"].strip()
        source_format = row["source_format"].strip()
        required_input = row["required_input"].strip()

        if status_bucket not in VALID_STATUS_BUCKETS:
            errors.append(f"invalid status bucket for {pipeline_id}: {status_bucket}")
        if source_format not in VALID_SOURCE_FORMATS:
            errors.append(f"invalid source format for {pipeline_id}: {source_format}")
        if not required_input or required_input == "-":
            errors.append(f"missing required input contract for {pipeline_id}")

    if errors:
        print("FAIL")
        for err in errors:
            print(f"- {err}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
