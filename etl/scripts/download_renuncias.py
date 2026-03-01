#!/usr/bin/env python3
"""Download Renúncias Fiscais (tax waivers) from Portal da Transparência.

Source: https://portaldatransparencia.gov.br/download-de-dados/renuncias
"""

from __future__ import annotations

import argparse
import logging
import zipfile
from pathlib import Path

import httpx
from _download_utils import safe_extract_zip

logger = logging.getLogger(__name__)

BASE_URL = "https://portaldatransparencia.gov.br/download-de-dados/renuncias"


def download_year(output_dir: Path, year: int) -> None:
    """Download renuncias for a given year."""
    url = f"{BASE_URL}/{year}"
    dest_zip = output_dir / f"renuncias_{year}.zip"

    if dest_zip.exists():
        logger.info("Skipping (exists): %s", dest_zip.name)
        return

    logger.info("Downloading %s...", url)
    try:
        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=300,
            headers={"User-Agent": "BRACC-ETL/1.0"},
        )
        response.raise_for_status()
        dest_zip.write_bytes(response.content)
        logger.info("Downloaded: %s (%d bytes)", dest_zip.name, len(response.content))

        with zipfile.ZipFile(dest_zip, "r") as zf:
            extracted = safe_extract_zip(zf, output_dir)
            logger.info("Extracted %d files", len(extracted))
    except httpx.HTTPError:
        logger.warning("Failed to download renuncias for %d", year)


def main() -> None:
    parser = argparse.ArgumentParser(description="Download Renúncias Fiscais data")
    parser.add_argument("--start-year", type=int, default=2020, help="Start year")
    parser.add_argument("--end-year", type=int, default=2024, help="End year")
    parser.add_argument("--output-dir", default="./data/renuncias", help="Output directory")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for year in range(args.start_year, args.end_year + 1):
        download_year(output_dir, year)


if __name__ == "__main__":
    main()
