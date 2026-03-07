#!/usr/bin/env python3
"""Download TSE electoral data — candidates and campaign donations.

Handles all election years from 2002–2024. The TSE changed URL patterns
and column names over time:

- Candidates: same column format (SQ_CANDIDATO, NR_CPF_CANDIDATO, etc.)
  across all years. File naming: consulta_cand_YYYY_UF.csv.

- Donations: THREE different URL + format eras:
  * 2002–2010, 2016: prestacao_contas/prestacao_contas_YYYY.zip
  * 2012, 2014: prestacao_contas/prestacao_final_YYYY.zip
  * 2018+: prestacao_contas/prestacao_de_contas_eleitorais_candidatos_YYYY.zip

  Column names also differ:
  * 2018+: coded (SQ_CANDIDATO, NR_CPF_CNPJ_DOADOR, VR_RECEITA, AA_ELEICAO)
  * Pre-2018: Portuguese ("Sequencial Candidato", "CPF/CNPJ do doador",
    "Valor receita" — no year column; extracted from ZIP filename)

  File structures inside ZIPs differ too:
  * 2002–2010: nested dirs (candidato/UF/ReceitasCandidatos.txt)
  * 2012+: flat (receitas_candidatos_YYYY_UF.txt/.csv)

Usage:
    python etl/scripts/download_tse.py --years 2024
    python etl/scripts/download_tse.py --years 2002 2004 2006 2008 2010 2012 2014 2016 2018 2020 2022 2024
    python etl/scripts/download_tse.py --output-dir ./data/tse --years 2022
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

TSE_CDN = "https://cdn.tse.jus.br/estatistica/sead/odsele"

# ── Candidate column mapping (consistent across all years) ────────────

CANDIDATO_COLS = {
    "SQ_CANDIDATO": "sq_candidato",
    "NR_CPF_CANDIDATO": "cpf",
    "NM_CANDIDATO": "nome",
    "DS_CARGO": "cargo",
    "SG_UF": "uf",
    "NM_UE": "municipio",
    "ANO_ELEICAO": "ano",
    "SG_PARTIDO": "partido",
    "NR_CANDIDATO": "nr_candidato",
}

# ── Donation column mappings (two eras) ───────────────────────────────

# 2018+ format: coded column names
DOACAO_COLS_NEW = {
    "SQ_CANDIDATO": "sq_candidato",
    "NR_CPF_CNPJ_DOADOR": "cpf_cnpj_doador",
    "NM_DOADOR": "nome_doador",
    "VR_RECEITA": "valor",
    "AA_ELEICAO": "ano",
    "NM_CANDIDATO": "nome_candidato",
    "SG_PARTIDO": "partido",
    "NR_CANDIDATO": "nr_candidato",
}

# Pre-2018 format: Portuguese column names (2010-2016)
DOACAO_COLS_LEGACY = {
    "Sequencial Candidato": "sq_candidato",
    "CPF/CNPJ do doador": "cpf_cnpj_doador",
    "Nome do doador": "nome_doador",
    "Valor receita": "valor",
    "Nome candidato": "nome_candidato",
    # Partido has inconsistent spacing across years; handled in _detect_partido_col
}

# Early format: uppercase/underscored column names (2002-2008)
# Column names vary per year, so we try multiple variants for each field.
DOACAO_COLS_EARLY_VARIANTS: dict[str, list[str]] = {
    "sq_candidato": ["SEQUENCIAL_CANDIDATO"],
    "cpf_cnpj_doador": ["CD_CPF_CNPJ_DOADOR", "CD_CPF_CGC", "CD_CPF_CGC_DOA", "NUMERO_CPF_CGC_DOADOR"],
    "nome_doador": ["NM_DOADOR", "NO_DOADOR", "NOME_DOADOR"],
    "valor": ["VR_RECEITA", "VALOR_RECEITA"],
    "nome_candidato": ["NM_CANDIDATO", "NO_CAND", "NOME_CANDIDATO"],
    "partido": ["SG_PARTIDO", "SG_PART", "SIGLA_PARTIDO"],
}


def _donation_url(year: int) -> str:
    """Map election year → correct TSE CDN URL for donation data."""
    if year >= 2018:
        return (
            f"{TSE_CDN}/prestacao_contas/"
            f"prestacao_de_contas_eleitorais_candidatos_{year}.zip"
        )
    if year in (2012, 2014):
        return f"{TSE_CDN}/prestacao_contas/prestacao_final_{year}.zip"
    # 2002–2010, 2016
    return f"{TSE_CDN}/prestacao_contas/prestacao_contas_{year}.zip"


def _download_and_extract(
    url: str, name: str, raw_dir: Path, *, skip_existing: bool, timeout: int,
) -> list[Path]:
    """Download ZIP and extract, returning all extracted file paths."""
    zip_path = raw_dir / f"{name}.zip"
    if skip_existing and zip_path.exists():
        logger.info("Skipping (exists): %s", zip_path.name)
    else:
        if not download_file(url, zip_path, timeout=timeout):
            return []

    extract_dir = raw_dir / f"{name}_extracted"
    extract_dir.mkdir(parents=True, exist_ok=True)
    return extract_zip(zip_path, extract_dir)


def _find_candidate_csvs(extracted: list[Path]) -> list[Path]:
    """Filter for candidate CSV files."""
    return [f for f in extracted if f.suffix.lower() == ".csv"]


def _find_receita_files(extracted: list[Path]) -> list[Path]:
    """Find receitas (donation receipt) files across all TSE ZIP layouts.

    Handles:
    - 2002–2006: nested YYYY/Candidato/Receita/ReceitaCandidato.csv
    - 2008: flat receitas_candidatos_YYYY_brasil.csv
    - 2010: nested candidato/UF/ReceitasCandidatos.txt
    - 2012–2014: flat receitas_candidatos_YYYY_UF.txt
    - 2016+: flat receitas_candidatos_YYYY_UF.csv or .txt
    """
    result = []
    for f in extracted:
        name_lower = f.name.lower()
        if f.is_dir():
            continue
        # Match 2002-2006 format: ReceitaCandidato.csv
        if name_lower == "receitacandidato.csv" or name_lower == "receitascandidatos.txt" or name_lower.startswith("receitas_candidatos"):
            result.append(f)
    return result


def _concat_state_csvs(
    csv_paths: list[Path], encoding: str = "latin-1",
) -> pd.DataFrame:
    """TSE distributes data as per-state files. Concatenate them."""
    frames = []
    for path in csv_paths:
        try:
            df = pd.read_csv(
                path, sep=";", encoding=encoding, dtype=str, keep_default_na=False,
            )
            frames.append(df)
        except Exception as e:
            logger.warning("Skipping %s: %s", path.name, e)
    if not frames:
        return pd.DataFrame()
    combined = pd.concat(frames, ignore_index=True)
    logger.info("Concatenated %d files → %d rows", len(frames), len(combined))
    return combined


def _detect_donation_format(df: pd.DataFrame) -> str:
    """Detect whether a donation DataFrame uses new, legacy, or early column names."""
    if "SQ_CANDIDATO" in df.columns:
        return "new"
    if "Sequencial Candidato" in df.columns:
        return "legacy"
    # Early format (2002-2008): uppercase underscored, check for any known variant
    early_indicators = {"SEQUENCIAL_CANDIDATO", "VR_RECEITA", "VALOR_RECEITA", "CD_CPF_CGC", "CD_CPF_CGC_DOA"}
    if early_indicators & set(df.columns):
        return "early"
    logger.warning("Unknown donation format. Columns: %s", list(df.columns)[:10])
    return "unknown"


def _detect_partido_col(df: pd.DataFrame) -> str | None:
    """Find the partido column in legacy format (has inconsistent spacing)."""
    for col in df.columns:
        if "sigla" in col.lower() and "partido" in col.lower():
            return col
    return None


def _remap_early_donations(df: pd.DataFrame) -> dict[str, str]:
    """Build column map for early-format (2002-2008) donations by matching variants."""
    col_map: dict[str, str] = {}
    cols = set(df.columns)
    for target, variants in DOACAO_COLS_EARLY_VARIANTS.items():
        for variant in variants:
            if variant in cols:
                col_map[variant] = target
                break
    return col_map


def _remap_donations(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """Remap donation columns to pipeline-expected names, handling all three formats."""
    fmt = _detect_donation_format(df)

    if fmt == "new":
        col_map = dict(DOACAO_COLS_NEW)
    elif fmt == "legacy":
        col_map = dict(DOACAO_COLS_LEGACY)
        partido_col = _detect_partido_col(df)
        if partido_col:
            col_map[partido_col] = "partido"
    elif fmt == "early":
        col_map = _remap_early_donations(df)
    else:
        logger.warning("Skipping year %d: unknown donation format", year)
        return pd.DataFrame()

    available = {real: pipe for real, pipe in col_map.items() if real in df.columns}
    if not available:
        logger.warning("Year %d: no matching columns after remapping", year)
        return pd.DataFrame()

    mapped = df[list(available.keys())].rename(columns=available)

    # Legacy/early format has no year column — inject it
    if "ano" not in mapped.columns:
        mapped["ano"] = str(year)

    return mapped


def _remap_and_write(
    df: pd.DataFrame, col_map: dict[str, str], output_path: Path, dataset: str,
) -> bool:
    """Remap columns and write pipeline-ready CSV."""
    available = {real: pipe for real, pipe in col_map.items() if real in df.columns}
    missing = set(col_map) - set(available)
    if missing:
        logger.warning("%s: missing source columns: %s", dataset, missing)

    mapped = df[list(available.keys())].rename(columns=available)
    mapped.to_csv(output_path, index=False, encoding="latin-1")
    logger.info("Wrote %d rows to %s", len(mapped), output_path)
    return True


# ── Download orchestrators ────────────────────────────────────────────


def _download_candidates(
    years: list[int], raw_dir: Path, output_dir: Path, *, skip_existing: bool, timeout: int,
) -> bool:
    """Download and process candidate data for given election years."""
    all_csvs: list[Path] = []
    for year in years:
        url = f"{TSE_CDN}/consulta_cand/consulta_cand_{year}.zip"
        extracted = _download_and_extract(
            url, f"candidatos_{year}", raw_dir, skip_existing=skip_existing, timeout=timeout,
        )
        csvs = _find_candidate_csvs(extracted)
        all_csvs.extend(csvs)

    if not all_csvs:
        logger.warning("No candidate CSVs downloaded")
        return False

    df = _concat_state_csvs(all_csvs)
    if df.empty:
        return False

    return _remap_and_write(df, CANDIDATO_COLS, output_dir / "candidatos.csv", "candidatos")


def _download_donations(
    years: list[int], raw_dir: Path, output_dir: Path, *, skip_existing: bool, timeout: int,
) -> bool:
    """Download and process campaign donation data for given election years."""
    all_frames: list[pd.DataFrame] = []

    for year in years:
        url = _donation_url(year)
        extracted = _download_and_extract(
            url, f"doacoes_{year}", raw_dir, skip_existing=skip_existing, timeout=timeout,
        )
        receita_files = _find_receita_files(extracted)

        if not receita_files:
            logger.warning("Year %d: no receitas files found in ZIP", year)
            continue

        logger.info("Year %d: found %d receitas files", year, len(receita_files))
        df_year = _concat_state_csvs(receita_files)
        if df_year.empty:
            continue

        mapped = _remap_donations(df_year, year)
        if not mapped.empty:
            all_frames.append(mapped)
            logger.info("Year %d: %d donation rows mapped", year, len(mapped))

    if not all_frames:
        logger.warning("No donation data downloaded")
        return False

    combined = pd.concat(all_frames, ignore_index=True)
    output_path = output_dir / "doacoes.csv"
    combined.to_csv(output_path, index=False, encoding="latin-1")
    logger.info("Wrote %d total donation rows to %s", len(combined), output_path)
    return True


@click.command()
@click.option(
    "--years",
    multiple=True,
    type=int,
    default=[2024],
    help="Election years to download (e.g. --years 2018 --years 2022)",
)
@click.option("--output-dir", default="./data/tse", help="Output directory")
@click.option("--skip-existing/--no-skip-existing", default=True, help="Skip existing ZIPs")
@click.option("--timeout", type=int, default=600, help="Download timeout in seconds")
@click.option("--candidates-only", is_flag=True, help="Download only candidates (skip donations)")
@click.option("--donations-only", is_flag=True, help="Download only donations (skip candidates)")
def main(
    years: tuple[int, ...],
    output_dir: str,
    skip_existing: bool,
    timeout: int,
    candidates_only: bool,
    donations_only: bool,
) -> None:
    """Download TSE candidate and donation data."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    year_list = list(years)
    logger.info("=== TSE download: years %s ===", year_list)

    success_count = 0
    if not donations_only and _download_candidates(
        year_list, raw_dir, out, skip_existing=skip_existing, timeout=timeout,
    ):
        success_count += 1

    if not candidates_only and _download_donations(
        year_list, raw_dir, out, skip_existing=skip_existing, timeout=timeout,
    ):
        success_count += 1

    logger.info("=== Done: %d dataset(s) downloaded ===", success_count)
    if success_count == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
