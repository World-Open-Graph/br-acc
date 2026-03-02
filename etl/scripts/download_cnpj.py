#!/usr/bin/env python3
"""Download CNPJ data from Receita Federal open data portal.

Usage:
    python etl/scripts/download_cnpj.py                    # download all (reference + main)
    python etl/scripts/download_cnpj.py --reference-only   # reference tables only (tiny)
    python etl/scripts/download_cnpj.py --files 1          # just first file of each type
    python etl/scripts/download_cnpj.py --types Empresas   # specific type only
    python etl/scripts/download_cnpj.py --release 2026-03  # pin to specific monthly release
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click
import httpx

sys.path.insert(0, str(Path(__file__).parent))
from _download_utils import download_file, extract_zip, validate_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Receita Federal Nextcloud (primary since Jan 2026)
NEXTCLOUD_BASE = "https://arquivos.receitafederal.gov.br/s/{token}/download?path=%2F&files="
KNOWN_TOKENS = ["gn672Ad4CF8N6TK", "YggdBLfdninEJX9"]

# Legacy URLs (dadosabertos.rfb.gov.br decommissioned Jan 2026)
LEGACY_NEW_BASE_PATTERN = "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/{year_month}/"
LEGACY_BASE_URL = "https://dadosabertos.rfb.gov.br/CNPJ/"

MAIN_TYPES = ["Empresas", "Socios", "Estabelecimentos"]
REFERENCE_FILES = [
    "Naturezas.zip",
    "Qualificacoes.zip",
    "Cnaes.zip",
    "Municipios.zip",
    "Paises.zip",
    "Motivos.zip",
]


EXPECTED_COLS = {
    "EMPRE": 7,
    "SOCIO": 11,
    "ESTABELE": 30,
    "Naturezas": 2,
    "Qualificacoes": 2,
    "Cnaes": 2,
    "Municipios": 2,
    "Paises": 2,
    "Motivos": 2,
}


def _previous_month(year: int, month: int) -> tuple[int, int]:
    """Return (year, month) for the previous month."""
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _check_url_accessible(url: str, timeout: int = 30) -> bool:
    """Send HTTP HEAD to verify a URL is accessible (2xx)."""
    try:
        resp = httpx.head(url, follow_redirects=True, timeout=timeout)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def _check_nextcloud_token(token: str, timeout: int = 30) -> bool:
    """Verify a Nextcloud share token is valid via HEAD request."""
    share_url = f"https://arquivos.receitafederal.gov.br/s/{token}"
    try:
        resp = httpx.head(share_url, follow_redirects=True, timeout=timeout)
        return resp.status_code < 400
    except httpx.HTTPError:
        return False


def resolve_rf_release(year_month: str | None = None) -> str:
    """Resolve the Receita Federal CNPJ release URL.

    Strategy:
    1. Try Nextcloud share (primary since Jan 2026):
       a. Check CNPJ_SHARE_TOKEN env var first.
       b. Then try each known token.
    2. Fall back to legacy dadosabertos.rfb.gov.br paths.
    3. Raise RuntimeError if nothing works (fail-closed).

    Returns the resolved base URL. For Nextcloud, files are fetched via
    ``{base_url}{filename}``.
    """
    now = datetime.now(timezone.utc)

    # --- Nextcloud (primary) ---
    tokens_to_try: list[str] = []

    env_token = os.environ.get("CNPJ_SHARE_TOKEN")
    if env_token:
        tokens_to_try.append(env_token)

    for t in KNOWN_TOKENS:
        if t not in tokens_to_try:
            tokens_to_try.append(t)

    for token in tokens_to_try:
        logger.info("Probing Nextcloud token: %s...", token[:6])
        if _check_nextcloud_token(token):
            base_url = NEXTCLOUD_BASE.format(token=token)
            logger.info("Resolved CNPJ via Nextcloud (token %s...)", token[:6])
            return base_url

    # --- Legacy dadosabertos.rfb.gov.br ---
    if year_month is not None:
        candidates = [year_month]
    else:
        current = f"{now.year:04d}-{now.month:02d}"
        prev_y, prev_m = _previous_month(now.year, now.month)
        previous = f"{prev_y:04d}-{prev_m:02d}"
        candidates = [current, previous]

    for ym in candidates:
        url = LEGACY_NEW_BASE_PATTERN.format(year_month=ym)
        logger.info("Probing legacy release URL: %s", url)
        if _check_url_accessible(url):
            logger.info("Resolved CNPJ release (legacy new path): %s", url)
            return url

    logger.info("Trying legacy flat URL: %s", LEGACY_BASE_URL)
    if _check_url_accessible(LEGACY_BASE_URL):
        logger.info("Resolved CNPJ release (legacy flat): %s", LEGACY_BASE_URL)
        return LEGACY_BASE_URL

    tried = ", ".join(candidates)
    raise RuntimeError(
        f"Could not resolve CNPJ release. Tried Nextcloud tokens, "
        f"legacy months [{tried}], and legacy flat path. "
        "Receita Federal portal may be down or the URL structure has changed."
    )


def _write_manifest(
    output_dir: Path,
    base_url: str,
    resolved_release: str,
    file_results: list[dict],
    started_at: str,
) -> Path:
    """Write download manifest JSON after download completes."""
    finished_at = datetime.now(timezone.utc).isoformat()

    # Compute an aggregate checksum over all successful file names + sizes
    hasher = hashlib.sha256()
    for fr in sorted(file_results, key=lambda x: x["name"]):
        hasher.update(f"{fr['name']}:{fr['size_bytes']}:{fr['status']}".encode())
    checksum = f"sha256:{hasher.hexdigest()}"

    manifest = {
        "source": "receita_federal_cnpj",
        "resolved_release": resolved_release,
        "base_url": base_url,
        "files": file_results,
        "started_at": started_at,
        "finished_at": finished_at,
        "checksum": checksum,
    }

    manifest_path = output_dir / "download_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Manifest written: %s", manifest_path)
    return manifest_path


@click.command()
@click.option("--output-dir", default="./data/cnpj", help="Base output directory")
@click.option("--files", type=int, default=10, help="Number of files per type (0-9)")
@click.option("--types", multiple=True, help="Specific types to download (Empresas, Socios, etc.)")
@click.option("--reference-only", is_flag=True, help="Download only reference tables")
@click.option("--skip-existing/--no-skip-existing", default=True, help="Skip already downloaded files")
@click.option("--skip-extract", is_flag=True, help="Skip extraction after download")
@click.option("--timeout", type=int, default=600, help="Download timeout in seconds")
@click.option("--release", default=None, help="Pin to specific monthly release (YYYY-MM format)")
def main(
    output_dir: str,
    files: int,
    types: tuple[str, ...],
    reference_only: bool,
    skip_existing: bool,
    skip_extract: bool,
    timeout: int,
    release: str | None,
) -> None:
    """Download and extract CNPJ data from Receita Federal."""
    started_at = datetime.now(timezone.utc).isoformat()

    base_url = resolve_rf_release(release)
    # Extract the release identifier from the resolved URL
    resolved_release = release or "legacy"
    if "arquivos.receitafederal.gov.br" in base_url:
        resolved_release = "nextcloud"
    elif "/dados_abertos_cnpj/" in base_url:
        # Extract YYYY-MM from URL
        resolved_release = base_url.rstrip("/").rsplit("/", 1)[-1]

    base = Path(output_dir)
    raw_dir = base / "raw"
    extract_dir = base / "extracted"
    ref_dir = base / "reference"
    for d in [raw_dir, extract_dir, ref_dir]:
        d.mkdir(parents=True, exist_ok=True)

    file_results: list[dict] = []

    # --- Reference tables (always download, they're tiny) ---
    logger.info("=== Reference tables ===")
    for filename in REFERENCE_FILES:
        dest = raw_dir / filename
        if skip_existing and dest.exists():
            logger.info("Skipping (exists): %s", filename)
            file_results.append({
                "name": filename,
                "status": "skipped",
                "size_bytes": dest.stat().st_size,
            })
        else:
            success = download_file(f"{base_url}{filename}", dest, timeout=timeout)
            file_results.append({
                "name": filename,
                "status": "ok" if success else "failed",
                "size_bytes": dest.stat().st_size if dest.exists() else 0,
            })

        if not skip_extract and dest.exists():
            extracted = extract_zip(dest, ref_dir)
            for f in extracted:
                table_name = f.stem.split(".")[0]
                expected = EXPECTED_COLS.get(table_name)
                validate_csv(f, expected_cols=expected)

    if reference_only:
        logger.info("Reference-only mode -- done.")
        _write_manifest(base, base_url, resolved_release, file_results, started_at)
        return

    # --- Main data files ---
    file_types = list(types) if types else MAIN_TYPES
    for file_type in file_types:
        logger.info("=== %s ===", file_type)
        for i in range(min(files, 10)):
            filename = f"{file_type}{i}.zip"
            dest = raw_dir / filename
            if skip_existing and dest.exists():
                logger.info("Skipping (exists): %s", filename)
                file_results.append({
                    "name": filename,
                    "status": "skipped",
                    "size_bytes": dest.stat().st_size,
                })
            else:
                success = download_file(f"{base_url}{filename}", dest, timeout=timeout)
                if not success:
                    file_results.append({
                        "name": filename,
                        "status": "failed",
                        "size_bytes": 0,
                    })
                    continue
                file_results.append({
                    "name": filename,
                    "status": "ok",
                    "size_bytes": dest.stat().st_size if dest.exists() else 0,
                })

            if not skip_extract and dest.exists():
                extracted = extract_zip(dest, extract_dir)
                for f in extracted:
                    # Determine expected column count from filename
                    expected = None
                    for key, cols in EXPECTED_COLS.items():
                        if key in f.name:
                            expected = cols
                            break
                    validate_csv(f, expected_cols=expected)

    logger.info("=== Download complete ===")
    _print_summary(raw_dir, extract_dir, ref_dir)
    _write_manifest(base, base_url, resolved_release, file_results, started_at)


def _print_summary(raw_dir: Path, extract_dir: Path, ref_dir: Path) -> None:
    """Print download summary with file counts and sizes."""
    for label, d in [("Raw ZIPs", raw_dir), ("Extracted", extract_dir), ("Reference", ref_dir)]:
        files = list(d.iterdir())
        total_size = sum(f.stat().st_size for f in files if f.is_file())
        logger.info(
            "%s: %d files, %.1f MB",
            label,
            len([f for f in files if f.is_file()]),
            total_size / 1e6,
        )


if __name__ == "__main__":
    main()
