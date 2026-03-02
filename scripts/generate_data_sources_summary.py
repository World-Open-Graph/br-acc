#!/usr/bin/env python3
"""Generate the summary block in docs/data-sources.md from source registry CSV."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

START_MARKER = "<!-- SOURCE_SUMMARY_START -->"
END_MARKER = "<!-- SOURCE_SUMMARY_END -->"


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def compute_counts(registry_path: Path) -> dict[str, int]:
    rows = list(csv.DictReader(registry_path.open(encoding="utf-8", newline="")))
    universe = [row for row in rows if parse_bool(row.get("in_universe_v1", ""))]

    status = Counter((row.get("status") or "").strip() for row in universe)
    load_state = Counter((row.get("load_state") or "").strip() for row in universe)
    implemented = [row for row in universe if (row.get("implementation_state") or "").strip() == "implemented"]

    return {
        "universe": len(universe),
        "implemented": len(implemented),
        "loaded": load_state.get("loaded", 0),
        "partial_load": load_state.get("partial", 0),
        "not_loaded": load_state.get("not_loaded", 0),
        "status_loaded": status.get("loaded", 0),
        "status_partial": status.get("partial", 0),
        "status_stale": status.get("stale", 0),
        "status_blocked_external": status.get("blocked_external", 0),
        "status_not_built": status.get("not_built", 0),
    }


def render_block(counts: dict[str, int], stamp_utc: str) -> str:
    return "\n".join(
        [
            START_MARKER,
            f"**Generated from `docs/source_registry_br_v1.csv` (as-of UTC: {stamp_utc})**",
            "",
            f"- Universe v1 sources: {counts['universe']}",
            f"- Implemented pipelines: {counts['implemented']}",
            f"- Loaded sources (load_state=loaded): {counts['loaded']}",
            f"- Partial sources (load_state=partial): {counts['partial_load']}",
            f"- Not loaded sources (load_state=not_loaded): {counts['not_loaded']}",
            (
                "- Status counts: "
                f"loaded={counts['status_loaded']}, "
                f"partial={counts['status_partial']}, "
                f"stale={counts['status_stale']}, "
                f"blocked_external={counts['status_blocked_external']}, "
                f"not_built={counts['status_not_built']}"
            ),
            END_MARKER,
        ]
    )


def replace_block(doc_text: str, block: str) -> str:
    if START_MARKER in doc_text and END_MARKER in doc_text:
        start = doc_text.index(START_MARKER)
        end = doc_text.index(END_MARKER) + len(END_MARKER)
        return doc_text[:start] + block + doc_text[end:]

    lines = doc_text.splitlines()
    insertion_idx = 1 if len(lines) > 1 else len(lines)
    out = lines[:insertion_idx] + ["", block, ""] + lines[insertion_idx:]
    return "\n".join(out) + ("\n" if doc_text.endswith("\n") else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate summary block in docs/data-sources.md")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--docs-path", default="docs/data-sources.md")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--stamp-utc", default="")
    args = parser.parse_args()

    registry_path = Path(args.registry_path)
    docs_path = Path(args.docs_path)
    doc_text = docs_path.read_text(encoding="utf-8")
    existing_stamp_match = re.search(r"as-of UTC:\s*([0-9T:\-]+Z)", doc_text)
    existing_stamp = existing_stamp_match.group(1) if existing_stamp_match else ""
    stamp = args.stamp_utc or (existing_stamp if args.check else datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"))

    counts = compute_counts(registry_path)
    expected_block = render_block(counts, stamp)
    rendered = replace_block(doc_text, expected_block)

    if args.check:
        if rendered != doc_text:
            print("FAIL")
            print("- docs/data-sources.md summary block is out of date")
            return 1
        print("PASS")
        return 0

    docs_path.write_text(rendered, encoding="utf-8")
    print("UPDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
