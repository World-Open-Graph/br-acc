#!/usr/bin/env python3
"""Download Senate inquiry data (CPI/CPMI) in canonical v2 format.

Outputs consumed by SenadoCpisPipeline:
- data/senado_cpis/inquiries.csv
- data/senado_cpis/requirements.csv
- data/senado_cpis/sessions.csv
- data/senado_cpis/members.csv
- data/senado_cpis/history_sources.csv
"""

from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click
import httpx
from defusedxml import ElementTree as ET
from download_senado_cpi_archive import fetch_archive_historical

logger = logging.getLogger(__name__)

SENADO_OPEN_DATA = "https://legis.senado.leg.br/dadosabertos"
REQ_PAGE_SIZE = 20  # endpoint rejects larger values


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        logger.warning("No rows for %s", path.name)
        path.write_text("", encoding="utf-8")
        return

    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)

    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    logger.info("Wrote %d rows to %s", len(rows), path)


def _text(node: ET.Element | None) -> str:
    return (node.text if node is not None and node.text else "").strip()


def _slugify(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return normalized or "unknown"


def _make_inquiry_id(kind: str, code: str, sigla: str, name: str) -> str:
    anchor = sigla or code or name
    return f"senado-{_slugify(kind)}-{_slugify(anchor)}"


def _parse_date(value: str) -> str:
    raw = value.strip()
    if not raw:
        return ""
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
    if len(raw) >= 10 and raw[2] == "/" and raw[5] == "/":
        try:
            dt = datetime.strptime(raw[:10], "%d/%m/%Y")
            return dt.replace(tzinfo=UTC).strftime("%Y-%m-%d")
        except ValueError:
            return ""
    return ""


def _dedupe(rows: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    seen: set[str] = set()
    output: list[dict[str, Any]] = []
    for row in rows:
        value = str(row.get(key, "")).strip()
        if not value or value in seen:
            continue
        seen.add(value)
        output.append(row)
    return output


def _temporal_status(event_date: str, start_date: str, end_date: str) -> str:
    if not event_date or not start_date:
        return "unknown"
    if event_date < start_date:
        return "invalid"
    if end_date and event_date > end_date:
        return "invalid"
    return "valid"


def _fetch_official_active_inquiries(
    client: httpx.Client,
) -> tuple[list[dict[str, str]], dict[str, str]]:
    rows: list[dict[str, str]] = []
    sigla_to_inquiry_id: dict[str, str] = {}

    for kind in ("CPI", "CPMI"):
        url = f"{SENADO_OPEN_DATA}/comissao/lista/{kind}"
        try:
            resp = client.get(url, timeout=60)
            resp.raise_for_status()
            raw = resp.content
            xml_start = raw.find(b"<")
            if xml_start > 0:
                raw = raw[xml_start:]
            root = ET.fromstring(raw)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Official Senado endpoint failed for tipo=%s: %s", kind, exc)
            continue

        colegiados = root.findall(".//Colegiado") + root.findall(".//colegiado")
        for com in colegiados:
            code = _text(com.find("CodigoColegiado")) or _text(com.find("Codigo"))
            sigla = _text(com.find("SiglaColegiado")) or _text(com.find("Sigla"))
            name = _text(com.find("NomeColegiado")) or _text(com.find("Nome"))
            if not name:
                continue

            inquiry_id = _make_inquiry_id(kind, code, sigla, name)
            if sigla:
                sigla_to_inquiry_id[sigla.upper()] = inquiry_id

            rows.append({
                "inquiry_id": inquiry_id,
                "inquiry_code": code or sigla,
                "name": name,
                "kind": kind,
                "house": "congresso" if kind == "CPMI" else "senado",
                "status": "em atividade",
                "subject": (
                    _text(com.find("TextoFinalidade"))
                    or _text(com.find("DescricaoSubtitulo"))
                ),
                "date_start": _parse_date(_text(com.find("DataInicio"))),
                "date_end": _parse_date(_text(com.find("DataFim"))),
                "source_url": url,
                "source_system": "senado_open_data",
                "extraction_method": "comissao_lista_tipo",
                "source_ref": sigla or code,
                "date_precision": "day",
            })

    return _dedupe(rows, "inquiry_id"), sigla_to_inquiry_id


def _fetch_official_requirements_for_sigla(
    client: httpx.Client,
    sigla: str,
    inquiry_id: str,
    max_pages: int,
    run_id: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    page = 0
    endpoint = f"{SENADO_OPEN_DATA}/comissao/cpi/{sigla}/requerimentos"

    while page < max_pages:
        params = {"pagina": page, "tamanho": REQ_PAGE_SIZE}
        resp = client.get(endpoint, params=params, timeout=90)
        if resp.status_code in (400, 404):
            if page == 0:
                logger.info("No requirement endpoint rows for sigla=%s", sigla)
            break
        resp.raise_for_status()
        if not resp.content.strip():
            break
        try:
            payload = resp.json()
        except ValueError:
            logger.warning(
                "Invalid requirements payload for sigla=%s page=%d",
                sigla,
                page,
            )
            break

        if not isinstance(payload, list) or not payload:
            break

        for req in payload:
            if not isinstance(req, dict):
                continue
            code = str(req.get("codigo", "")).strip()
            number = str(req.get("numero", "")).strip()
            year = str(req.get("ano", "")).strip()
            requirement_id = (
                f"senado-req-{_slugify(sigla)}-{_slugify(number)}-"
                f"{year or 'na'}-{code or 'na'}"
            )
            author_obj = req.get("autor") if isinstance(req.get("autor"), dict) else {}
            author_name = (
                str(author_obj.get("nomeParlamentar", "")).strip()
                or str(author_obj.get("nome", "")).strip()
                or str(req.get("autoria", "")).strip()
            )
            source_ref = ""
            doc_obj = req.get("documento") if isinstance(req.get("documento"), dict) else {}
            if doc_obj:
                source_ref = str(doc_obj.get("linkDownload", "")).strip()
            date_value = _parse_date(
                str(req.get("dataApresentacao", "")).strip()
                or str(req.get("dataApreciacao", "")).strip(),
            )
            rows.append({
                "requirement_id": requirement_id,
                "inquiry_id": inquiry_id,
                "type": str(req.get("tipoRequerimento", "")).strip() or "REQUERIMENTO",
                "date": date_value,
                "text": str(req.get("ementa", "")).strip() or str(req.get("assunto", "")).strip(),
                "status": str(req.get("situacao", "")).strip(),
                "author_name": author_name,
                "author_cpf": "",
                "source_url": source_ref or endpoint,
                "source_system": "senado_open_data",
                "extraction_method": "comissao_cpi_requerimentos",
                "source_ref": code or number or sigla,
                "date_precision": "day" if date_value else "unknown",
                "run_id": run_id,
            })

        if len(payload) < REQ_PAGE_SIZE:
            break
        page += 1

    return rows


def _fetch_official_requirements(
    client: httpx.Client,
    sigla_to_inquiry_id: dict[str, str],
    max_pages: int,
    run_id: str,
) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for sigla, inquiry_id in sorted(sigla_to_inquiry_id.items()):
        rows.extend(
            _fetch_official_requirements_for_sigla(
                client=client,
                sigla=sigla,
                inquiry_id=inquiry_id,
                max_pages=max_pages,
                run_id=run_id,
            ),
        )
    return _dedupe(rows, "requirement_id")


def _merge_with_run_id(rows: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        item = dict(row)
        item.setdefault("run_id", run_id)
        out.append(item)
    return out


def _temporal_summary(
    inquiries: list[dict[str, Any]],
    requirements: list[dict[str, Any]],
    sessions: list[dict[str, Any]],
) -> tuple[int, int]:
    inquiry_dates = {
        str(row.get("inquiry_id", "")): (
            str(row.get("date_start", "")).strip(),
            str(row.get("date_end", "")).strip(),
        )
        for row in inquiries
    }
    invalid = 0
    unknown = 0
    for row in requirements:
        inquiry_id = str(row.get("inquiry_id", "")).strip()
        event = str(row.get("date", "")).strip()
        start, end = inquiry_dates.get(inquiry_id, ("", ""))
        status = _temporal_status(event, start, end)
        if status == "invalid":
            invalid += 1
        elif status == "unknown":
            unknown += 1
    for row in sessions:
        inquiry_id = str(row.get("inquiry_id", "")).strip()
        event = str(row.get("date", "")).strip()
        start, end = inquiry_dates.get(inquiry_id, ("", ""))
        status = _temporal_status(event, start, end)
        if status == "invalid":
            invalid += 1
        elif status == "unknown":
            unknown += 1
    return invalid, unknown


def _write_manifest(
    manifest_path: Path,
    *,
    run_id: str,
    history_source: str,
    strict_history_completeness: bool,
    strict_temporal_order: bool,
    official_active_inquiries: int,
    archive_historical_inquiries: int,
    merged_inquiries: int,
    requirements: int,
    sessions: int,
    members: int,
    blocked_external: str | None,
    missing_fields_count: int,
    temporal_invalid_count: int,
    temporal_unknown_count: int,
    window_start: str,
    window_end: str,
    checksum: str,
) -> None:
    status = "ok"
    if blocked_external:
        status = "blocked_external"
    if temporal_invalid_count > 0:
        status = "invalid_temporal"

    payload = {
        "generated_at_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "run_id": run_id,
        "source_id": "senado_cpis",
        "window_start": window_start,
        "window_end": window_end,
        "rows": merged_inquiries + requirements + sessions,
        "error": blocked_external,
        "checksum": checksum,
        "retrieved_at_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "history_source": history_source,
        "strict_history_completeness": strict_history_completeness,
        "strict_temporal_order": strict_temporal_order,
        "status": status,
        "counts": {
            "official_active_inquiries": official_active_inquiries,
            "archive_historical_inquiries": archive_historical_inquiries,
            "merged_inquiries": merged_inquiries,
            "requirements": requirements,
            "sessions": sessions,
            "members": members,
            "missing_fields_count": missing_fields_count,
            "temporal_invalid_count": temporal_invalid_count,
            "temporal_unknown_count": temporal_unknown_count,
        },
        "blocked_external": blocked_external,
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote Senado CPIs manifest: %s", manifest_path)


@click.command()
@click.option("--output-dir", default="./data/senado_cpis", help="Output directory")
@click.option("--skip-existing/--no-skip-existing", default=True)
@click.option(
    "--history-source",
    type=click.Choice(["official_archive", "official_only"], case_sensitive=False),
    default="official_archive",
    show_default=True,
    help="Historical coverage strategy.",
)
@click.option(
    "--strict-history-completeness/--allow-partial-history",
    default=True,
    help="Fail if historical extraction is empty in archive mode.",
)
@click.option(
    "--strict-temporal-order/--allow-temporal-unknown",
    default=True,
    help="Fail if invalid temporal order is detected.",
)
@click.option(
    "--manifest-path",
    default=None,
    help="Optional manifest JSON output path (default: <output-dir>/download_manifest.json).",
)
@click.option("--max-pages", default=200, type=int, help="Max pages per inquiry requirements API.")
def main(
    output_dir: str,
    skip_existing: bool,
    history_source: str,
    strict_history_completeness: bool,
    strict_temporal_order: bool,
    manifest_path: str | None,
    max_pages: int,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    run_id = f"senado_cpis_{datetime.now(tz=UTC).strftime('%Y%m%d%H%M%S')}"

    inquiries_path = out / "inquiries.csv"
    req_path = out / "requirements.csv"
    sessions_path = out / "sessions.csv"
    members_path = out / "members.csv"
    history_sources_path = out / "history_sources.csv"
    manifest_file = Path(manifest_path) if manifest_path else out / "download_manifest.json"

    outputs = (inquiries_path, req_path, sessions_path, members_path, history_sources_path)
    if skip_existing and all(path.exists() for path in outputs):
        logger.info("Skipping (all outputs exist)")
        return

    official_inquiries: list[dict[str, Any]] = []
    official_requirements: list[dict[str, Any]] = []
    archive_inquiries: list[dict[str, Any]] = []
    archive_requirements: list[dict[str, Any]] = []
    archive_sessions: list[dict[str, Any]] = []
    history_sources_rows: list[dict[str, Any]] = []
    blocked_external: str | None = None
    window_start = ""
    window_end = ""
    checksum = hashlib.sha256(run_id.encode("utf-8")).hexdigest()

    with httpx.Client(follow_redirects=True) as client:
        official_inquiries, sigla_map = _fetch_official_active_inquiries(client)
        official_requirements = _fetch_official_requirements(
            client=client,
            sigla_to_inquiry_id=sigla_map,
            max_pages=max_pages,
            run_id=run_id,
        )
        if history_source == "official_archive":
            try:
                (
                    archive_inquiries,
                    archive_requirements,
                    archive_sessions,
                    history_sources_rows,
                ) = fetch_archive_historical(
                    client=client,
                    run_id=run_id,
                )
            except Exception as exc:  # noqa: BLE001
                blocked_external = str(exc)
                logger.warning("Official archive historical extraction failed: %s", exc)

    if (
        history_source == "official_archive"
        and strict_history_completeness
        and not archive_inquiries
    ):
        _write_manifest(
            manifest_file,
            run_id=run_id,
            history_source=history_source,
            strict_history_completeness=strict_history_completeness,
            strict_temporal_order=strict_temporal_order,
            official_active_inquiries=len(official_inquiries),
            archive_historical_inquiries=0,
            merged_inquiries=len(official_inquiries),
            requirements=len(official_requirements),
            sessions=0,
            members=0,
            blocked_external=blocked_external or "archive_historical_inquiries=0",
            missing_fields_count=0,
            temporal_invalid_count=0,
            temporal_unknown_count=0,
            window_start=window_start,
            window_end=window_end,
            checksum=checksum,
        )
        raise click.ClickException(
            "Historical archive is required in strict mode and returned zero inquiries.",
        )

    merged_inquiries = _merge_with_run_id(
        _dedupe(official_inquiries + archive_inquiries, "inquiry_id"),
        run_id=run_id,
    )
    merged_requirements = _merge_with_run_id(
        _dedupe(official_requirements + archive_requirements, "requirement_id"),
        run_id=run_id,
    )
    merged_sessions = _merge_with_run_id(
        _dedupe(archive_sessions, "session_id"),
        run_id=run_id,
    )
    merged_members: list[dict[str, Any]] = []
    all_dates = sorted(
        value
        for value in (
            [str(row.get("date_start", "")).strip() for row in merged_inquiries]
            + [str(row.get("date", "")).strip() for row in merged_requirements]
            + [str(row.get("date", "")).strip() for row in merged_sessions]
        )
        if value
    )
    window_start = all_dates[0] if all_dates else ""
    window_end = all_dates[-1] if all_dates else ""
    checksum_basis = "|".join(
        sorted(
            [str(row.get("inquiry_id", "")).strip() for row in merged_inquiries]
            + [str(row.get("requirement_id", "")).strip() for row in merged_requirements]
            + [str(row.get("session_id", "")).strip() for row in merged_sessions]
        )
    )
    checksum = hashlib.sha256(checksum_basis.encode("utf-8")).hexdigest()

    if not merged_inquiries:
        raise click.ClickException("No Senate inquiry rows found from official sources.")

    temporal_invalid_count, temporal_unknown_count = _temporal_summary(
        inquiries=merged_inquiries,
        requirements=merged_requirements,
        sessions=merged_sessions,
    )
    if strict_temporal_order and temporal_invalid_count > 0:
        _write_manifest(
            manifest_file,
            run_id=run_id,
            history_source=history_source,
            strict_history_completeness=strict_history_completeness,
            strict_temporal_order=strict_temporal_order,
            official_active_inquiries=len(official_inquiries),
            archive_historical_inquiries=len(archive_inquiries),
            merged_inquiries=len(merged_inquiries),
            requirements=len(merged_requirements),
            sessions=len(merged_sessions),
            members=0,
            blocked_external=blocked_external,
            missing_fields_count=0,
            temporal_invalid_count=temporal_invalid_count,
            temporal_unknown_count=temporal_unknown_count,
            window_start=window_start,
            window_end=window_end,
            checksum=checksum,
        )
        raise click.ClickException(
            f"Strict temporal order failed with {temporal_invalid_count} invalid edges.",
        )

    missing_fields_count = sum(
        1
        for row in merged_inquiries
        if not str(row.get("name", "")).strip() or not str(row.get("inquiry_id", "")).strip()
    )
    _write_csv(inquiries_path, merged_inquiries)
    _write_csv(req_path, merged_requirements)
    _write_csv(sessions_path, merged_sessions)
    _write_csv(members_path, merged_members)
    _write_csv(history_sources_path, history_sources_rows)
    _write_manifest(
        manifest_file,
        run_id=run_id,
        history_source=history_source,
        strict_history_completeness=strict_history_completeness,
        strict_temporal_order=strict_temporal_order,
        official_active_inquiries=len(official_inquiries),
        archive_historical_inquiries=len(archive_inquiries),
        merged_inquiries=len(merged_inquiries),
        requirements=len(merged_requirements),
        sessions=len(merged_sessions),
        members=len(merged_members),
        blocked_external=blocked_external,
        missing_fields_count=missing_fields_count,
        temporal_invalid_count=temporal_invalid_count,
        temporal_unknown_count=temporal_unknown_count,
        window_start=window_start,
        window_end=window_end,
        checksum=checksum,
    )


if __name__ == "__main__":
    main()
