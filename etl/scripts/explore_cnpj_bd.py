#!/usr/bin/env python3
"""Explore CNPJ data via Base dos Dados (BigQuery).

Requires:
    1. gcloud auth: `gcloud auth application-default login`
    2. basedosdados: `uv pip install basedosdados`

Usage:
    python etl/scripts/explore_cnpj_bd.py                        # explore all tables
    python etl/scripts/explore_cnpj_bd.py --export-state SP      # export SP subset to CSV
    python etl/scripts/explore_cnpj_bd.py --full-export           # export all 3 tables (no filter)
    python etl/scripts/explore_cnpj_bd.py --full-export --limit 500000  # full export with row cap
    python etl/scripts/explore_cnpj_bd.py --limit 50              # limit sample rows
"""

from __future__ import annotations

import logging
import sys

import click

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BD_DATASET = "br_me_cnpj"
TABLES = ["empresas", "socios", "estabelecimentos"]
# BigQuery has ~1MB query limit; chunk IN clauses to stay under it
IN_CLAUSE_BATCH_SIZE = 10_000


def _query(sql: str, billing_project: str | None = None) -> pd.DataFrame:
    """Execute a BigQuery SQL query via basedosdados."""
    import basedosdados as bd

    logger.info("Querying: %s", sql[:120])
    return bd.read_sql(sql, billing_project_id=billing_project)


def _explore_table(table: str, limit: int, billing_project: str | None) -> None:
    """Print schema, sample values, and null counts for a table."""
    import pandas as pd

    sql = f"SELECT * FROM `basedosdados.{BD_DATASET}.{table}` LIMIT {limit}"
    df = _query(sql, billing_project)

    print(f"\n{'=' * 60}")
    print(f"  TABLE: {BD_DATASET}.{table}")
    print(f"  Rows sampled: {len(df)}")
    print(f"{'=' * 60}")

    print(f"\n  Columns ({len(df.columns)}):")
    for col in df.columns:
        dtype = df[col].dtype
        nulls = df[col].isna().sum()
        sample = df[col].dropna().iloc[0] if not df[col].dropna().empty else "N/A"
        sample_str = str(sample)[:50]
        print(f"    {col:<40} {str(dtype):<10} nulls={nulls:<4} sample={sample_str}")

    print("\n  First 3 rows:")
    pd.set_option("display.max_columns", None)
    pd.set_option("display.width", 200)
    print(df.head(3).to_string(index=False))


def _query_batched_in(
    table: str,
    column: str,
    values: list[str],
    billing_project: str | None,
) -> pd.DataFrame:
    """Query a table with IN clause, batching to avoid BQ query size limits."""
    import pandas as pd

    frames: list[pd.DataFrame] = []
    total = len(values)
    for i in range(0, total, IN_CLAUSE_BATCH_SIZE):
        batch = values[i : i + IN_CLAUSE_BATCH_SIZE]
        in_str = ",".join(f"'{v}'" for v in batch)
        sql = (
            f"SELECT * FROM `basedosdados.{BD_DATASET}.{table}` "
            f"WHERE {column} IN ({in_str})"
        )
        logger.info("Batch %d/%d (%d values)", i // IN_CLAUSE_BATCH_SIZE + 1,
                     (total + IN_CLAUSE_BATCH_SIZE - 1) // IN_CLAUSE_BATCH_SIZE,
                     len(batch))
        frames.append(_query(sql, billing_project))
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _export_state_subset(
    state: str,
    output_dir: str,
    limit: int,
    billing_project: str | None,
) -> None:
    """Export a subset of data filtered by UF (state) to local CSV."""
    from pathlib import Path

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Estabelecimentos for state
    sql_estab = (
        f"SELECT * FROM `basedosdados.{BD_DATASET}.estabelecimentos` "
        f"WHERE sigla_uf = '{state}' LIMIT {limit}"
    )
    df_estab = _query(sql_estab, billing_project)
    estab_path = out / f"estabelecimentos_{state}.csv"
    df_estab.to_csv(estab_path, index=False)
    logger.info("Exported %d estabelecimentos to %s", len(df_estab), estab_path)

    # Get cnpj_basico values for joining (no cap — use all unique basicos)
    if not df_estab.empty and "cnpj_basico" in df_estab.columns:
        basicos = df_estab["cnpj_basico"].unique().tolist()
        logger.info("Found %d unique cnpj_basicos to join", len(basicos))

        df_emp = _query_batched_in("empresas", "cnpj_basico", basicos, billing_project)
        emp_path = out / f"empresas_{state}.csv"
        df_emp.to_csv(emp_path, index=False)
        logger.info("Exported %d empresas to %s", len(df_emp), emp_path)

        df_soc = _query_batched_in("socios", "cnpj_basico", basicos, billing_project)
        soc_path = out / f"socios_{state}.csv"
        df_soc.to_csv(soc_path, index=False)
        logger.info("Exported %d socios to %s", len(df_soc), soc_path)

    logger.info("Export complete for state %s", state)


def _export_full(
    output_dir: str,
    limit: int | None,
    billing_project: str | None,
) -> None:
    """Export all 3 tables directly — no state filter, no join logic."""
    from pathlib import Path

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for table in TABLES:
        limit_clause = f" LIMIT {limit}" if limit else ""
        sql = f"SELECT * FROM `basedosdados.{BD_DATASET}.{table}`{limit_clause}"
        df = _query(sql, billing_project)
        csv_path = out / f"{table}.csv"
        df.to_csv(csv_path, index=False)
        logger.info("Exported %d rows from %s to %s", len(df), table, csv_path)

    logger.info("Full export complete")


@click.command()
@click.option("--limit", type=int, default=None, help="Max rows per table (default: no limit)")
@click.option("--export-state", type=str, default=None, help="Export subset for state (e.g. DF, SP)")
@click.option("--full-export", is_flag=True, default=False, help="Export all 3 tables directly (no state filter)")
@click.option("--output-dir", default="./data/cnpj/extracted", help="Output directory for exports")
@click.option("--billing-project", type=str, default=None, help="GCP billing project ID")
def main(
    limit: int | None,
    export_state: str | None,
    full_export: bool,
    output_dir: str,
    billing_project: str | None,
) -> None:
    """Explore CNPJ data from Base dos Dados (BigQuery)."""
    try:
        import basedosdados  # noqa: F401
    except ImportError:
        logger.error("basedosdados not installed. Run: uv pip install 'basedosdados>=2.0.0'")
        sys.exit(1)

    if full_export:
        _export_full(output_dir, limit, billing_project)
    elif export_state:
        # State mode uses limit for estabelecimentos query (default: 100K)
        _export_state_subset(export_state, output_dir, limit or 100_000, billing_project)
    else:
        for table in TABLES:
            _explore_table(table, limit or 100, billing_project)


if __name__ == "__main__":
    main()
