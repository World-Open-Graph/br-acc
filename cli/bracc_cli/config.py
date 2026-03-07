from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _default_repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_env(repo_root: Path, cli_root: Path) -> None:
    load_dotenv(repo_root / ".env", override=False)
    load_dotenv(cli_root / ".env", override=False)


@dataclass(frozen=True)
class Settings:
    repo_root: Path
    cli_root: Path
    api_url: str
    neo4j_password: str | None
    report_root: Path
    data_dir: Path


def get_settings() -> Settings:
    repo_root_value = os.getenv("BRACC_REPO_ROOT", str(_default_repo_root()))
    repo_root = Path(repo_root_value).resolve()
    cli_root = repo_root / "cli"
    _load_env(repo_root, cli_root)

    api_url = os.getenv("BRACC_API_URL", "http://localhost:8000").rstrip("/")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    return Settings(
        repo_root=repo_root,
        cli_root=cli_root,
        api_url=api_url,
        neo4j_password=neo4j_password,
        report_root=repo_root / "audit-results",
        data_dir=repo_root / "data",
    )
