from __future__ import annotations

import httpx
import typer
from rich.console import Console

from bracc_cli.config import get_settings

app = typer.Typer(help="Check the state of the BR-ACC services.")
console = Console()


def _status_label(ok: bool) -> str:
    return "[green]OK[/green]" if ok else "[red]ERROR[/red]"


@app.callback(invoke_without_command=True)
def health() -> None:
    """Check API and Neo4j health endpoints."""
    settings = get_settings()
    api_ok = False
    neo4j_ok = False

    try:
        with httpx.Client(timeout=10.0) as client:
            api_response = client.get(f"{settings.api_url}/health")
            api_response.raise_for_status()
            api_ok = api_response.json().get("status") == "ok"

            neo4j_response = client.get(f"{settings.api_url}/api/v1/meta/health")
            neo4j_response.raise_for_status()
            neo4j_ok = neo4j_response.json().get("neo4j") == "connected"
    except httpx.HTTPError as exc:
        console.print(f"[red]Health check failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    console.print(f"API: {_status_label(api_ok)}")
    console.print(f"Neo4j: {_status_label(neo4j_ok)}")

    if not api_ok or not neo4j_ok:
        raise typer.Exit(1)
