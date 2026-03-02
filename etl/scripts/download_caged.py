#!/usr/bin/env python3
"""Download CAGED labor movement data from Base dos Dados (BigQuery).

Streams microdados_movimentacao year-by-year to separate CSVs for
resumability and memory management on large datasets.

Usage:
    python etl/scripts/download_caged.py --billing-project icarus-corruptos
    python etl/scripts/download_caged.py --billing-project icarus-corruptos --start-year 2024
    python etl/scripts/download_caged.py --billing-project icarus-corruptos --skip-existing
"""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BQ_TABLE = "basedosdados.br_me_caged.microdados_movimentacao"

COLUMNS = [
    "ano",
    "mes",
    "sigla_uf",
    "id_municipio",
    "cnae_2_secao",
    "cnae_2_subclasse",
    "cbo_2002",
    "categoria",
    "grau_instrucao",
    "idade",
    "horas_contratuais",
    "raca_cor",
    "sexo",
    "tipo_empregador",
    "tipo_estabelecimento",
    "tipo_movimentacao",
    "tipo_deficiencia",
    "indicador_trabalho_intermitente",
    "indicador_trabalho_parcial",
    "salario_mensal",
    "saldo_movimentacao",
    "tamanho_estabelecimento_janeiro",
    "indicador_aprendiz",
    "origem_informacao",
    "indicador_fora_prazo",
]

PAGE_SIZE = 100_000


def _download_year(
    client: object,
    year: int,
    output_dir: Path,
    *,
    skip_existing: bool = False,
) -> int:
    """Download a single year of CAGED data. Returns row count."""
    dest = output_dir / f"caged_{year}.csv"
    if skip_existing and dest.exists():
        logger.info("Skipping (exists): %s", dest.name)
        return 0

    cols = ", ".join(COLUMNS)
    sql = f"SELECT {cols} FROM `{BQ_TABLE}` WHERE ano = {year}"  # noqa: S608

    logger.info("Querying year %d ...", year)
    query_job = client.query(sql)  # type: ignore[union-attr]

    rows_written = 0
    for i, chunk_df in enumerate(query_job.result().to_dataframe_iterable()):
        chunk_df.to_csv(dest, mode="a", header=(i == 0), index=False)
        rows_written += len(chunk_df)
        if i == 0 or rows_written % (PAGE_SIZE * 5) == 0:
            logger.info("  caged_%d: %d rows written", year, rows_written)

    if rows_written == 0:
        logger.info("  caged_%d: no data found", year)
    else:
        size_mb = dest.stat().st_size / 1e6
        logger.info("  caged_%d: %d rows, %.1f MB", year, rows_written, size_mb)

    return rows_written


@click.command()
@click.option("--billing-project", required=True, help="GCP project for BigQuery billing")
@click.option("--output-dir", default="./data/caged", help="Output directory for CSV files")
@click.option("--start-year", type=int, default=2020, help="Start year (default: 2020, first year of new CAGED)")
@click.option("--end-year", type=int, default=None, help="End year inclusive (default: current year)")
@click.option("--skip-existing", is_flag=True, help="Skip years whose CSV already exists")
def main(
    billing_project: str,
    output_dir: str,
    start_year: int,
    end_year: int | None,
    skip_existing: bool,
) -> None:
    """Download CAGED labor movement data from Base dos Dados (BigQuery).

    Downloads year-by-year into separate files (caged_2020.csv, caged_2021.csv, ...)
    for resumability and manageable BQ scan sizes.
    """
    from google.cloud import bigquery

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if end_year is None:
        end_year = datetime.now(tz=timezone.utc).year

    years = list(range(start_year, end_year + 1))

    logger.info(
        "Downloading CAGED from %s (years %d-%d, billing: %s)",
        BQ_TABLE, start_year, end_year, billing_project,
    )

    client = bigquery.Client(project=billing_project)
    total_rows = 0

    for year in years:
        rows = _download_year(client, year, out, skip_existing=skip_existing)
        total_rows += rows

    # Print summary
    logger.info("=== Download complete === (%d total rows)", total_rows)
    for f in sorted(out.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / 1e6
            logger.info("  %s: %.1f MB", f.name, size_mb)


if __name__ == "__main__":
    main()
    sys.exit(0)
