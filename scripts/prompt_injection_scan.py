#!/usr/bin/env python3
"""Conservative prompt-injection scanner for PR textual surfaces.

This scanner intentionally favors recall over precision for suspicious patterns
that often appear in prompt-injection attempts. It is used as a preflight gate
before any automated approve/merge action.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Rule:
    name: str
    pattern: re.Pattern[str]
    severity: str
    description: str


RULES: tuple[Rule, ...] = (
    Rule(
        name="override_system_instructions",
        pattern=re.compile(
            r"(?is)\b(ignore|disregard|forget|override)\b.{0,100}\b"
            r"(system\s*prompt|developer\s*message|instructions?|polic(y|ies)|guardrails?)\b"
        ),
        severity="high",
        description="Attempts to override system/developer instructions.",
    ),
    Rule(
        name="hidden_instruction_markers",
        pattern=re.compile(r"(?is)(<!--|-->|\[\[INTERNAL\]\]|BEGIN_(SYSTEM|PROMPT)|END_(SYSTEM|PROMPT))"),
        severity="high",
        description="Hidden marker often used to smuggle instructions.",
    ),
    Rule(
        name="secrecy_bypass_language",
        pattern=re.compile(r"(?is)\b(do\s*not\s*tell|without\s*mentioning|silently|secretly|hidden\s*instructions?)\b"),
        severity="high",
        description="Language instructing hidden behavior.",
    ),
    Rule(
        name="credential_or_exfil_terms",
        pattern=re.compile(r"(?is)\b(exfiltrat(e|ion)|secret(s)?|token(s)?|credential(s)?|api\s*key)\b"),
        severity="medium",
        description="Credential/exfiltration language.",
    ),
    Rule(
        name="network_fetch_commands",
        pattern=re.compile(r"(?is)\b(curl|wget)\b\s+https?://"),
        severity="medium",
        description="Network command included in user-controlled content.",
    ),
    Rule(
        name="obfuscation_terms",
        pattern=re.compile(r"(?is)\b(base64|rot13|encoded|decode\s*this|unicode\s*escape)\b"),
        severity="medium",
        description="Potential obfuscation to bypass screening.",
    ),
    Rule(
        name="zero_width_chars",
        pattern=re.compile(r"[\u200B-\u200F\u2060\uFEFF]"),
        severity="medium",
        description="Zero-width characters can hide instructions.",
    ),
)

SEVERITY_WEIGHT = {"high": 3, "medium": 1}
MAX_PER_RULE_PER_SOURCE = 5


def read_text(path: str | None) -> str:
    if not path:
        return ""
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def snippet(text: str, start: int, end: int, max_len: int = 180) -> str:
    left = max(0, start - 50)
    right = min(len(text), end + 120)
    raw = text[left:right].replace("\n", " ").replace("\r", " ")
    compact = re.sub(r"\s+", " ", raw).strip()
    if len(compact) <= max_len:
        return compact
    return compact[: max_len - 3] + "..."


def scan_source(source_name: str, text: str, max_findings: int) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not text:
        return findings

    for rule in RULES:
        hits = 0
        for match in rule.pattern.finditer(text):
            findings.append(
                {
                    "source": source_name,
                    "rule": rule.name,
                    "severity": rule.severity,
                    "description": rule.description,
                    "snippet": snippet(text, match.start(), match.end()),
                }
            )
            hits += 1
            if hits >= MAX_PER_RULE_PER_SOURCE:
                break
            if len(findings) >= max_findings:
                return findings
    return findings


def build_result(findings: list[dict[str, Any]], sources: dict[str, str]) -> dict[str, Any]:
    high = sum(1 for f in findings if f["severity"] == "high")
    medium = sum(1 for f in findings if f["severity"] == "medium")
    score = sum(SEVERITY_WEIGHT.get(f["severity"], 0) for f in findings)

    suspicious = high > 0 or score >= 4

    return {
        "scanner_version": "1.0",
        "suspicious": suspicious,
        "score": score,
        "high_findings": high,
        "medium_findings": medium,
        "source_sizes": {k: len(v) for k, v in sources.items()},
        "findings": findings,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan PR textual content for prompt-injection indicators.")
    parser.add_argument("--title-file", help="Path to file containing PR title text.")
    parser.add_argument("--body-file", help="Path to file containing PR body text.")
    parser.add_argument("--comments-file", help="Path to file containing PR comments text.")
    parser.add_argument("--diff-file", help="Path to file containing PR diff text.")
    parser.add_argument("--max-findings", type=int, default=80)
    parser.add_argument("--output", help="Optional output JSON file path.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    sources = {
        "title": read_text(args.title_file),
        "body": read_text(args.body_file),
        "comments": read_text(args.comments_file),
        "diff": read_text(args.diff_file),
    }

    findings: list[dict[str, Any]] = []
    for source_name, text in sources.items():
        if len(findings) >= args.max_findings:
            break
        findings.extend(scan_source(source_name, text, args.max_findings - len(findings)))

    result = build_result(findings, sources)
    payload = json.dumps(result, indent=2, ensure_ascii=True)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
