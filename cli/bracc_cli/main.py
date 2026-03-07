from __future__ import annotations

import typer

from bracc_cli.commands import api, dev, etl, health, report

app = typer.Typer(
    help="BR-ACC CLI for local development, API queries, ETLs, and reports.",
    no_args_is_help=True,
)

app.add_typer(dev.app, name="dev")
app.add_typer(api.app, name="api")
app.add_typer(etl.app, name="etl")
app.add_typer(report.app, name="report")
app.add_typer(health.app, name="health")


if __name__ == "__main__":
    app()
