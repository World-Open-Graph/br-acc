#!/usr/bin/env python3
"""Audit source URLs from the public registry with deterministic classification."""

from __future__ import annotations

import argparse
import csv
import json
import threading
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

USER_AGENT = "Mozilla/5.0 (compatible; BRACC-source-audit/1.0)"


@dataclass(frozen=True)
class UrlResult:
    source_id: str
    url: str
    final_url: str
    http_status: int | None
    error: str | None
    classification: str


def parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "y"}


def parse_simple_yaml_lists(path: Path) -> dict[str, set[str]]:
    parsed: dict[str, set[str]] = {
        "allow_broken_404_410": set(),
        "allow_auth_or_rate_limited": set(),
        "allow_transient_error": set(),
    }
    if not path.exists():
        return parsed

    active_key: str | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        stripped_comment = raw.split("#", 1)[0].rstrip()
        if not stripped_comment.strip():
            continue

        if not stripped_comment.startswith(" ") and stripped_comment.endswith(":"):
            candidate = stripped_comment[:-1].strip()
            active_key = candidate if candidate in parsed else None
            continue

        item = stripped_comment.strip()
        if active_key and item.startswith("- "):
            value = item[2:].strip().strip("\"'")
            if value:
                parsed[active_key].add(value)
    return parsed


def classify(status: int | None, error: str | None) -> str:
    if status is None:
        return "transient_error"
    if 200 <= status < 300:
        return "ok"
    if 300 <= status < 400:
        return "redirected"
    if status in {401, 403, 429}:
        return "auth_or_rate_limited"
    if status in {404, 410}:
        return "broken_404_410"
    if error:
        return "transient_error"
    return "transient_error"


def probe_url(url: str, timeout_sec: float) -> tuple[int | None, str | None, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="HEAD")
    status: int | None = None
    error: str | None = None
    final_url = url

    try:
        with urlopen(request, timeout=timeout_sec) as response:
            status = getattr(response, "status", None) or response.getcode()
            final_url = getattr(response, "url", final_url)
            return status, error, final_url
    except HTTPError as exc:
        status = exc.code
        if status == 405:
            # Fallback when HEAD is not supported.
            fallback = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
            try:
                with urlopen(fallback, timeout=timeout_sec) as response:
                    status = getattr(response, "status", None) or response.getcode()
                    final_url = getattr(response, "url", final_url)
                    return status, error, final_url
            except HTTPError as fallback_exc:
                status = fallback_exc.code
                return status, error, final_url
            except URLError as fallback_exc:
                error = type(fallback_exc).__name__
                return None, error, final_url
            except TimeoutError:
                return None, "TimeoutError", final_url
        return status, error, final_url
    except URLError as exc:
        error = type(exc).__name__
        return None, error, final_url
    except TimeoutError:
        return None, "TimeoutError", final_url


def load_registry_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(f"Registry file not found: {path}")

    rows = list(csv.DictReader(path.open(encoding="utf-8", newline="")))
    return [
        row
        for row in rows
        if parse_bool(row.get("in_universe_v1", "")) and (row.get("primary_url") or "").strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit source URLs in source_registry_br_v1.csv")
    parser.add_argument("--registry-path", default="docs/source_registry_br_v1.csv")
    parser.add_argument("--exceptions-path", default="config/source_url_exceptions.yml")
    parser.add_argument("--output", default="")
    parser.add_argument("--timeout-sec", type=float, default=8.0)
    parser.add_argument("--max-workers", type=int, default=16)
    parser.add_argument("--fail-on-transient", action="store_true")
    args = parser.parse_args()

    registry_path = Path(args.registry_path)
    exceptions_path = Path(args.exceptions_path)
    rows = load_registry_rows(registry_path)
    exceptions = parse_simple_yaml_lists(exceptions_path)

    lock = threading.Lock()
    results: list[UrlResult] = []

    def task(row: dict[str, str]) -> None:
        source_id = (row.get("source_id") or "").strip()
        url = (row.get("primary_url") or "").strip()
        status, error, final_url = probe_url(url, timeout_sec=args.timeout_sec)
        classification = classify(status, error)
        rec = UrlResult(
            source_id=source_id,
            url=url,
            final_url=final_url,
            http_status=status,
            error=error,
            classification=classification,
        )
        with lock:
            results.append(rec)

    with ThreadPoolExecutor(max_workers=max(args.max_workers, 1)) as executor:
        futures = [executor.submit(task, row) for row in rows]
        for future in as_completed(futures):
            future.result()

    results.sort(key=lambda item: item.source_id)
    summary = Counter(item.classification for item in results)

    allow_broken = exceptions["allow_broken_404_410"]
    allow_auth = exceptions["allow_auth_or_rate_limited"]
    allow_transient = exceptions["allow_transient_error"]

    broken_failures = [
        item
        for item in results
        if item.classification == "broken_404_410" and item.source_id not in allow_broken
    ]
    auth_failures = [
        item
        for item in results
        if item.classification == "auth_or_rate_limited" and item.source_id not in allow_auth
    ]
    transient_failures = [
        item
        for item in results
        if item.classification == "transient_error" and item.source_id not in allow_transient
    ]

    payload = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "registry_path": str(registry_path),
        "exceptions_path": str(exceptions_path),
        "checked_sources": len(results),
        "summary": dict(summary),
        "failures": {
            "broken_404_410_unallowlisted": [item.__dict__ for item in broken_failures],
            "auth_or_rate_limited_unallowlisted": [item.__dict__ for item in auth_failures],
            "transient_unallowlisted": [item.__dict__ for item in transient_failures],
        },
        "results": [item.__dict__ for item in results],
    }

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")

    print(
        "checked={checked} ok={ok} redirected={redirected} auth_or_rate_limited={auth} "
        "broken_404_410={broken} transient_error={transient}".format(
            checked=len(results),
            ok=summary.get("ok", 0),
            redirected=summary.get("redirected", 0),
            auth=summary.get("auth_or_rate_limited", 0),
            broken=summary.get("broken_404_410", 0),
            transient=summary.get("transient_error", 0),
        )
    )

    if broken_failures:
        print("FAIL: unallowlisted broken_404_410 URLs found")
        for item in broken_failures:
            print(f"- {item.source_id}: {item.http_status} {item.url}")
        return 1

    if args.fail_on_transient and transient_failures:
        print("FAIL: unallowlisted transient URL failures found")
        for item in transient_failures:
            print(f"- {item.source_id}: {item.error or item.http_status} {item.url}")
        return 1

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
