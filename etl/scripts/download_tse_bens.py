#!/usr/bin/env python3
"""Download TSE Bens Declarados (candidate declared assets) from Base dos Dados (BigQuery).

Streams from BigQuery table `basedosdados.br_tse_eleicoes.bens_candidato` to a local CSV.
Requires `google-cloud-bigquery` and an authenticated GCP project.

Usage:
    python etl/scripts/download_tse_bens.py --billing-project icarus-corruptos
    python etl/scripts/download_tse_bens.py --billing-project icarus-corruptos --start-year 2018
    python etl/scripts/download_tse_bens.py --billing-project icarus-corruptos --skip-existing
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BQ_BENS = "basedosdados.br_tse_eleicoes.bens_candidato"
BQ_CANDIDATOS = "basedosdados.br_tse_eleicoes.candidatos"

PAGE_SIZE = 100_000


@click.command()
@click.option("--billing-project", required=True, help="GCP project for BigQuery billing")
@click.option("--output-dir", default="./data/tse_bens", help="Output directory for CSV")
@click.option("--start-year", type=int, default=2002, help="Earliest election year to include")
@click.option("--skip-existing", is_flag=True, help="Skip download if CSV already exists")
def main(
    billing_project: str,
    output_dir: str,
    start_year: int,
    skip_existing: bool,
) -> None:
    """Download TSE Bens Declarados from Base dos Dados (BigQuery) to local CSV."""
    import google.auth
    from google.cloud import bigquery

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "bens.csv"

    if skip_existing and dest.exists():
        logger.info("Skipping (exists): %s", dest)
        return

    credentials, _ = google.auth.default()
    client = bigquery.Client(
        credentials=credentials,
        project=billing_project,
        location="US",
    )

    # JOIN bens with candidatos to get CPF and candidate name
    query = (
        f"SELECT b.ano, b.sigla_uf, b.tipo_item AS tipo_bem, "  # noqa: S608
        f"  b.descricao_item AS descricao_bem, b.valor_item AS valor_bem, "
        f"  c.cpf, c.nome AS nome_candidato, c.sigla_partido "
        f"FROM `{BQ_BENS}` b "
        f"LEFT JOIN `{BQ_CANDIDATOS}` c "
        f"  ON b.sequencial_candidato = c.sequencial AND b.ano = c.ano "
        f"WHERE b.ano >= {start_year} "
        f"ORDER BY b.ano, b.sigla_uf"
    )

    logger.info("Running query: bens JOIN candidatos (start_year=%d)", start_year)
    query_job = client.query(query)

    rows_written = 0
    for i, chunk_df in enumerate(query_job.result().to_dataframe_iterable()):
        chunk_df.to_csv(dest, mode="a", header=(i == 0), index=False)
        rows_written += len(chunk_df)
        if i == 0 or rows_written % (PAGE_SIZE * 5) == 0:
            logger.info("  bens: %d rows written", rows_written)

    logger.info("Done: %s (%d rows)", dest, rows_written)

    size_mb = dest.stat().st_size / 1e6
    logger.info("File size: %.1f MB", size_mb)


if __name__ == "__main__":
    main()
    sys.exit(0)
