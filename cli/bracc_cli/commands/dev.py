from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import typer
from rich.console import Console

from bracc_cli.config import get_settings

app = typer.Typer(help="Manage the local development environment.")
console = Console()


def _run(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    input_text: str | None = None,
) -> None:
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        input=input_text,
        text=True,
        check=False,
    )
    if completed.returncode != 0:
        raise typer.Exit(completed.returncode)


def _seed_via_shell(repo_root: Path, env: dict[str, str]) -> bool:
    script = repo_root / "infra" / "scripts" / "seed-dev.sh"
    for candidate in ("bash", "sh"):
        executable = shutil.which(candidate)
        if executable is None:
            continue
        _run([executable, str(script)], cwd=repo_root, env=env)
        return True
    return False


def _seed_via_docker(repo_root: Path, env: dict[str, str]) -> None:
    cypher_file = repo_root / "infra" / "scripts" / "seed-dev.cypher"
    _run(
        [
            "docker",
            "exec",
            "-i",
            "-e",
            f"NEO4J_PASSWORD={env['NEO4J_PASSWORD']}",
            "bracc-neo4j",
            "cypher-shell",
            "-u",
            env.get("NEO4J_USER", "neo4j"),
            "-p",
            env["NEO4J_PASSWORD"],
        ],
        cwd=repo_root,
        env=env,
        input_text=cypher_file.read_text(encoding="utf-8"),
    )


@app.command("up")
def up() -> None:
    """Start the local Docker stack."""
    settings = get_settings()
    _run(["docker", "compose", "up", "-d", "--build"], cwd=settings.repo_root)


@app.command("down")
def down() -> None:
    """Stop the local Docker stack."""
    settings = get_settings()
    _run(["docker", "compose", "down"], cwd=settings.repo_root)


@app.command("restart")
def restart() -> None:
    """Restart the local Docker stack."""
    settings = get_settings()
    _run(["docker", "compose", "down"], cwd=settings.repo_root)
    _run(["docker", "compose", "up", "-d", "--build"], cwd=settings.repo_root)


@app.command("seed")
def seed() -> None:
    """Load deterministic development data into Neo4j."""
    settings = get_settings()
    if not settings.neo4j_password:
        console.print("[red]NEO4J_PASSWORD must be set in the environment or .env file.[/red]")
        raise typer.Exit(1)

    env = os.environ.copy()
    env["NEO4J_PASSWORD"] = settings.neo4j_password

    if _seed_via_shell(settings.repo_root, env):
        return

    if shutil.which("docker") is None:
        console.print("[red]Neither bash/sh nor docker is available to run the seed.[/red]")
        raise typer.Exit(1)

    _seed_via_docker(settings.repo_root, env)
