#!/usr/bin/env python3
"""Deterministic policy gate for AI PR governance.

This script converts policy + PR metadata + scanner/evaluation/check outputs into
an objective merge eligibility decision. The LLM is advisory; this gate is final.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Decision:
    eligible: bool
    decision: str
    reasons: list[str]
    metrics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "eligible": self.eligible,
            "decision": self.decision,
            "reasons": self.reasons,
            "metrics": self.metrics,
        }


def read_json(path: str | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.exists():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def as_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "y"}:
            return True
        if lowered in {"false", "0", "no", "n"}:
            return False
    return default


def match_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatch(path, pattern) for pattern in patterns)


def get_files(pr_metadata: dict[str, Any]) -> list[dict[str, Any]]:
    files = pr_metadata.get("files") or []
    out: list[dict[str, Any]] = []
    for f in files:
        if isinstance(f, dict) and f.get("path"):
            out.append(
                {
                    "path": str(f.get("path")),
                    "additions": int(f.get("additions") or 0),
                    "deletions": int(f.get("deletions") or 0),
                }
            )
    return out


def preflight(policy: dict[str, Any], pr: dict[str, Any], prompt_scan: dict[str, Any]) -> Decision:
    thresholds = policy.get("thresholds") or {}
    allowlist = list(policy.get("allowlist") or [])
    denylist = list(policy.get("denylist") or [])

    files = get_files(pr)
    changed_files = len(files)
    total_churn = sum(f["additions"] + f["deletions"] for f in files)

    reasons: list[str] = []

    internal_pr = as_bool(pr.get("internal_pr"), default=True)
    if not internal_pr:
        reasons.append("blocked_not_internal_pr")

    if as_bool(pr.get("isDraft"), default=False):
        reasons.append("blocked_draft_pr")

    if as_bool((prompt_scan or {}).get("suspicious"), default=False):
        reasons.append("blocked_prompt_injection_signal")

    max_changed_files = int(thresholds.get("max_changed_files", 12))
    if changed_files > max_changed_files:
        reasons.append("blocked_too_many_changed_files")

    max_total_churn = int(thresholds.get("max_total_churn", 400))
    if total_churn > max_total_churn:
        reasons.append("blocked_total_churn_threshold")

    denylist_hits = [f["path"] for f in files if match_any(f["path"], denylist)]
    if denylist_hits:
        reasons.append("blocked_sensitive_path_denylist")

    allowlist_misses = [f["path"] for f in files if not match_any(f["path"], allowlist)]
    if allowlist_misses:
        reasons.append("blocked_outside_low_risk_allowlist")

    if changed_files == 0:
        reasons.append("blocked_empty_diff")

    eligible = len(reasons) == 0
    decision_code = "eligible_preflight" if eligible else reasons[0]

    metrics = {
        "internal_pr": internal_pr,
        "changed_files": changed_files,
        "total_churn": total_churn,
        "max_changed_files": max_changed_files,
        "max_total_churn": max_total_churn,
        "denylist_hits": denylist_hits,
        "allowlist_misses": allowlist_misses,
        "prompt_injection_score": int((prompt_scan or {}).get("score") or 0),
        "prompt_injection_suspicious": as_bool((prompt_scan or {}).get("suspicious"), default=False),
    }

    return Decision(eligible=eligible, decision=decision_code, reasons=reasons, metrics=metrics)


def final_decision(
    policy: dict[str, Any],
    evaluation: dict[str, Any],
    checks: dict[str, Any],
) -> Decision:
    eval_cfg = policy.get("evaluation") or {}
    min_conf = float(eval_cfg.get("min_confidence", 0.9))
    allowed_risk = {str(x).lower() for x in (eval_cfg.get("allowed_risk_levels") or ["low"])}

    reasons: list[str] = []

    useful = as_bool(evaluation.get("useful"), default=False)
    necessary = as_bool(evaluation.get("necessary"), default=False)
    safe = as_bool(evaluation.get("safe"), default=False)
    confidence = float(evaluation.get("confidence") or 0.0)
    risk_level = str(evaluation.get("risk_level") or "").lower()
    blocking_findings = evaluation.get("blocking_findings") or []

    checks_status = str(checks.get("status") or "unknown").lower()

    if checks_status != "pass":
        reasons.append(f"blocked_required_checks_{checks_status}")

    if not useful:
        reasons.append("blocked_eval_not_useful")
    if not necessary:
        reasons.append("blocked_eval_not_necessary")
    if not safe:
        reasons.append("blocked_eval_not_safe")
    if confidence < min_conf:
        reasons.append("blocked_eval_low_confidence")
    if risk_level not in allowed_risk:
        reasons.append("blocked_eval_risk_level")
    if isinstance(blocking_findings, list) and len(blocking_findings) > 0:
        reasons.append("blocked_eval_blocking_findings")

    eligible = len(reasons) == 0
    decision_code = "eligible_merge" if eligible else reasons[0]

    metrics = {
        "checks_status": checks_status,
        "useful": useful,
        "necessary": necessary,
        "safe": safe,
        "confidence": confidence,
        "min_confidence": min_conf,
        "risk_level": risk_level,
        "allowed_risk_levels": sorted(allowed_risk),
        "blocking_findings_count": len(blocking_findings) if isinstance(blocking_findings, list) else 0,
    }

    return Decision(eligible=eligible, decision=decision_code, reasons=reasons, metrics=metrics)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic merge gate for Claude PR governor.")
    parser.add_argument("--mode", choices=["preflight", "final"], required=True)
    parser.add_argument("--policy", required=True, help="Path to policy JSON.")
    parser.add_argument("--pr-metadata-json", help="Path to PR metadata JSON (required for preflight).")
    parser.add_argument("--prompt-scan-json", help="Path to prompt scanner JSON.")
    parser.add_argument("--evaluation-json", help="Path to Claude evaluation JSON.")
    parser.add_argument("--checks-json", help="Path to required checks status JSON.")
    parser.add_argument("--output", help="Path to write decision JSON.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    policy = read_json(args.policy)

    if args.mode == "preflight":
        if not args.pr_metadata_json:
            raise SystemExit("--pr-metadata-json is required for preflight mode")
        pr = read_json(args.pr_metadata_json)
        scan = read_json(args.prompt_scan_json)
        result = preflight(policy, pr, scan)
    else:
        evaluation = read_json(args.evaluation_json)
        checks = read_json(args.checks_json)
        result = final_decision(policy, evaluation, checks)

    payload = json.dumps(result.to_dict(), indent=2, ensure_ascii=True)
    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
