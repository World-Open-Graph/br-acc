#!/usr/bin/env python3
"""Generate docs/pipeline_status.md from the source registry."""

from __future__ import annotations

import argparse
import csv
from datetime import UTC, datetime
from pathlib import Path


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def status_bucket(row: dict[str, str]) -> str:
    implementation_state = (row.get("implementation_state") or "").strip()
    status = (row.get("status") or "").strip()
    load_state = (row.get("load_state") or "").strip()

    if implementation_state != "implemented":
        return "not_built"
    if status == "blocked_external":
        return "blocked_external"
    if load_state == "loaded":
        return "implemented_loaded"
    return "implemented_partial"


def source_format(access_mode: str) -> str:
    mapping = {
        "api": "api_json",
        "file": "file_batch",
        "bigquery": "bigquery_table",
        "web": "web_portal",
    }
    return mapping.get(access_mode.strip(), "unknown")


def required_input(row: dict[str, str]) -> str:
    mode = (row.get("access_mode") or "").strip()
    pipeline_id = (row.get("pipeline_id") or row.get("source_id") or "").strip()

    if mode == "file":
        return f"data/{pipeline_id}/*"
    if mode == "api":
        return f"API payload from {row.get('primary_url', '').strip()}"
    if mode == "bigquery":
        return "BigQuery query/export result"
    if mode == "web":
        return f"Portal export/scrape output under data/{pipeline_id}/"
    return "source-specific contract required"


def known_blockers(row: dict[str, str]) -> str:
    status = (row.get("status") or "").strip()
    note = (row.get("notes") or "").strip()
    if status in {"loaded"}:
        return "-"
    return note or status or "-"


def escape_md(text: str) -> str:
    return text.replace("|", "\\|")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate pipeline status markdown")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--output", default="docs/pipeline_status.md")
    args = parser.parse_args()

    rows = list(csv.DictReader(Path(args.registry_path).open(encoding="utf-8", newline="")))
    rows = [row for row in rows if parse_bool(row.get("in_universe_v1", ""))]
    rows.sort(key=lambda row: (row.get("source_id") or ""))

    stamp = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    lines = [
        "# Pipeline Status",
        "",
        f"Generated from `docs/source_registry_br_v1.csv` (as-of UTC: {stamp}).",
        "",
        "Status buckets:",
        "- `implemented_loaded`: implemented and loaded in registry.",
        "- `implemented_partial`: implemented but partial/stale/not fully loaded.",
        "- `blocked_external`: implemented but externally blocked.",
        "- `not_built`: not implemented in public repo.",
        "",
        "| Source ID | Pipeline ID | Status Bucket | Load State | Source Format | Required Input | Known Blockers |",
        "|---|---|---|---|---|---|---|",
    ]

    for row in rows:
        src = (row.get("source_id") or "").strip()
        pipeline = (row.get("pipeline_id") or src).strip() or src
        bucket = status_bucket(row)
        load_state = (row.get("load_state") or "").strip() or "-"
        fmt = source_format((row.get("access_mode") or "").strip())
        req = required_input(row)
        blockers = known_blockers(row)

        lines.append(
            "| {src} | {pipeline} | {bucket} | {load_state} | {fmt} | {req} | {blockers} |".format(
                src=escape_md(src),
                pipeline=escape_md(pipeline),
                bucket=escape_md(bucket),
                load_state=escape_md(load_state),
                fmt=escape_md(fmt),
                req=escape_md(req),
                blockers=escape_md(blockers),
            )
        )

    Path(args.output).write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("UPDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
