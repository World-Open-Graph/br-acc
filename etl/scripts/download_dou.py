#!/usr/bin/env python3
"""Download DOU (Diario Oficial da Uniao) from Imprensa Nacional XML dumps.

Uses the official open data XML distribution from dadosabertos-download.cgu.gov.br.
Each month has 3 ZIP files (one per DOU section), each containing XML articles.

URL pattern: https://dadosabertos-download.cgu.gov.br/inlabs/{AAMM}/S0{section}{AAMM}.zip

Usage:
    python etl/scripts/download_dou.py
    python etl/scripts/download_dou.py --start-month 2024-01 --end-month 2024-12
    python etl/scripts/download_dou.py --skip-existing --output-dir ./data/dou
"""

from __future__ import annotations

import logging
import sys
import zipfile
from io import BytesIO
from pathlib import Path

import click
import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)

BASE_URL = "https://dadosabertos-download.cgu.gov.br/inlabs"
SECTIONS = [1, 2, 3]
TIMEOUT = 120


def _month_range(start: str, end: str) -> list[str]:
    """Generate AAMM strings from YYYY-MM to YYYY-MM inclusive."""
    sy, sm = start.split("-")
    ey, em = end.split("-")
    year, month = int(sy), int(sm)
    end_year, end_month = int(ey), int(em)

    months: list[str] = []
    while (year, month) <= (end_year, end_month):
        # AAMM format: last 2 digits of year + 2-digit month
        aamm = f"{year % 100:02d}{month:02d}"
        months.append(aamm)
        month += 1
        if month > 12:
            month = 1
            year += 1
    return months


def _download_zip(
    client: httpx.Client,
    aamm: str,
    section: int,
    output_dir: Path,
    *,
    skip_existing: bool,
) -> int:
    """Download and extract one section ZIP. Returns number of XML files extracted."""
    zip_name = f"S0{section}{aamm}.zip"
    url = f"{BASE_URL}/{aamm}/{zip_name}"

    # Check if already extracted
    section_dir = output_dir / f"S{section}" / aamm
    marker = section_dir / ".done"
    if skip_existing and marker.exists():
        logger.info("Skipping %s (already extracted)", zip_name)
        return 0

    logger.info("Downloading %s", url)
    try:
        resp = client.get(url, timeout=TIMEOUT)
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.warning("Not found: %s (month may not be available yet)", zip_name)
        else:
            logger.warning("HTTP %d for %s", e.response.status_code, zip_name)
        return 0
    except httpx.RequestError as e:
        logger.warning("Request failed for %s: %s", zip_name, e)
        return 0

    section_dir.mkdir(parents=True, exist_ok=True)
    xml_count = 0

    try:
        resolved_dir = section_dir.resolve()
        with zipfile.ZipFile(BytesIO(resp.content)) as zf:
            for member in zf.namelist():
                # Path traversal guard
                target = (section_dir / member).resolve()
                if not target.is_relative_to(resolved_dir):
                    logger.warning(
                        "Path traversal detected in %s: %s — skipping",
                        zip_name,
                        member,
                    )
                    continue
                if member.lower().endswith(".xml"):
                    zf.extract(member, section_dir)
                    xml_count += 1
    except zipfile.BadZipFile:
        logger.warning("Bad ZIP file: %s", zip_name)
        return 0

    if xml_count > 0:
        marker.write_text(str(xml_count))
        logger.info("Extracted %d XML files from %s", xml_count, zip_name)

    return xml_count


@click.command()
@click.option(
    "--start-month",
    default="2024-01",
    help="Start month (YYYY-MM)",
)
@click.option(
    "--end-month",
    default="2025-02",
    help="End month (YYYY-MM)",
)
@click.option("--output-dir", default="./data/dou", help="Output directory")
@click.option("--skip-existing/--no-skip-existing", default=True)
def main(
    start_month: str,
    end_month: str,
    output_dir: str,
    skip_existing: bool,
) -> None:
    """Download DOU XML dumps from Imprensa Nacional open data."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    months = _month_range(start_month, end_month)
    logger.info("=== DOU XML Download ===")
    logger.info("Months: %s to %s (%d months)", start_month, end_month, len(months))
    logger.info("Output: %s", out.resolve())

    total_xml = 0
    total_zips = 0

    with httpx.Client(follow_redirects=True) as client:
        for aamm in months:
            for section in SECTIONS:
                count = _download_zip(
                    client, aamm, section, out, skip_existing=skip_existing,
                )
                total_xml += count
                if count > 0:
                    total_zips += 1

    logger.info("=== Done ===")
    logger.info("Downloaded %d ZIPs, extracted %d XML files", total_zips, total_xml)

    if total_xml == 0:
        logger.warning(
            "No XML files extracted. The URL pattern may have changed. "
            "Check https://dadosabertos-download.cgu.gov.br/inlabs/ manually."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
