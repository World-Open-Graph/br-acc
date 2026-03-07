from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.markdown import Markdown

from bracc_cli.config import get_settings

app = typer.Typer(help="Read generated BR-ACC reports.")
console = Console()


def _report_root() -> Path:
    return get_settings().report_root


@app.command("latest")
def latest() -> None:
    """Show the latest bootstrap-all summary report."""
    summary_path = _report_root() / "bootstrap-all" / "latest" / "summary.md"
    if not summary_path.exists():
        console.print(f"[red]Report not found:[/red] {summary_path}")
        raise typer.Exit(1)

    console.print(Markdown(summary_path.read_text(encoding="utf-8")))


@app.command("list")
def list_reports() -> None:
    """List report files under audit-results."""
    report_root = _report_root()
    if not report_root.exists():
        console.print(f"[red]Report directory not found:[/red] {report_root}")
        raise typer.Exit(1)

    files = sorted(path for path in report_root.rglob("*") if path.is_file())
    if not files:
        console.print("[yellow]No reports found.[/yellow]")
        return

    for path in files:
        console.print(path.relative_to(report_root.parent))
