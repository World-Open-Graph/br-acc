#!/usr/bin/env python3
"""Download CNPJ data from Base dos Dados (BigQuery mirror) with history manifest.

Streams full tables from BigQuery to local CSVs page-by-page to avoid OOM.
Writes canonical historical files:
  - empresas_history.csv
  - socios_history.csv
  - estabelecimentos_history.csv
And a manifest:
  - download_manifest.json

Usage:
  python etl/scripts/download_cnpj_bq.py --billing-project icarus-corruptos
  python etl/scripts/download_cnpj_bq.py --billing-project icarus-corruptos --tables socios
"""

from __future__ import annotations

import hashlib
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_BQ_PROJECT = "basedosdados"
DEFAULT_BQ_DATASET = "br_me_cnpj"
SOURCE_ID = "cnpj"

# Include snapshot columns to preserve historical windows.
TABLES: dict[str, list[str]] = {
    "empresas": [
        "ano",
        "mes",
        "data",
        "cnpj_basico",
        "razao_social",
        "natureza_juridica",
        "qualificacao_responsavel",
        "capital_social",
        "porte",
        "ente_federativo",
    ],
    "socios": [
        "ano",
        "mes",
        "data",
        "cnpj_basico",
        "tipo",
        "nome",
        "documento",
        "qualificacao",
        "data_entrada_sociedade",
        "id_pais",
        "cpf_representante_legal",
        "nome_representante_legal",
        "qualificacao_representante_legal",
        "faixa_etaria",
    ],
    "estabelecimentos": [
        "ano",
        "mes",
        "data",
        "cnpj_basico",
        "cnpj_ordem",
        "cnpj_dv",
        "identificador_matriz_filial",
        "nome_fantasia",
        "situacao_cadastral",
        "data_situacao_cadastral",
        "motivo_situacao_cadastral",
        "nome_cidade_exterior",
        "id_pais",
        "data_inicio_atividade",
        "cnae_fiscal_principal",
        "cnae_fiscal_secundaria",
        "tipo_logradouro",
        "logradouro",
        "numero",
        "complemento",
        "bairro",
        "cep",
        "sigla_uf",
        "id_municipio",
        "ddd_1",
        "telefone_1",
        "ddd_2",
        "telefone_2",
        "ddd_fax",
        "fax",
        "email",
        "situacao_especial",
        "data_situacao_especial",
    ],
}

# Rows per page when streaming via BQ Storage Read API.
PAGE_SIZE = 100_000


def _run_bigquery_precheck(
    *,
    billing_project: str,
    source_project: str,
    source_dataset: str,
    snapshot_start: str | None,
) -> None:
    """Run explicit auth/ACL prechecks before starting large table downloads."""
    from google.cloud import bigquery

    client = bigquery.Client(project=billing_project)
    logger.info("Running BigQuery precheck: SELECT 1")
    list(client.query("SELECT 1 AS ok").result())

    socios_table = f"{source_project}.{source_dataset}.socios"
    if snapshot_start:
        precheck_sql = (
            f"SELECT COUNT(1) AS n FROM `{socios_table}` "
            "WHERE data >= @snapshot_start"
        )
        query_params = [
            bigquery.ScalarQueryParameter("snapshot_start", "DATE", snapshot_start),
        ]
    else:
        precheck_sql = f"SELECT COUNT(1) AS n FROM `{socios_table}`"
        query_params = []

    logger.info("Running BigQuery precheck: %s", precheck_sql)
    rows = list(
        client.query(
            precheck_sql,
            job_config=bigquery.QueryJobConfig(query_parameters=query_params),
        ).result(),
    )
    check_value = rows[0].n if rows else 0
    logger.info("BigQuery precheck OK: socios_count=%s", check_value)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _normalize_date(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    return text[:10]


def _download_table(
    billing_project: str,
    source_project: str,
    source_dataset: str,
    table: str,
    columns: list[str],
    output_dir: Path,
    *,
    snapshot_start: str | None = None,
    snapshot_end: str | None = None,
    skip_existing: bool = False,
) -> dict[str, Any]:
    """Stream one BQ table to historical CSV with snapshot metrics."""
    from google.cloud import bigquery

    dest = output_dir / f"{table}_history.csv"
    table_ref = f"{source_project}.{source_dataset}.{table}"
    started_at = datetime.now(UTC).isoformat()

    if skip_existing and dest.exists():
        logger.info("Skipping (exists): %s", dest.name)
        return {
            "table": table,
            "output_file": dest.name,
            "status": "skipped_existing",
            "rows": None,
            "snapshot_min": None,
            "snapshot_max": None,
            "checksum": _sha256_file(dest),
            "started_at": started_at,
            "finished_at": datetime.now(UTC).isoformat(),
            "error": "",
        }

    client = bigquery.Client(project=billing_project)
    table_obj = client.get_table(table_ref)
    table_schema = {f.name: f for f in table_obj.schema}
    selected_columns = [c for c in columns if c in table_schema]
    if not selected_columns:
        raise RuntimeError(f"No selected fields found for {table_ref}")

    where_clauses: list[str] = []
    query_params: list[bigquery.ScalarQueryParameter] = []
    if snapshot_start:
        where_clauses.append("data >= @snapshot_start")
        query_params.append(bigquery.ScalarQueryParameter("snapshot_start", "DATE", snapshot_start))
    if snapshot_end:
        where_clauses.append("data <= @snapshot_end")
        query_params.append(bigquery.ScalarQueryParameter("snapshot_end", "DATE", snapshot_end))

    where_sql = ""
    if where_clauses:
        where_sql = " WHERE " + " AND ".join(where_clauses)

    sql = (
        "SELECT "
        + ", ".join([f"`{c}`" for c in selected_columns])
        + f" FROM `{table_ref}`"
        + where_sql
    )

    logger.info(
        "Reading %s (%d columns)%s%s...",
        table_ref,
        len(selected_columns),
        f" from {snapshot_start}" if snapshot_start else "",
        f" to {snapshot_end}" if snapshot_end else "",
    )
    if dest.exists():
        dest.unlink()

    query_job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(query_parameters=query_params),
    )

    rows_written = 0
    snapshot_min = ""
    snapshot_max = ""
    for i, chunk_df in enumerate(
        query_job.result(page_size=PAGE_SIZE).to_dataframe_iterable(),
    ):
        if "data" in chunk_df.columns:
            snapshot_series = chunk_df["data"].map(_normalize_date)
            valid_dates = snapshot_series[snapshot_series != ""]
            if not valid_dates.empty:
                chunk_min = str(valid_dates.min())
                chunk_max = str(valid_dates.max())
                if not snapshot_min or chunk_min < snapshot_min:
                    snapshot_min = chunk_min
                if not snapshot_max or chunk_max > snapshot_max:
                    snapshot_max = chunk_max

        chunk_df.to_csv(dest, mode="a", header=(i == 0), index=False)
        rows_written += len(chunk_df)
        if i == 0 or rows_written % (PAGE_SIZE * 5) == 0:
            logger.info("  %s: %d rows written", table, rows_written)

    if rows_written == 0:
        raise RuntimeError(f"Table {table_ref} returned 0 rows")
    if not snapshot_max:
        raise RuntimeError(f"Table {table_ref} missing snapshot metadata (data column empty)")

    logger.info("Done: %s -> %s (%d rows)", table, dest.name, rows_written)
    return {
        "table": table,
        "output_file": dest.name,
        "status": "ok",
        "rows": rows_written,
        "snapshot_min": snapshot_min,
        "snapshot_max": snapshot_max,
        "checksum": _sha256_file(dest),
        "started_at": started_at,
        "finished_at": datetime.now(UTC).isoformat(),
        "error": "",
    }


@click.command()
@click.option("--billing-project", required=True, help="GCP project for BigQuery billing")
@click.option(
    "--dataset",
    default=f"{DEFAULT_BQ_PROJECT}.{DEFAULT_BQ_DATASET}",
    help="BigQuery source dataset in format <project>.<dataset>",
)
@click.option("--output-dir", default="../data/cnpj/extracted", help="Output directory for CSVs")
@click.option(
    "--manifest-path",
    default=None,
    help="Manifest output path (default: <output-dir>/download_manifest.json)",
)
@click.option(
    "--tables",
    multiple=True,
    type=click.Choice(list(TABLES.keys())),
    help="Tables to download (default: all)",
)
@click.option(
    "--snapshot-start",
    default=None,
    help="Inclusive snapshot date lower bound (YYYY-MM-DD) applied on column `data`",
)
@click.option(
    "--snapshot-end",
    default=None,
    help="Inclusive snapshot date upper bound (YYYY-MM-DD) applied on column `data`",
)
@click.option("--skip-existing", is_flag=True, help="Skip tables whose CSV already exists")
def main(
    billing_project: str,
    dataset: str,
    output_dir: str,
    manifest_path: str | None,
    tables: tuple[str, ...],
    snapshot_start: str | None,
    snapshot_end: str | None,
    skip_existing: bool,
) -> None:
    """Download CNPJ history from Base dos Dados (BigQuery) and write manifest."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    manifest_file = Path(manifest_path) if manifest_path else out / "download_manifest.json"

    if "." not in dataset:
        raise click.ClickException(
            "Invalid --dataset. Expected format <project>.<dataset> "
            f"(got: {dataset})",
        )
    source_project, source_dataset = dataset.split(".", 1)

    try:
        _run_bigquery_precheck(
            billing_project=billing_project,
            source_project=source_project,
            source_dataset=source_dataset,
            snapshot_start=snapshot_start,
        )
    except Exception as exc:
        raise click.ClickException(
            "BigQuery precheck failed. Configure a non-interactive service account "
            "(GOOGLE_APPLICATION_CREDENTIALS) with dataset ACL and billing access.",
        ) from exc

    selected = list(tables) if tables else list(TABLES.keys())
    run_id = f"cnpj-bq-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}-{uuid.uuid4().hex[:8]}"
    logger.info(
        "Downloading %d table(s) from %s (billing: %s) run_id=%s",
        len(selected), f"{source_project}.{source_dataset}", billing_project, run_id,
    )

    table_results: list[dict[str, Any]] = []
    failed = 0
    for table in selected:
        try:
            result = _download_table(
                billing_project,
                source_project,
                source_dataset,
                table,
                TABLES[table],
                out,
                snapshot_start=snapshot_start,
                snapshot_end=snapshot_end,
                skip_existing=skip_existing,
            )
            table_results.append(result)
        except Exception as exc:
            failed += 1
            logger.exception("Failed table %s: %s", table, exc)
            table_results.append(
                {
                    "table": table,
                    "output_file": f"{table}_history.csv",
                    "status": "failed",
                    "rows": 0,
                    "snapshot_min": None,
                    "snapshot_max": None,
                    "checksum": "",
                    "started_at": datetime.now(UTC).isoformat(),
                    "finished_at": datetime.now(UTC).isoformat(),
                    "error": str(exc),
                },
            )

    ok_count = sum(1 for r in table_results if r["status"] == "ok")
    skipped_count = sum(1 for r in table_results if r["status"] == "skipped_existing")
    rows_total = sum(int(r["rows"] or 0) for r in table_results if r["status"] == "ok")

    all_snapshot_max = sorted(
        [r["snapshot_max"] for r in table_results if r.get("snapshot_max")],
    )
    all_snapshot_min = sorted(
        [r["snapshot_min"] for r in table_results if r.get("snapshot_min")],
    )
    manifest_payload = {
        "run_id": run_id,
        "source_id": SOURCE_ID,
        "dataset": f"{source_project}.{source_dataset}",
        "billing_project": billing_project,
        "retrieved_at_utc": datetime.now(UTC).isoformat(),
        "tables": table_results,
        "summary": {
            "requested": len(selected),
            "ok": ok_count,
            "skipped_existing": skipped_count,
            "failed": failed,
            "rows_total": rows_total,
            "snapshot_min": all_snapshot_min[0] if all_snapshot_min else None,
            "snapshot_max": all_snapshot_max[-1] if all_snapshot_max else None,
            "requested_snapshot_start": snapshot_start,
            "requested_snapshot_end": snapshot_end,
        },
    }
    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    manifest_file.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Manifest written: %s", manifest_file)

    if ok_count == 0 and skipped_count == 0:
        raise click.ClickException("No CNPJ history tables downloaded successfully.")
    if failed > 0:
        raise click.ClickException(f"{failed} CNPJ history table(s) failed. See manifest.")

    logger.info("=== Download complete ===")
    for f in sorted(out.iterdir()):
        if f.is_file():
            size_mb = f.stat().st_size / 1e6
            logger.info("  %s: %.1f MB", f.name, size_mb)


if __name__ == "__main__":
    main()
    sys.exit(0)
