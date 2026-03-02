#!/usr/bin/env python3
"""Download SICONFI municipal finance data from Tesouro Nacional API.

Fetches DCA (Declaracao de Contas Anuais) balance sheet data for all
Brazilian municipalities (~5,570) and states (27). Uses direct HTTP
calls to the Tesouro Nacional datalake API for speed.

API docs: https://apidatalake.tesouro.gov.br/ords/siconfi/tt/
No authentication required. Rate limit: be polite (~0.3s between calls).

Requires: pip install httpx
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
import time
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

BASE_URL = "https://apidatalake.tesouro.gov.br/ords/siconfi/tt"

# DCA-Anexo I-C = Balance sheet (revenue/expense by account)
DEFAULT_ANNEX = "DCA-Anexo I-C"


def get_all_entities() -> list[dict]:
    """Fetch all municipality/state IBGE codes from the entes endpoint."""
    url = f"{BASE_URL}/entes"
    logger.info("Fetching entity codes from %s ...", url)

    all_items: list[dict] = []
    offset = 0
    limit = 5000

    while True:
        response = httpx.get(
            url,
            params={"offset": offset, "limit": limit},
            timeout=60,
            headers={"User-Agent": "BR-ACC-ETL/1.0"},
        )
        response.raise_for_status()
        data = response.json()
        items = data.get("items", [])
        if not items:
            break
        all_items.extend(items)
        logger.info("  fetched %d entities (total %d)", len(items), len(all_items))
        if len(items) < limit:
            break
        offset += limit
        time.sleep(0.5)

    logger.info("Total entities: %d", len(all_items))
    return all_items


def fetch_dca(
    client: httpx.Client, cod_ibge: int, year: int, annex: str
) -> list[dict]:
    """Fetch DCA data for a single entity and year."""
    url = f"{BASE_URL}/dca"
    params = {
        "an_exercicio": year,
        "no_anexo": annex,
        "id_ente": cod_ibge,
    }
    response = client.get(url, params=params, timeout=120)
    response.raise_for_status()
    data = response.json()
    return data.get("items", [])


def download_year(
    output_dir: Path,
    year: int,
    entities: list[dict],
    annex: str,
    delay: float,
    file_prefix: str,
) -> None:
    """Download DCA for a list of entities for a given year.

    Supports resume via partial CSV files. Writes incrementally so
    progress is not lost if the process is interrupted.
    """
    dest = output_dir / f"{file_prefix}_{year}.csv"

    # Skip if final file already exists
    if dest.exists() and dest.stat().st_size > 1000:
        logger.info(
            "Skipping %s %d -- already exists (%s)",
            file_prefix, year, _human_size(dest.stat().st_size),
        )
        return

    # Partial resume support
    partial = output_dir / f"{file_prefix}_{year}.partial.csv"
    done_codes: set[int] = set()
    if partial.exists() and partial.stat().st_size > 0:
        with open(partial, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    done_codes.add(int(row.get("cod_ibge", 0)))
                except (ValueError, TypeError):
                    pass
        logger.info(
            "Resuming %s %d: %d entities already fetched",
            file_prefix, year, len(done_codes),
        )

    total = len(entities)
    fetched = 0
    empty = 0
    failed = 0
    rows_written = 0
    header_written = partial.exists() and partial.stat().st_size > 0

    with (
        httpx.Client(headers={"User-Agent": "BR-ACC-ETL/1.0"}) as client,
        open(partial, "a", newline="", encoding="utf-8") as f,
    ):
        writer: csv.DictWriter | None = None

        for i, entity in enumerate(entities, 1):
            cod = entity["cod_ibge"]

            if cod in done_codes:
                continue

            try:
                items = fetch_dca(client, cod, year, annex)
                fetched += 1

                if items:
                    if writer is None:
                        fieldnames = list(items[0].keys())
                        writer = csv.DictWriter(f, fieldnames=fieldnames)
                        if not header_written:
                            writer.writeheader()
                            header_written = True
                    for item in items:
                        writer.writerow(item)
                    rows_written += len(items)
                    f.flush()
                else:
                    empty += 1

                if fetched % 200 == 0:
                    logger.info(
                        "%s %d: %d/%d fetched, %d rows, %d empty, %d failed",
                        file_prefix, year, i, total, rows_written, empty, failed,
                    )

            except httpx.HTTPStatusError as e:
                failed += 1
                status = e.response.status_code
                if status == 429:
                    logger.warning(
                        "%s %d: rate limited at entity %d/%d, backing off 30s",
                        file_prefix, year, i, total,
                    )
                    time.sleep(30)
                elif status >= 500:
                    logger.warning(
                        "%s %d: server error %d for cod %d, skipping",
                        file_prefix, year, status, cod,
                    )
                    time.sleep(2)
                else:
                    logger.warning(
                        "%s %d: HTTP %d for cod %d",
                        file_prefix, year, status, cod,
                    )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                failed += 1
                logger.warning(
                    "%s %d: network error for cod %d: %s",
                    file_prefix, year, cod, e,
                )
                time.sleep(5)

            time.sleep(delay)

    logger.info(
        "%s %d complete: %d fetched, %d rows, %d empty, %d failed",
        file_prefix, year, fetched, rows_written, empty, failed,
    )

    # Rename partial to final
    if partial.exists() and partial.stat().st_size > 0:
        partial.rename(dest)
        logger.info(
            "%s %d: saved %s (%s)",
            file_prefix, year, dest.name, _human_size(dest.stat().st_size),
        )
    else:
        logger.warning("%s %d: no data collected", file_prefix, year)


def _human_size(nbytes: int | float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if nbytes < 1024:
            return f"{nbytes:.1f}{unit}"
        nbytes /= 1024
    return f"{nbytes:.1f}TB"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download SICONFI municipal finance data"
    )
    parser.add_argument(
        "--start-year", type=int, default=2020, help="Start year (default: 2020)"
    )
    parser.add_argument(
        "--end-year", type=int, default=2024, help="End year (default: 2024)"
    )
    parser.add_argument(
        "--output-dir", default="./data/siconfi", help="Output directory"
    )
    parser.add_argument("--annex", default=DEFAULT_ANNEX, help="DCA annex to fetch")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.3,
        help="Seconds between API calls (default: 0.3)",
    )
    parser.add_argument(
        "--states-only",
        action="store_true",
        help="Only fetch state-level data (27 entities)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Get entity codes from API
    all_entities = get_all_entities()

    states = [e for e in all_entities if e.get("esfera") == "E"]
    municipalities = [e for e in all_entities if e.get("esfera") == "M"]

    logger.info("Found %d states, %d municipalities", len(states), len(municipalities))
    logger.info(
        "Config: years %d-%d, annex=%s, delay=%.1fs",
        args.start_year,
        args.end_year,
        args.annex,
        args.delay,
    )

    # States first (quick, ~27 entities per year)
    for year in range(args.start_year, args.end_year + 1):
        logger.info("=== Year %d: States ===", year)
        download_year(output_dir, year, states, args.annex, args.delay, "dca_states")

    # Municipalities (slow, ~5,570 entities per year)
    if not args.states_only:
        for year in range(args.start_year, args.end_year + 1):
            logger.info("=== Year %d: Municipalities (%d entities) ===", year, len(municipalities))
            download_year(
                output_dir, year, municipalities, args.annex, args.delay, "dca_mun"
            )

    logger.info("Done. Files in %s", output_dir)


if __name__ == "__main__":
    main()
