#!/usr/bin/env python3
"""Download PNCP procurement bid publications via REST API.

Fetches data from the PNCP public API in date-range windows and saves
as JSON files for pipeline consumption.  Each (window, modalidade)
combination is checkpointed to disk immediately, so progress is never
lost on crash.  Use --skip-existing to resume interrupted runs.

API: https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao
Swagger: https://pncp.gov.br/api/consulta/swagger-ui/index.html

Usage:
    python etl/scripts/download_pncp.py
    python etl/scripts/download_pncp.py --start-date 2021-01-01 --end-date 2026-02-25
    python etl/scripts/download_pncp.py --output-dir ./data/pncp --modalidades 6,8,9
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path

import click
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"

# All PNCP modalidade codes (procurement types)
ALL_MODALIDADES = [1, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

# API constraints
MAX_PAGE_SIZE = 50
MAX_DATE_RANGE_DAYS = 10
REQUEST_DELAY_SECONDS = 1.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 5.0


def _fetch_page(
    client: httpx.Client,
    date_start: str,
    date_end: str,
    modalidade: int,
    page: int,
) -> dict | None:
    """Fetch a single page from the PNCP API.

    Returns parsed JSON dict, or None for empty responses (204, empty body).
    """
    params = {
        "dataInicial": date_start,
        "dataFinal": date_end,
        "codigoModalidadeContratacao": modalidade,
        "pagina": page,
        "tamanhoPagina": MAX_PAGE_SIZE,
    }
    response = client.get(API_BASE, params=params)

    # 204 No Content = no data for this combination
    if response.status_code == 204:
        return None

    response.raise_for_status()

    text = response.text.strip()
    if not text:
        return None

    # PNCP sometimes returns invalid control characters in JSON text fields
    return json.loads(text, strict=False)  # type: ignore[no-any-return]


def _fetch_window(
    client: httpx.Client,
    date_start: str,
    date_end: str,
    modalidade: int,
    *,
    page_workers: int = 1,
    request_delay_seconds: float = REQUEST_DELAY_SECONDS,
) -> list[dict]:
    """Fetch all pages for a single date window + modalidade combination."""
    def fetch_with_retry(page: int) -> dict | None:
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return _fetch_page(client, date_start, date_end, modalidade, page)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (400, 404):
                    # No data or invalid range
                    return None
                if e.response.status_code == 429:
                    wait = RETRY_BACKOFF_SECONDS * attempt * 2
                    logger.warning(
                        "Rate limited (429) for %s-%s mod=%d page=%d, "
                        "waiting %.0fs (attempt %d/%d)",
                        date_start, date_end, modalidade, page,
                        wait, attempt, MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "HTTP %d for %s-%s mod=%d page=%d (attempt %d/%d)",
                        e.response.status_code, date_start, date_end,
                        modalidade, page, attempt, MAX_RETRIES,
                    )
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                logger.warning(
                    "Giving up on %s-%s mod=%d page=%d after %d attempts: %s",
                    date_start, date_end, modalidade, page, MAX_RETRIES, e,
                )
                return None
            except httpx.HTTPError as e:
                if attempt < MAX_RETRIES:
                    logger.warning(
                        "Network error for %s-%s mod=%d page=%d "
                        "(attempt %d/%d): %s",
                        date_start, date_end, modalidade, page,
                        attempt, MAX_RETRIES, e,
                    )
                    time.sleep(RETRY_BACKOFF_SECONDS * attempt)
                    continue
                logger.warning(
                    "Giving up on %s-%s mod=%d page=%d after %d attempts: %s",
                    date_start, date_end, modalidade, page, MAX_RETRIES, e,
                )
                return None
        return None

    first = fetch_with_retry(1)
    if first is None:
        return []

    first_items = first.get("data", [])
    if not first_items or first.get("empty", True):
        return []

    all_records: list[dict] = list(first_items)
    total_pages = int(first.get("totalPaginas", 1) or 1)
    if total_pages <= 1:
        return all_records

    remaining_pages = range(2, total_pages + 1)
    workers = max(1, int(page_workers))
    if workers == 1:
        for page in remaining_pages:
            data = fetch_with_retry(page)
            if data is None:
                continue
            items = data.get("data", [])
            if items and not data.get("empty", False):
                all_records.extend(items)
            if request_delay_seconds > 0:
                time.sleep(request_delay_seconds)
        return all_records

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {executor.submit(fetch_with_retry, page): page for page in remaining_pages}
        for future in as_completed(futures):
            data = future.result()
            if data is None:
                continue
            items = data.get("data", [])
            if items and not data.get("empty", False):
                all_records.extend(items)
    return all_records


def _date_windows(
    start: datetime, end: datetime, window_days: int,
) -> list[tuple[str, str]]:
    """Generate (start_yyyymmdd, end_yyyymmdd) tuples for date windows."""
    windows: list[tuple[str, str]] = []
    current = start
    while current < end:
        window_end = min(current + timedelta(days=window_days - 1), end)
        windows.append((
            current.strftime("%Y%m%d"),
            window_end.strftime("%Y%m%d"),
        ))
        current = window_end + timedelta(days=1)
    return windows


def _month_key_for_record(rec: dict, fallback: str) -> str:
    """Extract YYYYMM month key from a record's publication date."""
    pub_date = str(rec.get("dataPublicacaoPncp", fallback))
    if "-" in pub_date:
        return pub_date[:7].replace("-", "")
    return fallback[:6]


def _flush_to_disk(
    out_dir: Path,
    month_key: str,
    new_records: list[dict],
) -> int:
    """Append-merge new_records into the monthly JSON file.

    Deduplicates by numeroControlePNCP.  Returns total record count
    in the file after merge.
    """
    out_file = out_dir / f"pncp_{month_key}.json"

    existing_data: list[dict] = []
    if out_file.exists():
        try:
            raw = json.loads(out_file.read_text(encoding="utf-8"), strict=False)
            if isinstance(raw, dict) and "data" in raw:
                existing_data = raw["data"]
            elif isinstance(raw, list):
                existing_data = raw
        except (json.JSONDecodeError, OSError):
            logger.warning("Could not read existing file %s, overwriting", out_file)

    # Deduplicate by control number
    seen_ids: set[str] = {
        str(r.get("numeroControlePNCP", "")) for r in existing_data
    }
    unique_new = [
        r for r in new_records
        if str(r.get("numeroControlePNCP", "")) not in seen_ids
    ]

    merged = existing_data + unique_new
    out_file.write_text(
        json.dumps(merged, ensure_ascii=False, indent=None),
        encoding="utf-8",
    )
    return len(merged)


def _load_checkpoint(checkpoint_file: Path) -> set[str]:
    """Load set of completed (window_start, window_end, modalidade) keys."""
    if not checkpoint_file.exists():
        return set()
    try:
        lines = checkpoint_file.read_text(encoding="utf-8").strip().splitlines()
        return set(lines)
    except OSError:
        return set()


def _save_checkpoint(checkpoint_file: Path, key: str) -> None:
    """Append a completed key to the checkpoint file."""
    with checkpoint_file.open("a", encoding="utf-8") as f:
        f.write(key + "\n")


def _month_range(start: datetime, end: datetime) -> list[str]:
    """Return YYYYMM keys from start month to end month inclusive."""
    keys: list[str] = []
    cursor = datetime(start.year, start.month, 1)
    limit = datetime(end.year, end.month, 1)
    while cursor <= limit:
        keys.append(cursor.strftime("%Y%m"))
        if cursor.month == 12:
            cursor = datetime(cursor.year + 1, 1, 1)
        else:
            cursor = datetime(cursor.year, cursor.month + 1, 1)
    return keys


def _load_month_file(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), strict=False)
    except (json.JSONDecodeError, OSError):
        return []
    if isinstance(raw, dict) and "data" in raw and isinstance(raw["data"], list):
        return [r for r in raw["data"] if isinstance(r, dict)]
    if isinstance(raw, list):
        return [r for r in raw if isinstance(r, dict)]
    return []


def _compute_missing_months(out_dir: Path, expected_months: list[str]) -> list[str]:
    missing: list[str] = []
    for mk in expected_months:
        if not (out_dir / f"pncp_{mk}.json").exists():
            missing.append(mk)
    return missing


def _write_manifest(
    manifest_path: Path,
    start_date: str,
    end_date: str,
    expected_months: list[str],
    month_sources: dict[str, set[str]],
    missing_months: list[str],
) -> None:
    month_entries: list[dict[str, object]] = []
    totals = {"in_sync": 0, "empty": 0, "missing": 0}

    for mk in expected_months:
        rows = len(_load_month_file(manifest_path.parent / f"pncp_{mk}.json"))
        if mk in missing_months:
            status = "missing"
        elif rows == 0:
            status = "empty"
        else:
            status = "in_sync"
        totals[status] += 1
        month_entries.append({
            "month": mk,
            "rows": rows,
            "source_windows": sorted(month_sources.get(mk, set())),
            "status": status,
        })

    payload = {
        "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "range_start": start_date,
        "range_end": end_date,
        "expected_months": expected_months,
        "missing_months": missing_months,
        "summary": {
            "months_total": len(expected_months),
            "months_in_sync": totals["in_sync"],
            "months_empty": totals["empty"],
            "months_missing": totals["missing"],
        },
        "months": month_entries,
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote PNCP manifest: %s", manifest_path)


@click.command()
@click.option(
    "--start-date",
    default="2021-01-01",
    help="Start date (YYYY-MM-DD). Default: 2021-01-01 (PNCP launch).",
)
@click.option(
    "--end-date",
    default=lambda: datetime.now().strftime("%Y-%m-%d"),
    help="End date (YYYY-MM-DD). Default: today.",
)
@click.option(
    "--modalidades",
    default=",".join(str(m) for m in ALL_MODALIDADES),
    help="Comma-separated modalidade codes. Default: all.",
)
@click.option("--output-dir", default="./data/pncp", help="Output directory")
@click.option(
    "--window-days", type=int, default=MAX_DATE_RANGE_DAYS,
    help="Days per API window",
)
@click.option(
    "--skip-existing/--no-skip-existing", default=True,
    help="Skip already-checkpointed windows",
)
@click.option("--timeout", type=int, default=90, help="HTTP request timeout in seconds")
@click.option(
    "--strict-month-continuity/--no-strict-month-continuity",
    default=False,
    help="Fail if any month in range has no monthly PNCP file after run.",
)
@click.option(
    "--request-delay",
    type=float,
    default=REQUEST_DELAY_SECONDS,
    show_default=True,
    help="Delay (seconds) between combo requests. Use 0 for max throughput.",
)
@click.option(
    "--page-workers",
    type=int,
    default=1,
    show_default=True,
    help="Parallel workers to fetch remaining pages inside each combo.",
)
@click.option(
    "--manifest-path",
    default=None,
    help="Optional manifest JSON output path (default: <output-dir>/download_manifest.json).",
)
def main(
    start_date: str,
    end_date: str,
    modalidades: str,
    output_dir: str,
    window_days: int,
    skip_existing: bool,
    timeout: int,
    strict_month_continuity: bool,
    request_delay: float,
    page_workers: int,
    manifest_path: str | None,
) -> None:
    """Download PNCP procurement bid publications."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    mod_list = [int(m.strip()) for m in modalidades.split(",")]

    logger.info("=== PNCP Download ===")
    logger.info("Date range: %s to %s", start_date, end_date)
    logger.info("Modalidades: %s", mod_list)
    logger.info("Page workers: %d", max(1, page_workers))
    logger.info("Request delay: %.3fs", max(0.0, request_delay))

    windows = _date_windows(start, end, window_days)
    total_combos = len(windows) * len(mod_list)
    expected_months = _month_range(start, end)
    missing_before = _compute_missing_months(out, expected_months)
    logger.info("Date windows: %d, total combos: %d", len(windows), total_combos)
    logger.info(
        "Month continuity (pre-run): expected=%d missing=%d",
        len(expected_months),
        len(missing_before),
    )
    if missing_before:
        logger.info("Missing months before run: %s", ",".join(missing_before))

    # Checkpoint file tracks completed (window, modalidade) combos
    checkpoint_file = out / ".checkpoint"
    completed = _load_checkpoint(checkpoint_file) if skip_existing else set()
    if completed:
        logger.info("Resuming: %d combos already completed", len(completed))

    client = httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "BR-ACC-ETL/1.0 (public data research)"},
    )

    total_records = 0
    combos_done = len(completed)
    month_sources: dict[str, set[str]] = defaultdict(set)

    try:
        for win_start, win_end in windows:
            for mod in mod_list:
                combo_key = f"{win_start}_{win_end}_{mod}"

                if combo_key in completed:
                    continue

                logger.info(
                    "[%d/%d] Fetching %s-%s modalidade=%d...",
                    combos_done + 1, total_combos, win_start, win_end, mod,
                )
                records = _fetch_window(
                    client,
                    win_start,
                    win_end,
                    mod,
                    page_workers=max(1, page_workers),
                    request_delay_seconds=max(0.0, request_delay),
                )

                if records:
                    # Group by publication month and flush immediately
                    by_month: dict[str, list[dict]] = {}
                    for rec in records:
                        mk = _month_key_for_record(rec, win_start)
                        by_month.setdefault(mk, []).append(rec)
                        month_sources[mk].add(combo_key)

                    for mk, recs in by_month.items():
                        count = _flush_to_disk(out, mk, recs)
                        logger.info(
                            "  %s: +%d records (file total: %d)",
                            mk, len(recs), count,
                        )

                    total_records += len(records)

                # Mark combo as done
                _save_checkpoint(checkpoint_file, combo_key)
                completed.add(combo_key)
                combos_done += 1

                if request_delay > 0:
                    time.sleep(request_delay)
    except KeyboardInterrupt:
        logger.info("Interrupted. Progress saved — rerun with --skip-existing to resume.")
    finally:
        client.close()

    missing_after = _compute_missing_months(out, expected_months)
    logger.info(
        "Month continuity (post-run): expected=%d missing=%d",
        len(expected_months),
        len(missing_after),
    )
    if missing_after:
        logger.warning("Missing months after run: %s", ",".join(missing_after))

    manifest_output = Path(manifest_path) if manifest_path else out / "download_manifest.json"
    _write_manifest(
        manifest_output,
        start_date=start_date,
        end_date=end_date,
        expected_months=expected_months,
        month_sources=month_sources,
        missing_months=missing_after,
    )

    logger.info(
        "=== Done: %d new records fetched, %d/%d combos completed ===",
        total_records, combos_done, total_combos,
    )
    if strict_month_continuity and missing_after:
        raise click.ClickException(
            f"Strict month continuity failed: {len(missing_after)} missing month(s)",
        )


if __name__ == "__main__":
    main()
