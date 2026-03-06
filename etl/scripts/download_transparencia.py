#!/usr/bin/env python3
"""Download Portal da Transparencia data — contracts, servidores, emendas.

Usage:
    python etl/scripts/download_transparencia.py --year 2025
    python etl/scripts/download_transparencia.py --year 2025 --datasets compras,servidores
    python etl/scripts/download_transparencia.py --year 2025 --months 1 2 3
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import click
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
from _download_utils import download_file, extract_zip

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

BASE_URL = "https://portaldatransparencia.gov.br/download-de-dados"

# ── Column mappings: real government CSV → pipeline expected ─────────

CONTRATO_COLS = {
    "Código Contratado": "cnpj_contratada",
    "Nome Contratado": "razao_social",
    "Objeto": "objeto",
    "Valor Inicial Compra": "valor",
    "Nome Órgão": "orgao_contratante",
    "Data Assinatura Contrato": "data_inicio",
}

# Servidores: two files joined on Id_SERVIDOR_PORTAL
# Real SIAPE column names (quotes stripped by pandas)
SERVIDOR_CADASTRO_COLS = {
    "Id_SERVIDOR_PORTAL": "_join_id",
    "CPF": "cpf",
    "NOME": "nome",
    "ORG_EXERCICIO": "orgao",
}

SERVIDOR_REMUNERACAO_COLS = {
    "Id_SERVIDOR_PORTAL": "_join_id",
    "REMUNERAÇÃO BÁSICA BRUTA (R$)": "remuneracao",
}

EMENDA_COLS = {
    "Nome do Autor da Emenda": "nome_autor",
    "Código do Autor da Emenda": "codigo_autor",
    "Nome Ação": "objeto",
    "Valor Pago": "valor",
}


def _find_csvs(directory: Path, pattern: str = "*.csv") -> list[Path]:
    return sorted(directory.glob(pattern))


def _read_csv_safe(path: Path, sep: str = ";", encoding: str = "latin-1") -> pd.DataFrame | None:
    try:
        return pd.read_csv(path, sep=sep, encoding=encoding, dtype=str, keep_default_na=False)
    except Exception as e:
        logger.warning("Failed to read %s: %s", path.name, e)
        return None


def _download_monthly(
    dataset: str,
    year: int,
    months: list[int],
    raw_dir: Path,
    *,
    skip_existing: bool,
    timeout: int,
) -> list[Path]:
    """Download monthly ZIPs and return extracted CSV paths."""
    all_csvs: list[Path] = []
    for month in months:
        date_str = f"{year}{month:02d}"
        url = f"{BASE_URL}/{dataset}/{date_str}"
        name = f"{dataset}_{date_str}"
        zip_path = raw_dir / f"{name}.zip"

        if skip_existing and zip_path.exists():
            logger.info("Skipping (exists): %s", zip_path.name)
        else:
            if not download_file(url, zip_path, timeout=timeout):
                continue

        extract_dir = raw_dir / f"{name}_extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        extracted = extract_zip(zip_path, extract_dir)
        all_csvs.extend(f for f in extracted if f.suffix.lower() == ".csv")

    return all_csvs


def _download_yearly(
    dataset: str, year: int, raw_dir: Path, *, skip_existing: bool, timeout: int,
) -> list[Path]:
    """Download yearly ZIP and return extracted CSV paths."""
    url = f"{BASE_URL}/{dataset}/{year}"
    name = f"{dataset}_{year}"
    zip_path = raw_dir / f"{name}.zip"

    if skip_existing and zip_path.exists():
        logger.info("Skipping (exists): %s", zip_path.name)
    else:
        if not download_file(url, zip_path, timeout=timeout):
            return []

    extract_dir = raw_dir / f"{name}_extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    extracted = extract_zip(zip_path, extract_dir)
    return [f for f in extracted if f.suffix.lower() == ".csv"]


def _remap_concat(
    csvs: list[Path], col_map: dict[str, str], sep: str = ";", encoding: str = "latin-1",
) -> pd.DataFrame:
    """Read multiple CSVs, remap columns, concatenate."""
    frames = []
    for csv_path in csvs:
        df = _read_csv_safe(csv_path, sep=sep, encoding=encoding)
        if df is None:
            continue
        available = {real: pipe for real, pipe in col_map.items() if real in df.columns}
        if available:
            frames.append(df[list(available.keys())].rename(columns=available))
        else:
            logger.warning("%s: no matching columns found", csv_path.name)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


# ── Dataset processors ───────────────────────────────────────────────


def process_compras(
    year: int,
    months: list[int],
    raw_dir: Path,
    output_dir: Path,
    *,
    skip_existing: bool,
    timeout: int,
) -> bool:
    """Download and process government contract data."""
    logger.info("--- Compras (contracts) ---")
    csvs = _download_monthly(
        "compras", year, months, raw_dir, skip_existing=skip_existing, timeout=timeout,
    )
    if not csvs:
        logger.warning("No contract CSVs downloaded")
        return False

    # Only process *_Compras.csv files — ZIPs also contain ItemCompra,
    # TermoAditivo, Apostilamento which lack CNPJ columns.
    compras_csvs = [f for f in csvs if "_Compras" in f.name]
    if not compras_csvs:
        logger.warning("No *_Compras.csv files found in extracted data")
        return False

    df = _remap_concat(compras_csvs, CONTRATO_COLS)
    if df.empty:
        return False

    output_path = output_dir / "contratos.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Wrote %d contract rows to %s", len(df), output_path)
    return True


def process_servidores(
    year: int,
    months: list[int],
    raw_dir: Path,
    output_dir: Path,
    *,
    skip_existing: bool,
    timeout: int,
) -> bool:
    """Download servidores, join Cadastro + Remuneracao on ID_SERVIDOR_PORTAL."""
    logger.info("--- Servidores ---")
    csvs = _download_monthly(
        "servidores", year, months, raw_dir, skip_existing=skip_existing, timeout=timeout,
    )
    if not csvs:
        logger.warning("No servidor CSVs downloaded")
        return False

    # Servidores ZIP contains Cadastro and Remuneracao files
    cadastro_csvs = [f for f in csvs if "Cadastro" in f.name or "cadastro" in f.name]
    remuneracao_csvs = [f for f in csvs if "Remunerac" in f.name or "remunerac" in f.name]

    if not cadastro_csvs:
        # Fallback: try all CSVs as cadastro
        logger.warning("No Cadastro files found, using all CSVs")
        cadastro_csvs = csvs

    df_cadastro = _remap_concat(cadastro_csvs, SERVIDOR_CADASTRO_COLS)
    if df_cadastro.empty:
        logger.warning("Empty cadastro data")
        return False

    if remuneracao_csvs:
        df_remuneracao = _remap_concat(remuneracao_csvs, SERVIDOR_REMUNERACAO_COLS)
        if not df_remuneracao.empty and "_join_id" in df_remuneracao.columns:
            df_cadastro = df_cadastro.merge(
                df_remuneracao[["_join_id", "remuneracao"]],
                on="_join_id",
                how="left",
            )

    # Drop join key, fill missing remuneracao
    if "_join_id" in df_cadastro.columns:
        df_cadastro = df_cadastro.drop(columns=["_join_id"])
    if "remuneracao" not in df_cadastro.columns:
        df_cadastro["remuneracao"] = "0"

    output_path = output_dir / "servidores.csv"
    df_cadastro.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Wrote %d servidor rows to %s", len(df_cadastro), output_path)
    return True


def process_emendas(
    year: int,
    raw_dir: Path,
    output_dir: Path,
    *,
    skip_existing: bool,
    timeout: int,
) -> bool:
    """Download and process parliamentary amendments (yearly, not monthly)."""
    logger.info("--- Emendas parlamentares ---")
    csvs = _download_yearly(
        "emendas-parlamentares", year, raw_dir, skip_existing=skip_existing, timeout=timeout,
    )
    if not csvs:
        logger.warning("No emendas CSVs downloaded")
        return False

    df = _remap_concat(csvs, EMENDA_COLS)
    if df.empty:
        return False

    output_path = output_dir / "emendas.csv"
    df.to_csv(output_path, index=False, encoding="utf-8")
    logger.info("Wrote %d emenda rows to %s", len(df), output_path)
    return True


# ── CLI ──────────────────────────────────────────────────────────────


@click.command()
@click.option("--year", type=int, default=2025, help="Year to download")
@click.option(
    "--months",
    multiple=True,
    type=int,
    default=list(range(1, 13)),
    help="Months to download for monthly datasets",
)
@click.option(
    "--datasets",
    default="compras,servidores,emendas",
    help="Comma-separated datasets to download",
)
@click.option("--output-dir", default="./data/transparencia", help="Output directory")
@click.option("--skip-existing/--no-skip-existing", default=True, help="Skip existing ZIPs")
@click.option("--timeout", type=int, default=600, help="Download timeout in seconds")
def main(
    year: int,
    months: tuple[int, ...],
    datasets: str,
    output_dir: str,
    skip_existing: bool,
    timeout: int,
) -> None:
    """Download Portal da Transparencia data."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    month_list = list(months)
    dataset_list = [d.strip() for d in datasets.split(",")]
    logger.info("=== Transparencia download: year=%d, datasets=%s ===", year, dataset_list)

    success_count = 0
    total = len(dataset_list)

    if "compras" in dataset_list and process_compras(
        year, month_list, raw_dir, out, skip_existing=skip_existing, timeout=timeout,
    ):
        success_count += 1

    if "servidores" in dataset_list and process_servidores(
        year, month_list, raw_dir, out, skip_existing=skip_existing, timeout=timeout,
    ):
        success_count += 1

    if "emendas" in dataset_list and process_emendas(
        year, raw_dir, out, skip_existing=skip_existing, timeout=timeout,
    ):
        success_count += 1

    logger.info("=== Done: %d/%d datasets downloaded ===", success_count, total)
    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
