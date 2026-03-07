from __future__ import annotations

import json

import httpx
import typer
from rich.console import Console

from bracc_cli.config import get_settings

app = typer.Typer(help="Query public BR-ACC API endpoints.")
console = Console()


def _get_json(path: str, *, params: dict[str, object] | None = None) -> dict | list:
    settings = get_settings()
    url = f"{settings.api_url}{path}"
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        console.print(f"[red]Request failed ({exc.response.status_code}):[/red] {detail or exc}")
        raise typer.Exit(1) from exc
    except httpx.HTTPError as exc:
        console.print(f"[red]Could not reach API:[/red] {exc}")
        raise typer.Exit(1) from exc


def _print_json(payload: dict | list) -> None:
    console.print_json(json.dumps(payload, ensure_ascii=False, indent=2))


@app.command("meta")
def meta() -> None:
    """Show public metadata about the graph."""
    _print_json(_get_json("/api/v1/public/meta"))


def _require_cnpj(cnpj: str | None) -> str:
    """Validate CNPJ argument and exit with friendly message if missing."""
    if not cnpj or not str(cnpj).strip():
        console.print("[red]Erro:[/red] CNPJ ou ID da empresa é obrigatório.")
        console.print("[dim]Exemplo: bracc api company 11222333000181[/dim]")
        raise typer.Exit(1)
    return str(cnpj).strip()


@app.command("company")
def company(
    cnpj: str | None = typer.Argument(None, help="CNPJ ou ID da empresa"),
    depth: int = typer.Option(2, "--depth", min=1, max=3, help="Traversal depth."),
) -> None:
    """Fetch the public company graph for a CNPJ or entity id."""
    cnpj_val = _require_cnpj(cnpj)
    _print_json(_get_json(f"/api/v1/public/graph/company/{cnpj_val}", params={"depth": depth}))


@app.command("patterns")
def patterns(
    cnpj: str | None = typer.Argument(None, help="CNPJ ou ID da empresa"),
    lang: str = typer.Option("pt", "--lang", help="Response language."),
) -> None:
    """Fetch public patterns for a company."""
    cnpj_val = _require_cnpj(cnpj)
    _print_json(_get_json(f"/api/v1/public/patterns/company/{cnpj_val}", params={"lang": lang}))
