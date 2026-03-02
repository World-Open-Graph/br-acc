#!/usr/bin/env python3
"""Run one-command full ingestion for public reproducibility."""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

from bootstrap_all.adapters import PreparationContext, TERMINAL_PREP_STATUSES, prepare_source

FINAL_STATUSES = {
    "loaded",
    "blocked_external",
    "blocked_credentials",
    "failed_download",
    "failed_pipeline",
    "skipped",
}


def utc_now() -> datetime:
    return datetime.now(UTC)


def utc_stamp(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%SZ")


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def load_contract(path: Path) -> dict[str, Any]:
    raw = path.read_text(encoding="utf-8")
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        try:
            import yaml  # type: ignore
        except ImportError as exc:
            raise RuntimeError(
                f"Failed to parse {path} as JSON and PyYAML is not installed"
            ) from exc
        parsed = yaml.safe_load(raw)
        if not isinstance(parsed, dict):
            raise RuntimeError(f"Invalid contract format in {path}")
        return parsed


def parse_implemented_registry_ids(path: Path) -> set[str]:
    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    implemented = {
        (row.get("pipeline_id") or "").strip()
        for row in rows
        if (row.get("in_universe_v1") or "").strip().lower() in {"true", "1", "yes", "y"}
        and (row.get("implementation_state") or "").strip() == "implemented"
    }
    implemented.discard("")
    return implemented


def run_cmd(
    cmd: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    printable = " ".join(cmd)
    print(f"$ {printable}")
    completed = subprocess.run(
        cmd,
        cwd=str(cwd),
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if completed.stdout:
        print(completed.stdout.strip())
    if completed.stderr:
        print(completed.stderr.strip(), file=sys.stderr)
    return completed


def compose_base(compose_file: Path) -> list[str]:
    return ["docker", "compose", "-f", str(compose_file)]


def wait_for_neo4j(cwd: Path, password: str, timeout_sec: int = 300) -> bool:
    start = time.time()
    while (time.time() - start) < timeout_sec:
        completed = run_cmd(
            [
                "docker",
                "exec",
                "bracc-neo4j",
                "cypher-shell",
                "-u",
                "neo4j",
                "-p",
                password,
                "RETURN 1",
            ],
            cwd=cwd,
        )
        if completed.returncode == 0:
            return True
        time.sleep(2)
    return False


def wait_for_api(timeout_sec: int = 300) -> bool:
    start = time.time()
    while (time.time() - start) < timeout_sec:
        try:
            with urlopen("http://localhost:8000/health", timeout=5) as response:  # noqa: S310
                body = response.read().decode("utf-8")
                if "ok" in body.lower():
                    return True
        except URLError:
            pass
        time.sleep(2)
    return False


def determine_reset_policy(args: argparse.Namespace) -> bool:
    if args.yes_reset and args.no_reset:
        raise RuntimeError("Cannot set --yes-reset and --no-reset at the same time")
    if args.yes_reset:
        return True
    if args.no_reset:
        return False

    if args.noninteractive:
        return False

    if not sys.stdin.isatty():
        raise RuntimeError(
            "Interactive reset prompt requires a TTY. Use --yes-reset or --no-reset for automation."
        )

    while True:
        answer = input("Reset local Neo4j graph before ingestion? [yes/no]: ").strip().lower()
        if answer in {"yes", "y"}:
            return True
        if answer in {"no", "n"}:
            return False
        print("Please answer yes or no.")


def reset_graph(cwd: Path, password: str) -> None:
    completed = run_cmd(
        [
            "docker",
            "exec",
            "bracc-neo4j",
            "cypher-shell",
            "-u",
            "neo4j",
            "-p",
            password,
            "MATCH (n) DETACH DELETE n",
        ],
        cwd=cwd,
    )
    if completed.returncode != 0:
        raise RuntimeError("Failed to reset Neo4j graph")


def remediation_hint(status: str, source: dict[str, Any]) -> str:
    pipeline_id = source["pipeline_id"]
    if status == "blocked_credentials":
        env_vars = source.get("credential_env", [])
        return f"Set required credentials: {', '.join(env_vars)}"
    if status == "blocked_external":
        return f"Provide required inputs for {pipeline_id} under {', '.join(source.get('required_inputs', []))}"
    if status == "failed_download":
        return f"Retry downloader for {pipeline_id} and verify source availability"
    if status == "failed_pipeline":
        return f"Inspect ETL logs for {pipeline_id} and input schema assumptions"
    if status == "skipped":
        return f"Review acquisition mode config for {pipeline_id}"
    return "-"


def write_markdown(summary: dict[str, Any], path: Path) -> None:
    lines = [
        "# Bootstrap All Summary",
        "",
        f"- run_id: `{summary['run_id']}`",
        f"- started_at_utc: `{summary['started_at_utc']}`",
        f"- ended_at_utc: `{summary['ended_at_utc']}`",
        f"- full_historical: `{str(summary['full_historical']).lower()}`",
        f"- db_reset_used: `{str(summary['db_reset_used']).lower()}`",
        f"- total_sources: `{summary['total_sources']}`",
        f"- loaded: `{summary['counts'].get('loaded', 0)}`",
        f"- blocked_external: `{summary['counts'].get('blocked_external', 0)}`",
        f"- blocked_credentials: `{summary['counts'].get('blocked_credentials', 0)}`",
        f"- failed_download: `{summary['counts'].get('failed_download', 0)}`",
        f"- failed_pipeline: `{summary['counts'].get('failed_pipeline', 0)}`",
        f"- skipped: `{summary['counts'].get('skipped', 0)}`",
        "",
        "## Per-source Results",
        "",
        "| Pipeline | Core | Status | Duration (s) | Remediation |",
        "|---|---|---|---:|---|",
    ]

    for row in summary["results"]:
        lines.append(
            "| {pipeline_id} | {core} | {status} | {duration} | {hint} |".format(
                pipeline_id=row["pipeline_id"],
                core="yes" if row.get("core") else "no",
                status=row["status"],
                duration=f"{row.get('duration_sec', 0):.2f}",
                hint=(row.get("remediation_hint") or "-").replace("|", "\\|"),
            )
        )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run bootstrap-all orchestrator")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--contract-path", default="config/bootstrap_all_contract.yml")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--sources", default="", help="Optional comma-separated pipeline subset")
    parser.add_argument("--yes-reset", action="store_true")
    parser.add_argument("--no-reset", action="store_true")
    parser.add_argument("--noninteractive", action="store_true")
    parser.add_argument("--report-latest", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    latest_summary = repo_root / "audit-results" / "bootstrap-all" / "latest" / "summary.md"

    if args.report_latest:
        if not latest_summary.exists():
            print("No bootstrap-all report found at audit-results/bootstrap-all/latest/summary.md")
            return 1
        print(latest_summary.read_text(encoding="utf-8"))
        return 0

    if shutil.which("docker") is None:
        print("docker is required", file=sys.stderr)
        return 1

    contract_path = repo_root / args.contract_path
    registry_path = repo_root / args.registry_path
    compose_path = (repo_root / args.compose_file).resolve()

    contract = load_contract(contract_path)
    sources = contract.get("sources", [])
    if not isinstance(sources, list):
        print("Invalid contract: sources must be a list", file=sys.stderr)
        return 1

    implemented_ids = parse_implemented_registry_ids(registry_path)
    contract_ids = {str(source.get("pipeline_id", "")).strip() for source in sources}
    contract_ids.discard("")

    expected_count = int(contract.get("expected_implemented_count", len(contract_ids)))
    if len(contract_ids) != expected_count:
        print(
            f"Contract mismatch: expected_implemented_count={expected_count} but sources={len(contract_ids)}",
            file=sys.stderr,
        )
        return 1

    if contract_ids != implemented_ids:
        missing = sorted(implemented_ids - contract_ids)
        extra = sorted(contract_ids - implemented_ids)
        print("Contract/registry mismatch", file=sys.stderr)
        if missing:
            print(f"- missing in contract: {missing}", file=sys.stderr)
        if extra:
            print(f"- extra in contract: {extra}", file=sys.stderr)
        return 1

    selected_ids: set[str] | None = None
    if args.sources.strip():
        selected_ids = {item.strip() for item in args.sources.split(",") if item.strip()}
        unknown = sorted(selected_ids - contract_ids)
        if unknown:
            print(f"Unknown source(s) in --sources: {unknown}", file=sys.stderr)
            return 1
        sources = [source for source in sources if source["pipeline_id"] in selected_ids]

    dotenv_values = parse_dotenv(repo_root / ".env")
    neo4j_password = os.getenv("NEO4J_PASSWORD") or dotenv_values.get("NEO4J_PASSWORD") or "changeme"
    compose_env = os.environ.copy()
    compose_env.update(dotenv_values)
    compose_env["NEO4J_PASSWORD"] = neo4j_password

    compose = compose_base(compose_path)

    stack_up = run_cmd(
        compose + ["up", "-d", "neo4j", "api", "frontend"],
        cwd=repo_root,
        env=compose_env,
    )
    if stack_up.returncode != 0:
        print("Failed to start Docker stack", file=sys.stderr)
        return 1

    if not wait_for_neo4j(repo_root, neo4j_password):
        print("Neo4j did not become healthy", file=sys.stderr)
        return 1

    if not wait_for_api():
        print("API did not become healthy", file=sys.stderr)
        return 1

    try:
        db_reset = determine_reset_policy(args)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if db_reset:
        reset_graph(repo_root, neo4j_password)

    def run_etl_shell(shell_cmd: str) -> subprocess.CompletedProcess[str]:
        env_cmd = ["-e", f"NEO4J_PASSWORD={neo4j_password}"]
        for key in ("GOOGLE_APPLICATION_CREDENTIALS", "GOOGLE_CLOUD_PROJECT", "BQ_PROJECT_ID"):
            value = os.getenv(key) or dotenv_values.get(key)
            if value:
                env_cmd.extend(["-e", f"{key}={value}"])
        return run_cmd(
            compose + ["--profile", "etl", "run", "--rm"] + env_cmd + ["etl", "bash", "-lc", shell_cmd],
            cwd=repo_root,
            env=compose_env,
        )

    run_started = utc_now()
    stamp = utc_stamp(run_started)
    run_id = f"bootstrap-all-{stamp}"
    output_dir = repo_root / "audit-results" / "bootstrap-all" / stamp
    output_dir.mkdir(parents=True, exist_ok=True)

    context = PreparationContext(repo_root=str(repo_root), run_in_etl_shell=run_etl_shell)

    core_sources = set(contract.get("core_sources", []))
    results: list[dict[str, Any]] = []

    for source in sources:
        pipeline_id = source["pipeline_id"]
        started = time.time()

        credential_env = source.get("credential_env", [])
        missing_credentials = [
            key
            for key in credential_env
            if not (os.getenv(key) or dotenv_values.get(key))
        ]
        if missing_credentials:
            status = "blocked_credentials"
            result = {
                "pipeline_id": pipeline_id,
                "core": bool(source.get("core", False)),
                "status": status,
                "duration_sec": time.time() - started,
                "artifacts": [],
                "records_estimate": None,
                "error": None,
                "blocked_reason": f"missing credentials: {', '.join(missing_credentials)}",
                "remediation_hint": remediation_hint(status, source),
                "ingestion_exit_code": None,
            }
            results.append(result)
            print(f"[{pipeline_id}] {status}")
            continue

        prep = prepare_source(source, context)
        if prep.status in TERMINAL_PREP_STATUSES:
            status = prep.status if prep.status in FINAL_STATUSES else "skipped"
            result = {
                "pipeline_id": pipeline_id,
                "core": bool(source.get("core", False)),
                "status": status,
                "duration_sec": time.time() - started,
                "artifacts": prep.artifacts,
                "records_estimate": prep.records_estimate,
                "error": prep.error,
                "blocked_reason": prep.blocked_reason,
                "remediation_hint": remediation_hint(status, source),
                "ingestion_exit_code": None,
            }
            results.append(result)
            print(f"[{pipeline_id}] {status}")
            continue

        ingest_cmd = (
            "cd /workspace/etl && "
            f"bracc-etl run --source {pipeline_id} "
            "--neo4j-uri bolt://neo4j:7687 "
            "--neo4j-user neo4j "
            "--neo4j-password \"$NEO4J_PASSWORD\" "
            "--neo4j-database neo4j "
            "--data-dir ../data "
            "--linking-tier full"
        )
        completed = run_etl_shell(ingest_cmd)
        status = "loaded" if completed.returncode == 0 else "failed_pipeline"

        error_tail = (completed.stderr or "").strip()
        if len(error_tail) > 3000:
            error_tail = error_tail[-3000:]

        result = {
            "pipeline_id": pipeline_id,
            "core": bool(source.get("core", False)),
            "status": status,
            "duration_sec": time.time() - started,
            "artifacts": prep.artifacts,
            "records_estimate": prep.records_estimate,
            "error": None if status == "loaded" else error_tail,
            "blocked_reason": prep.blocked_reason,
            "remediation_hint": remediation_hint(status, source),
            "ingestion_exit_code": completed.returncode,
        }
        results.append(result)
        print(f"[{pipeline_id}] {status}")

    ended = utc_now()
    counts = Counter(row["status"] for row in results)
    core_failures = [
        row for row in results if (row["pipeline_id"] in core_sources or row.get("core")) and row["status"] != "loaded"
    ]

    summary = {
        "run_id": run_id,
        "started_at_utc": run_started.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ended_at_utc": ended.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "full_historical": bool(contract.get("full_historical_default", True)),
        "db_reset_used": db_reset,
        "contract_path": str(contract_path.relative_to(repo_root)),
        "registry_path": str(registry_path.relative_to(repo_root)),
        "total_sources": len(results),
        "core_sources": sorted(core_sources),
        "counts": dict(counts),
        "core_failures": [row["pipeline_id"] for row in core_failures],
        "results": results,
    }

    summary_json = output_dir / "summary.json"
    summary_json.write_text(json.dumps(summary, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")

    summary_md = output_dir / "summary.md"
    write_markdown(summary, summary_md)

    latest_dir = repo_root / "audit-results" / "bootstrap-all" / "latest"
    if latest_dir.exists():
        shutil.rmtree(latest_dir)
    shutil.copytree(output_dir, latest_dir)

    print(f"Bootstrap-all summary written to: {summary_json}")

    if core_failures:
        print(f"Core source failures detected: {[row['pipeline_id'] for row in core_failures]}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
