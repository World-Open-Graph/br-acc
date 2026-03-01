#!/usr/bin/env python3
"""Create Linear audit issues for AI PR governance decisions."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


def read_json(path: str) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def compact(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def build_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "## AI PR Governor Audit",
        "",
        f"- **Decision**: `{compact(payload.get('decision'))}`",
        f"- **Repository**: `{compact(payload.get('repository'))}`",
        f"- **PR**: {compact(payload.get('pr_url'))}",
        f"- **PR Number**: `{compact(payload.get('pr_number'))}`",
        f"- **Author**: `{compact(payload.get('author'))}`",
        f"- **Head Branch**: `{compact(payload.get('head_ref'))}`",
        f"- **Head SHA**: `{compact(payload.get('head_sha'))}`",
        f"- **Base Branch**: `{compact(payload.get('base_ref'))}`",
        f"- **Checks Status**: `{compact(payload.get('checks_status'))}`",
        f"- **Claude Confidence**: `{compact(payload.get('confidence'))}`",
        f"- **Claude Risk Level**: `{compact(payload.get('risk_level'))}`",
        f"- **Claude Cost (USD)**: `{compact(payload.get('claude_cost_usd'))}`",
        f"- **Workflow Run**: {compact(payload.get('workflow_run_url'))}",
        "",
        "### Summary",
        compact(payload.get("summary")) or "n/a",
        "",
        "### Blocking Findings",
    ]

    findings = payload.get("blocking_findings")
    if isinstance(findings, list) and findings:
        lines.extend([f"- {compact(item)}" for item in findings])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "### Gate Reasons",
        ]
    )
    reasons = payload.get("gate_reasons")
    if isinstance(reasons, list) and reasons:
        lines.extend([f"- {compact(item)}" for item in reasons])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "### Raw Evidence",
            "```json",
            json.dumps(payload, indent=2, ensure_ascii=False),
            "```",
        ]
    )

    return "\n".join(lines)


def linear_issue_create(api_key: str, team_id: str, title: str, description: str, api_url: str) -> dict[str, Any]:
    query = """
mutation IssueCreate($input: IssueCreateInput!) {
  issueCreate(input: $input) {
    success
    issue {
      id
      identifier
      title
      url
    }
  }
}
""".strip()

    variables = {
        "input": {
            "teamId": team_id,
            "title": title,
            "description": description,
        }
    }

    req_body = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=req_body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Authorization": api_key,
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Linear API HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Linear API connection error: {exc}") from exc

    if payload.get("errors"):
        raise RuntimeError(f"Linear GraphQL errors: {json.dumps(payload['errors'], ensure_ascii=False)}")

    result = (((payload.get("data") or {}).get("issueCreate") or {}))
    if not result.get("success"):
        raise RuntimeError("Linear issueCreate returned success=false")

    issue = result.get("issue") or {}
    return {
        "id": issue.get("id"),
        "identifier": issue.get("identifier"),
        "title": issue.get("title"),
        "url": issue.get("url"),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create Linear audit issue for AI PR governor decision.")
    parser.add_argument("--input-json", required=True, help="Path to decision payload JSON.")
    parser.add_argument("--team-id", help="Linear team ID (fallback: LINEAR_TEAM_ID env).")
    parser.add_argument("--api-url", default="https://api.linear.app/graphql")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--output", help="Optional output JSON path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    payload = read_json(args.input_json)

    team_id = args.team_id or os.environ.get("LINEAR_TEAM_ID")
    api_key = os.environ.get("LINEAR_API_KEY")

    pr_number = payload.get("pr_number", "unknown")
    decision = payload.get("decision", "unknown")
    title = f"[AI Governor] PR #{pr_number} {decision}"
    description = build_markdown(payload)

    result: dict[str, Any]
    if args.dry_run:
        result = {
            "dry_run": True,
            "title": title,
            "team_id": team_id,
            "api_url": args.api_url,
        }
    else:
        if not api_key:
            print("LINEAR_API_KEY not set", file=sys.stderr)
            return 2
        if not team_id:
            print("Linear team id missing (--team-id or LINEAR_TEAM_ID)", file=sys.stderr)
            return 2

        created = linear_issue_create(
            api_key=api_key,
            team_id=team_id,
            title=title,
            description=description,
            api_url=args.api_url,
        )
        result = {
            "dry_run": False,
            "created": created,
        }

    out = json.dumps(result, indent=2, ensure_ascii=False)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(out + "\n", encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
