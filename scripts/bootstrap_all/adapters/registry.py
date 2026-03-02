from __future__ import annotations

from pathlib import Path

from .base import PreparationContext, PreparationResult


def _expand_inputs(repo_root: str, patterns: list[str]) -> list[Path]:
    root = Path(repo_root)
    matches: list[Path] = []
    for pattern in patterns:
        matches.extend(root.glob(pattern))
    return sorted({path.resolve() for path in matches if path.exists()})


def _missing_patterns(repo_root: str, patterns: list[str]) -> list[str]:
    root = Path(repo_root)
    missing: list[str] = []
    for pattern in patterns:
        if not any(root.glob(pattern)):
            missing.append(pattern)
    return missing


def prepare_source(source: dict, context: PreparationContext) -> PreparationResult:
    pipeline_id = source["pipeline_id"]
    mode = source.get("acquisition_mode", "file_manifest").strip()
    required_inputs = source.get("required_inputs", [])
    blocked_reason = source.get("blocking_reason_if_any", "")

    if mode == "blocked_external":
        reason = blocked_reason if blocked_reason and blocked_reason != "-" else "external blocker declared"
        return PreparationResult(status="blocked_external", blocked_reason=reason)

    if mode == "script_download":
        download_commands = source.get("download_commands", [])
        if not download_commands:
            return PreparationResult(
                status="failed_download",
                error=f"No download_commands defined for {pipeline_id}",
            )

        for shell_cmd in download_commands:
            completed = context.run_in_etl_shell(shell_cmd)
            if completed.returncode != 0:
                tail = (completed.stderr or "").strip()[-2000:]
                return PreparationResult(
                    status="failed_download",
                    error=tail or f"download command failed for {pipeline_id}",
                )

        missing = _missing_patterns(context.repo_root, required_inputs)
        if missing:
            return PreparationResult(
                status="failed_download",
                blocked_reason=f"required inputs missing after download: {', '.join(missing)}",
            )

        artifacts = [str(path) for path in _expand_inputs(context.repo_root, required_inputs)[:25]]
        return PreparationResult(
            status="ready",
            artifacts=artifacts,
            records_estimate=len(artifacts),
        )

    if mode == "file_manifest":
        missing = _missing_patterns(context.repo_root, required_inputs)
        if missing:
            reason = blocked_reason if blocked_reason and blocked_reason != "-" else "input files not available"
            return PreparationResult(
                status="blocked_external",
                blocked_reason=f"{reason}; missing: {', '.join(missing)}",
            )

        artifacts = [str(path) for path in _expand_inputs(context.repo_root, required_inputs)[:25]]
        return PreparationResult(
            status="ready",
            artifacts=artifacts,
            records_estimate=len(artifacts),
        )

    return PreparationResult(status="skipped", blocked_reason=f"Unsupported acquisition mode: {mode}")
