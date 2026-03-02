#!/usr/bin/env python3
"""Download MiDES municipal procurement datasets from BigQuery.

Outputs canonical files consumed by MidesPipeline:
- data/mides/licitacao.csv
- data/mides/contrato.csv
- data/mides/item.csv
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

logger = logging.getLogger(__name__)

LEGACY_DATASET = "basedosdados.br_mides"
WORLD_WB_DATASET = "basedosdados.world_wb_mides"


def _run_query_to_csv(
    billing_project: str,
    query: str,
    output_path: Path,
    *,
    skip_existing: bool,
) -> int:
    if skip_existing and output_path.exists() and output_path.stat().st_size > 0:
        logger.info("Skipping (exists): %s", output_path)
        return -1

    try:
        import google.auth
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError("Install optional deps: pip install '.[bigquery]'") from exc

    credentials, _ = google.auth.default()
    client = bigquery.Client(project=billing_project, credentials=credentials)

    logger.info("Querying BigQuery into %s", output_path.name)
    df = client.query(query).result().to_dataframe(create_bqstorage_client=True)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("Wrote %d rows to %s", len(df), output_path)
    return int(len(df))


def _write_manifest(out_dir: Path, tables: list[dict[str, Any]]) -> Path:
    path = out_dir / "download_manifest.json"
    payload = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "source": "mides",
        "tables": tables,
        "summary": {
            "ok": sum(1 for t in tables if t["status"] == "ok"),
            "skipped_existing": sum(
                1 for t in tables if t["status"] == "skipped_existing"
            ),
            "failed": sum(1 for t in tables if t["status"] == "failed"),
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("Wrote manifest to %s", path)
    return path


@click.command()
@click.option("--billing-project", default="icarus-corruptos", help="GCP billing project")
@click.option(
    "--dataset",
    default=WORLD_WB_DATASET,
    help="BigQuery dataset id (supports br_mides and world_wb_mides)",
)
@click.option("--output-dir", default="./data/mides", help="Output directory")
@click.option("--start-year", type=int, default=2021, help="Filter start year")
@click.option("--end-year", type=int, default=2100, help="Filter end year")
@click.option("--skip-existing/--no-skip-existing", default=True)
def main(
    billing_project: str,
    dataset: str,
    output_dir: str,
    start_year: int,
    end_year: int,
    skip_existing: bool,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    if "world_wb_mides" in dataset.lower():
        profile = "world_wb_mides"
        year_filter_licitacao = (
            f"WHERE SAFE_CAST(l.ano AS INT64) BETWEEN {start_year} AND {end_year}"
        )
        year_filter_items = (
            f"WHERE SAFE_CAST(i.ano AS INT64) BETWEEN {start_year} AND {end_year}"
        )
        year_filter_participante = (
            f"WHERE SAFE_CAST(ano AS INT64) BETWEEN {start_year} AND {end_year}"
        )
        data_publicacao_expr = (
            "CAST(COALESCE(l.data_publicacao_dispensa, l.data_edital, "
            "l.data_abertura, l.data_homologacao) AS STRING)"
        )
        data_publicacao_filter = (
            "AND (COALESCE(l.data_publicacao_dispensa, l.data_edital, "
            "l.data_abertura, l.data_homologacao) IS NULL "
            "OR COALESCE(l.data_publicacao_dispensa, l.data_edital, "
            "l.data_abertura, l.data_homologacao) <= CURRENT_DATE() + INTERVAL 365 DAY)"
        )
        valor_estimado_expr = (
            "CAST(COALESCE(l.valor_orcamento, l.valor, l.valor_corrigido) AS FLOAT64)"
        )
        valor_expr = (
            "CAST(COALESCE(l.valor, l.valor_corrigido, l.valor_orcamento) AS FLOAT64)"
        )
        data_assinatura_expr = (
            "CAST(COALESCE(l.data_homologacao, l.data_abertura, l.data_edital) AS STRING)"
        )
        data_assinatura_filter = (
            "AND (COALESCE(l.data_homologacao, l.data_abertura, l.data_edital) IS NULL "
            "OR COALESCE(l.data_homologacao, l.data_abertura, l.data_edital) "
            "<= CURRENT_DATE() + INTERVAL 365 DAY)"
        )
        winners_cte = (
            "WITH winners AS ("
            f"SELECT id_licitacao, id_municipio, sigla_uf, orgao, id_unidade_gestora, "
            "ANY_VALUE(documento) AS winner_document "
            f"FROM `{dataset}.licitacao_participante` "
            f"{year_filter_participante} "
            "AND SAFE_CAST(vencedor AS INT64) = 1 "
            "GROUP BY id_licitacao, id_municipio, sigla_uf, orgao, id_unidade_gestora"
            ") "
        )
        queries = {
            "licitacao.csv": (
                winners_cte
                + "SELECT "
                "CAST(l.id_licitacao AS STRING) AS licitacao_id, "
                "CAST(l.id_licitacao_bd AS STRING) AS id_licitacao, "
                "CAST(l.id_licitacao AS STRING) AS numero_processo, "
                "CAST(l.id_municipio AS STRING) AS cod_ibge, "
                "CAST('' AS STRING) AS municipio, "
                "CAST(l.sigla_uf AS STRING) AS estado, "
                "CAST(l.modalidade AS STRING) AS modalidade, "
                "CAST(l.descricao_objeto AS STRING) AS objeto, "
                f"{data_publicacao_expr} AS data_publicacao, "
                "CAST(l.ano AS STRING) AS ano, "
                f"{valor_estimado_expr} AS valor_estimado, "
                f"{valor_expr} AS valor, "
                "CAST(w.winner_document AS STRING) AS cnpj_vencedor, "
                "CAST('https://basedosdados.org/dataset/world-wb-mides' AS STRING) AS url "
                f"FROM `{dataset}.licitacao` l "
                "LEFT JOIN winners w "
                "ON w.id_licitacao = l.id_licitacao "
                "AND w.id_municipio = l.id_municipio "
                "AND w.sigla_uf = l.sigla_uf "
                "AND w.orgao = l.orgao "
                "AND w.id_unidade_gestora = l.id_unidade_gestora "
                f"{year_filter_licitacao} "
                f"{data_publicacao_filter}"
            ),
            "contrato.csv": (
                winners_cte
                + "SELECT "
                "CAST(l.id_licitacao AS STRING) AS contrato_id, "
                "CAST(l.id_licitacao AS STRING) AS numero_contrato, "
                "CAST(l.id_licitacao AS STRING) AS licitacao_id, "
                "CAST(l.id_licitacao AS STRING) AS numero_processo, "
                "CAST(l.id_municipio AS STRING) AS cod_ibge, "
                "CAST('' AS STRING) AS municipio, "
                "CAST(l.sigla_uf AS STRING) AS estado, "
                f"{data_assinatura_expr} AS data_assinatura, "
                "CAST(l.descricao_objeto AS STRING) AS objeto, "
                f"{valor_expr} AS valor, "
                "CAST(w.winner_document AS STRING) AS cnpj_fornecedor, "
                "CAST('https://basedosdados.org/dataset/world-wb-mides' AS STRING) AS url "
                f"FROM `{dataset}.licitacao` l "
                "LEFT JOIN winners w "
                "ON w.id_licitacao = l.id_licitacao "
                "AND w.id_municipio = l.id_municipio "
                "AND w.sigla_uf = l.sigla_uf "
                "AND w.orgao = l.orgao "
                "AND w.id_unidade_gestora = l.id_unidade_gestora "
                f"{year_filter_licitacao} "
                f"{data_assinatura_filter}"
            ),
            "item.csv": (
                "SELECT "
                "CAST(i.id_licitacao AS STRING) AS contrato_id, "
                "CAST(i.id_licitacao AS STRING) AS licitacao_id, "
                "CAST(i.id_item_bd AS STRING) AS id_item, "
                "CAST(i.numero AS STRING) AS numero_item, "
                "CAST(i.descricao AS STRING) AS descricao, "
                "CAST(i.quantidade AS FLOAT64) AS quantidade, "
                "CAST(i.valor_unitario AS FLOAT64) AS valor_unitario, "
                "CAST(COALESCE(i.valor_total, i.valor_vencedor) AS FLOAT64) AS valor_total, "
                "CAST(i.documento AS STRING) AS cnpj_vencedor "
                f"FROM `{dataset}.licitacao_item` i "
                f"{year_filter_items}"
            ),
        }
    else:
        profile = "legacy_br_mides"
        year_filter = f"WHERE SAFE_CAST(ano AS INT64) BETWEEN {start_year} AND {end_year}"
        queries = {
            "licitacao.csv": f"SELECT * FROM `{dataset}.licitacao` {year_filter}",
            "contrato.csv": f"SELECT * FROM `{dataset}.contrato` {year_filter}",
            "item.csv": f"SELECT * FROM `{dataset}.item` {year_filter}",
        }

    logger.info("MiDES download profile=%s dataset=%s", profile, dataset)

    tables: list[dict[str, Any]] = []

    for filename, query in queries.items():
        table_name = filename.replace(".csv", "")
        entry = {
            "table": table_name,
            "file": filename,
            "status": "failed",
            "rows": 0,
            "error": "",
        }
        try:
            rows = _run_query_to_csv(
                billing_project,
                query,
                out / filename,
                skip_existing=skip_existing,
            )
            if rows == -1:
                entry["status"] = "skipped_existing"
            else:
                entry["status"] = "ok"
                entry["rows"] = rows
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed %s: %s", filename, exc)
            entry["error"] = str(exc)
        tables.append(entry)

    _write_manifest(out, tables)
    successful = sum(1 for t in tables if t["status"] in {"ok", "skipped_existing"})
    if successful == 0:
        raise click.ClickException(
            "No canonical MiDES tables downloaded successfully (0/3).",
        )


if __name__ == "__main__":
    main()
