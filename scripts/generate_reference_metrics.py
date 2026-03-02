#!/usr/bin/env python3
"""Generate reference metrics documentation and JSON snapshot."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate reference metrics docs/json")
    parser.add_argument("--node-count", type=int, default=219430848)
    parser.add_argument("--relationship-count", type=int, default=97451843)
    parser.add_argument("--as-of-utc", default="2026-03-01T23:05:00Z")
    parser.add_argument("--json-output", default="audit-results/public-trust/latest/neo4j-reference-metrics.json")
    parser.add_argument("--doc-output", default="docs/reference_metrics.md")
    args = parser.parse_args()

    json_path = Path(args.json_output)
    json_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "as_of_utc": args.as_of_utc,
        "dataset_scope": "reference_production_snapshot",
        "queries": {
            "node_count": "MATCH (n) RETURN count(n) AS node_count",
            "relationship_count": "MATCH ()-[r]->() RETURN count(r) AS relationship_count",
        },
        "metrics": {
            "node_count": args.node_count,
            "relationship_count": args.relationship_count,
        },
        "notes": [
            "Reference production snapshot metrics.",
            "Not expected from fresh local bootstrap or demo seed data.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    doc = "\n".join(
        [
            "# Reference Metrics",
            "",
            "This document tracks **reference production snapshot** metrics for transparency.",
            "",
            f"- dataset_scope: `reference_production_snapshot`",
            f"- as_of_utc: `{args.as_of_utc}`",
            f"- node_count: `{args.node_count}`",
            f"- relationship_count: `{args.relationship_count}`",
            "",
            "These numbers are not the expected output of `make bootstrap-demo`.",
            "",
            "## Provenance Queries",
            "",
            "```cypher",
            "MATCH (n) RETURN count(n) AS node_count;",
            "MATCH ()-[r]->() RETURN count(r) AS relationship_count;",
            "```",
        ]
    )
    Path(args.doc_output).write_text(doc + "\n", encoding="utf-8")

    print("UPDATED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
