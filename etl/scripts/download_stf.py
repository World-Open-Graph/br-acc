#!/usr/bin/env python3
"""Download STF (Supremo Tribunal Federal) decisions from Base dos Dados (BigQuery).

Streams from BigQuery table basedosdados.br_stf_corte_aberta.decisoes to local CSV.
Requires `google-cloud-bigquery` and an authenticated GCP project.

Usage:
    python etl/scripts/download_stf.py --billing-project icarus-corruptos
    python etl/scripts/download_stf.py --billing-project icarus-corruptos --skip-existing
    python etl/scripts/download_stf.py --billing-project icarus-corruptos --output-dir ./data/stf
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BQ_TABLE = "basedosdados.br_stf_corte_aberta.decisoes"

COLUMNS = [
    "ano",
    "classe",
    "numero",
    "relator",
    "link",
    "subgrupo_andamento",
    "andamento",
    "observacao_andamento_decisao",
    "modalidade_julgamento",
    "tipo_julgamento",
    "meio_tramitacao",
    "indicador_tramitacao",
    "assunto_processo",
    "ramo_direito",
    "data_autuacao",
    "data_decisao",
    "data_baixa_processo",
]

PAGE_SIZE = 100_000


def _download_decisions(
    billing_project: str,
    output_dir: Path,
    *,
    skip_existing: bool = False,
) -> None:
    """Stream STF decisions from BigQuery to a CSV file."""
    from google.cloud import bigquery

    dest = output_dir / "decisoes.csv"
    if skip_existing and dest.exists():
        logger.info("Skipping (exists): %s", dest.name)
        return

    client = bigquery.Client(project=billing_project)
    logger.info("Reading %s (%d columns)...", BQ_TABLE, len(COLUMNS))

    schema_fields = [bigquery.SchemaField(c, "STRING") for c in COLUMNS]

    rows_written = 0
    for i, chunk_df in enumerate(
        client.list_rows(BQ_TABLE, selected_fields=schema_fields, page_size=PAGE_SIZE)
        .to_dataframe_iterable(),
    ):
        chunk_df.to_csv(dest, mode="a", header=(i == 0), index=False)
        rows_written += len(chunk_df)
        if i == 0 or rows_written % (PAGE_SIZE * 5) == 0:
            logger.info("  decisoes: %d rows written", rows_written)

    logger.info("Done: %s -> %s (%d rows)", BQ_TABLE, dest.name, rows_written)


@click.command()
@click.option("--billing-project", required=True, help="GCP project for BigQuery billing")
@click.option("--output-dir", default="./data/stf", help="Output directory for CSV")
@click.option("--skip-existing", is_flag=True, help="Skip if CSV already exists")
def main(
    billing_project: str,
    output_dir: str,
    skip_existing: bool,
) -> None:
    """Download STF decisions from Base dos Dados (BigQuery) to local CSV."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    logger.info(
        "Downloading STF decisions from %s (billing: %s)",
        BQ_TABLE,
        billing_project,
    )

    _download_decisions(billing_project, out, skip_existing=skip_existing)

    # Print summary
    logger.info("=== Download complete ===")
    for f in sorted(out.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / 1e6
            logger.info("  %s: %.1f MB", f.name, size_mb)


if __name__ == "__main__":
    main()
    sys.exit(0)
