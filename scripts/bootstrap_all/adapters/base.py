from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

import subprocess


@dataclass
class PreparationResult:
    status: str
    artifacts: list[str] = field(default_factory=list)
    records_estimate: int | None = None
    error: str | None = None
    blocked_reason: str | None = None


@dataclass
class PreparationContext:
    repo_root: str
    run_in_etl_shell: Callable[[str], subprocess.CompletedProcess[str]]


TERMINAL_PREP_STATUSES = {
    "blocked_external",
    "blocked_credentials",
    "failed_download",
    "skipped",
}
