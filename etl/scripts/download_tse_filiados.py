#!/usr/bin/env python3
"""Download TSE party membership (filiacao partidaria) from Base dos Dados (BigQuery).

Streams the table basedosdados.br_tse_filiacao_partidaria.microdados to a local CSV.
Filters to REGULAR status only (active members) to reduce volume.

Requires `google-cloud-bigquery` and an authenticated GCP project.

Usage:
    python etl/scripts/download_tse_filiados.py --billing-project icarus-corruptos
    python etl/scripts/download_tse_filiados.py --billing-project icarus-corruptos --skip-existing
    python etl/scripts/download_tse_filiados.py --billing-project icarus-corruptos --all-statuses
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BQ_PROJECT = "basedosdados"
BQ_DATASET = "br_tse_filiacao_partidaria"
BQ_TABLE = "microdados"

COLUMNS = [
    "cpf",
    "nome",
    "nome_social",
    "sigla_uf",
    "id_municipio_tse",
    "sigla_partido",
    "data_filiacao",
    "situacao_registro",
    "data_desfiliacao",
    "data_cancelamento",
    "motivo_cancelamento",
    "motivo_desfiliacao",
    "titulo_eleitor",
]

PAGE_SIZE = 100_000


def _download(
    billing_project: str,
    output_dir: Path,
    *,
    skip_existing: bool = False,
    all_statuses: bool = False,
) -> None:
    from google.cloud import bigquery

    dest = output_dir / "filiados.csv"
    if skip_existing and dest.exists():
        logger.info("Skipping (exists): %s", dest.name)
        return

    client = bigquery.Client(project=billing_project)
    table_ref = f"{BQ_PROJECT}.{BQ_DATASET}.{BQ_TABLE}"

    cols = ", ".join(COLUMNS)
    where = "" if all_statuses else "WHERE situacao_registro = 'Regular'"
    query = f"SELECT {cols} FROM `{table_ref}` {where}"  # noqa: S608

    logger.info("Running query: %s", query[:200])
    query_job = client.query(query)

    rows_written = 0
    for i, chunk_df in enumerate(query_job.result().to_dataframe_iterable()):
        chunk_df.to_csv(dest, mode="a", header=(i == 0), index=False)
        rows_written += len(chunk_df)
        if i == 0 or rows_written % (PAGE_SIZE * 5) == 0:
            logger.info("  filiados: %d rows written", rows_written)

    logger.info("Done: %s (%d rows)", dest.name, rows_written)


@click.command()
@click.option("--billing-project", required=True, help="GCP project for BigQuery billing")
@click.option("--output-dir", default="./data/tse_filiados", help="Output directory for CSV")
@click.option("--skip-existing", is_flag=True, help="Skip if CSV already exists")
@click.option("--all-statuses", is_flag=True, help="Include all statuses, not just REGULAR")
def main(
    billing_project: str,
    output_dir: str,
    skip_existing: bool,
    all_statuses: bool,
) -> None:
    """Download TSE party membership data from Base dos Dados (BigQuery)."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading filiados from %s.%s.%s (billing: %s, all_statuses: %s)",
        BQ_PROJECT, BQ_DATASET, BQ_TABLE, billing_project, all_statuses,
    )

    _download(billing_project, out, skip_existing=skip_existing, all_statuses=all_statuses)

    # Print summary
    logger.info("=== Download complete ===")
    for f in sorted(out.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / 1e6
            logger.info("  %s: %.1f MB", f.name, size_mb)


if __name__ == "__main__":
    main()
    sys.exit(0)
