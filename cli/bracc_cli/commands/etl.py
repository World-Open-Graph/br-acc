from __future__ import annotations

import os
import shutil
import subprocess

import typer
from rich.console import Console

from bracc_cli.config import get_settings

DEFAULT_RUN_ALL_SOURCES = ["cnpj", "tse", "transparencia", "sanctions"]

app = typer.Typer(help="Run and inspect ETL pipelines.")
console = Console()


def _etl_base_command() -> list[str]:
    if shutil.which("uv") is not None:
        return ["uv", "run", "bracc-etl"]
    if shutil.which("bracc-etl") is not None:
        return ["bracc-etl"]
    console.print("[red]Neither uv nor bracc-etl is available in PATH.[/red]")
    raise typer.Exit(1)


def _run_etl(command: list[str], *, extra_env: dict[str, str] | None = None) -> None:
    settings = get_settings()
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)

    completed = subprocess.run(
        command,
        cwd=settings.repo_root / "etl",
        env=env,
        check=False,
    )
    if completed.returncode != 0:
        raise typer.Exit(completed.returncode)


@app.command("list")
def list_sources() -> None:
    """List available ETL pipelines."""
    _run_etl(_etl_base_command() + ["sources"])


def _require_source(source: str | None) -> str:
    """Validate source argument and exit with friendly message if missing."""
    if not source or not str(source).strip():
        console.print("[red]Erro:[/red] Nome do pipeline é obrigatório.")
        console.print("[dim]Use 'bracc etl list' para ver pipelines disponíveis.[/dim]")
        raise typer.Exit(1)
    return str(source).strip()


@app.command("run")
def run(
    source: str | None = typer.Argument(None, help="ID do pipeline (ex: cnpj, tse)"),
    neo4j_password: str | None = typer.Option(
        None,
        "--neo4j-password",
        help="Neo4j password. Defaults to NEO4J_PASSWORD.",
    ),
    data_dir: str | None = typer.Option(None, "--data-dir", help="Override the data directory."),
) -> None:
    """Run one ETL pipeline."""
    source_val = _require_source(source)
    settings = get_settings()
    password = neo4j_password or settings.neo4j_password
    if not password:
        console.print("[red]NEO4J_PASSWORD must be set to run ETL commands.[/red]")
        raise typer.Exit(1)

    command = _etl_base_command() + [
        "run",
        "--source",
        source_val,
        "--neo4j-password",
        password,
        "--data-dir",
        data_dir or str(settings.data_dir),
    ]
    _run_etl(command)


@app.command("run-all")
def run_all(
    sources: list[str] | None = typer.Argument(None, help="Optional subset of source ids."),
    neo4j_password: str | None = typer.Option(
        None,
        "--neo4j-password",
        help="Neo4j password. Defaults to NEO4J_PASSWORD.",
    ),
) -> None:
    """Run the default ETL suite or the provided sources."""
    selected_sources = sources or DEFAULT_RUN_ALL_SOURCES
    for source in selected_sources:
        console.print(f"[cyan]Running pipeline:[/cyan] {source}")
        run(source=source, neo4j_password=neo4j_password, data_dir=None)


@app.command("status")
def status(
    neo4j_password: str | None = typer.Option(
        None,
        "--neo4j-password",
        help="Neo4j password. Defaults to NEO4J_PASSWORD.",
    ),
) -> None:
    """Show ingestion status from Neo4j."""
    settings = get_settings()
    password = neo4j_password or settings.neo4j_password
    if not password:
        console.print("[red]NEO4J_PASSWORD must be set to inspect ETL status.[/red]")
        raise typer.Exit(1)

    _run_etl(_etl_base_command() + ["sources", "--status", "--neo4j-password", password])
