"""Shared download utilities for ETL data acquisition scripts."""

from __future__ import annotations

import logging
import shutil
import stat
import zipfile
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)


def download_file(url: str, dest: Path, *, timeout: int = 600) -> bool:
    """Download a file with streaming and resume support.

    Returns True on success, False on failure.
    """
    partial = dest.with_suffix(dest.suffix + ".partial")
    start_byte = partial.stat().st_size if partial.exists() else 0

    headers = {}
    if start_byte > 0:
        headers["Range"] = f"bytes={start_byte}-"
        logger.info("Resuming %s from %.1f MB", dest.name, start_byte / 1e6)

    try:
        with httpx.stream(
            "GET", url, follow_redirects=True, timeout=timeout, headers=headers,
        ) as response:
            if response.status_code == 416:
                logger.info("Already complete: %s", dest.name)
                if partial.exists():
                    partial.rename(dest)
                return True

            response.raise_for_status()

            total = response.headers.get("content-length")
            total_mb = f"{int(total) / 1e6:.1f} MB" if total else "unknown size"
            logger.info("Downloading %s (%s)...", dest.name, total_mb)

            mode = "ab" if start_byte > 0 else "wb"
            downloaded = start_byte
            with open(partial, mode) as f:
                for chunk in response.iter_bytes(chunk_size=65_536):
                    f.write(chunk)
                    downloaded += len(chunk)

            partial.rename(dest)
            logger.info("Downloaded: %s (%.1f MB)", dest.name, downloaded / 1e6)
            return True

    except httpx.HTTPError as e:
        logger.warning("Failed to download %s: %s", dest.name, e)
        return False


def extract_zip(zip_path: Path, output_dir: Path) -> list[Path]:
    """Extract ZIP and return list of extracted files.

    Deletes corrupted ZIPs for re-download.
    """
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            extracted = safe_extract_zip(zf, output_dir)
        logger.info("Extracted %d files from %s", len(extracted), zip_path.name)
        return extracted
    except zipfile.BadZipFile:
        logger.warning("Bad ZIP file: %s — deleting for re-download", zip_path.name)
        zip_path.unlink()
        return []
    except ValueError as exc:
        logger.warning("Unsafe ZIP file %s: %s — deleting", zip_path.name, exc)
        zip_path.unlink(missing_ok=True)
        return []


def validate_csv(
    path: Path,
    *,
    expected_cols: int | None = None,
    encoding: str = "latin-1",
    sep: str = ";",
) -> bool:
    """Quick validation: read first 10 rows, check encoding and column count."""
    try:
        import pandas as pd

        df = pd.read_csv(
            path,
            sep=sep,
            encoding=encoding,
            header=None,
            dtype=str,
            nrows=10,
            keep_default_na=False,
        )
        if df.empty:
            logger.warning("Empty file: %s", path.name)
            return False
        if expected_cols and len(df.columns) != expected_cols:
            logger.warning(
                "%s: expected %d cols, got %d", path.name, expected_cols, len(df.columns),
            )
            return False
        logger.info("Validated %s: %d cols, first row OK", path.name, len(df.columns))
        return True
    except Exception as e:
        logger.warning("Validation failed for %s: %s", path.name, e)
        return False


def safe_extract_zip(
    archive: zipfile.ZipFile,
    output_dir: Path,
    *,
    max_members: int = 50_000,
    max_uncompressed_bytes: int = 5_000_000_000,
) -> list[Path]:
    """Safely extract a ZIP archive.

    Blocks path traversal, symlinks, and oversized archives.
    """
    output_root = output_dir.resolve()
    infos = archive.infolist()
    if len(infos) > max_members:
        msg = f"ZIP has too many entries ({len(infos)} > {max_members})"
        raise ValueError(msg)

    extracted: list[Path] = []
    uncompressed_total = 0
    for info in infos:
        member_name = info.filename.replace("\\", "/")
        if not member_name:
            continue

        # Reject symlink entries.
        mode = info.external_attr >> 16
        if stat.S_ISLNK(mode):
            msg = f"ZIP contains symlink entry: {member_name}"
            raise ValueError(msg)

        target = (output_dir / member_name).resolve()
        try:
            target.relative_to(output_root)
        except ValueError as exc:
            msg = f"Path traversal detected: {member_name}"
            raise ValueError(msg) from exc

        if info.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            continue

        uncompressed_total += info.file_size
        if uncompressed_total > max_uncompressed_bytes:
            msg = (
                f"ZIP exceeds max extracted size "
                f"({uncompressed_total} > {max_uncompressed_bytes})"
            )
            raise ValueError(msg)

        target.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info, "r") as source, target.open("wb") as destination:
            shutil.copyfileobj(source, destination)
        extracted.append(target)

    return extracted
