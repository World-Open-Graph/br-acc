#!/usr/bin/env python3
"""Download Câmara CPI/CPMI metadata, requirements and sessions.

Outputs canonical CSV files consumed by CamaraInquiriesPipeline:
- data/camara_inquiries/inquiries.csv
- data/camara_inquiries/requirements.csv
- data/camara_inquiries/sessions.csv

Default strategy is BigQuery-first (historical coverage).
API-only fallback is preserved as non-default mode.
"""

from __future__ import annotations

import csv
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import click
import httpx

logger = logging.getLogger(__name__)

CAMARA_BASE_URL = "https://dadosabertos.camara.leg.br/api/v2"
CAMARA_BQ_DATASET = "basedosdados.br_camara_dados_abertos"
INQUIRY_TYPES = (
    "Comissão Parlamentar de Inquérito",
    "Comissão Parlamentar Mista de Inquérito",
)


def _request_json(
    client: httpx.Client,
    url: str,
    params: dict[str, Any] | None = None,
    tolerated_statuses: set[int] | None = None,
) -> dict[str, Any]:
    response = client.get(url, params=params, timeout=60)
    if tolerated_statuses and response.status_code in tolerated_statuses:
        logger.warning("Endpoint returned %d for %s", response.status_code, response.url)
        return {}
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
    dados = payload.get("dados")
    if isinstance(dados, list):
        return [x for x in dados if isinstance(x, dict)]
    return []


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

    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    logger.info("Wrote %d rows to %s", len(rows), path)


def _kind_from_tipo(tipo_orgao: str) -> str:
    return "CPMI" if "MISTA" in tipo_orgao.upper() else "CPI"


def _parse_date(value: Any) -> str:
    if value is None:
        return ""
    raw = str(value).strip()
    if len(raw) >= 10 and raw[4] == "-" and raw[7] == "-":
        return raw[:10]
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


def _fetch_from_bigquery(
    billing_project: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    try:
        import google.auth
        from google.cloud import bigquery
    except ImportError as exc:
        raise RuntimeError("Install optional deps: pip install '.[bigquery]'") from exc

    credentials, _ = google.auth.default()
    client = bigquery.Client(project=billing_project, credentials=credentials)

    inquiries_query = f"""
    SELECT
      id_orgao,
      nome,
      apelido,
      sigla,
      tipo_orgao,
      data_inicio,
      data_final,
      situacao
    FROM `{CAMARA_BQ_DATASET}.orgao`
    WHERE tipo_orgao IN UNNEST(@types)
    """

    inquiry_job = client.query(
        inquiries_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("types", "STRING", list(INQUIRY_TYPES)),
            ],
        ),
    )
    inquiry_rows = list(inquiry_job.result())

    inquiries: list[dict[str, Any]] = []
    for row in inquiry_rows:
        orgao_id = str(row["id_orgao"]).strip()
        if not orgao_id:
            continue
        tipo = str(row["tipo_orgao"] or "").strip()
        kind = _kind_from_tipo(tipo)
        inquiries.append({
            "inquiry_id": f"camara-{orgao_id}",
            "inquiry_code": str(row["sigla"] or "").strip(),
            "name": str(row["nome"] or row["apelido"] or "").strip(),
            "kind": kind,
            "house": "congresso" if kind == "CPMI" else "camara",
            "status": str(row["situacao"] or "").strip(),
            "subject": tipo,
            "date_start": _parse_date(row["data_inicio"]),
            "date_end": _parse_date(row["data_final"]),
            "source_url": f"{CAMARA_BASE_URL}/orgaos/{orgao_id}",
            "source_system": "camara_bq",
            "extraction_method": "orgao_tipo_inquerito",
        })

    sessions_query = f"""
    WITH inq AS (
      SELECT id_orgao
      FROM `{CAMARA_BQ_DATASET}.orgao`
      WHERE tipo_orgao IN UNNEST(@types)
    )
    SELECT DISTINCT
      eo.id_orgao,
      e.id_evento,
      e.data_inicio,
      e.descricao,
      e.tipo
    FROM `{CAMARA_BQ_DATASET}.evento_orgao` eo
    JOIN inq i ON i.id_orgao = eo.id_orgao
    JOIN `{CAMARA_BQ_DATASET}.evento` e ON e.id_evento = eo.id_evento
    """
    sessions_job = client.query(
        sessions_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("types", "STRING", list(INQUIRY_TYPES)),
            ],
        ),
    )
    sessions_rows = list(sessions_job.result())

    sessions: list[dict[str, Any]] = []
    for row in sessions_rows:
        orgao_id = str(row["id_orgao"]).strip()
        event_id = str(row["id_evento"]).strip()
        if not orgao_id or not event_id:
            continue
        sessions.append({
            "session_id": f"camara-event-{event_id}",
            "inquiry_id": f"camara-{orgao_id}",
            "date": _parse_date(row["data_inicio"]),
            "topic": str(row["descricao"] or row["tipo"] or "").strip(),
            "source_url": f"{CAMARA_BASE_URL}/eventos/{event_id}",
            "source_system": "camara_bq",
            "extraction_method": "evento_orgao_join",
        })

    requirements_query = f"""
    WITH inq AS (
      SELECT id_orgao
      FROM `{CAMARA_BQ_DATASET}.orgao`
      WHERE tipo_orgao IN UNNEST(@types)
    ),
    ev AS (
      SELECT DISTINCT eo.id_orgao, eo.id_evento
      FROM `{CAMARA_BQ_DATASET}.evento_orgao` eo
      JOIN inq i ON i.id_orgao = eo.id_orgao
    ),
    pa AS (
      SELECT
        id_proposicao,
        ARRAY_AGG(
          STRUCT(
            nome_autor,
            SAFE_CAST(proponente AS INT64) AS proponente_rank,
            SAFE_CAST(ordem_assinatura AS INT64) AS assinatura_rank
          )
          ORDER BY SAFE_CAST(proponente AS INT64) DESC, SAFE_CAST(ordem_assinatura AS INT64) ASC
          LIMIT 1
        )[OFFSET(0)] AS picked
      FROM `{CAMARA_BQ_DATASET}.proposicao_autor`
      GROUP BY id_proposicao
    )
    SELECT
      ev.id_orgao,
      er.id_evento,
      er.id_proposicao,
      er.titulo_requerimento,
      pm.sigla AS prop_sigla,
      pm.data AS prop_data,
      pm.ementa,
      pm.situacao_ultimo_status,
      pa.picked.nome_autor AS author_name
    FROM `{CAMARA_BQ_DATASET}.evento_requerimento` er
    JOIN ev ON ev.id_evento = er.id_evento
    LEFT JOIN `{CAMARA_BQ_DATASET}.proposicao_microdados` pm ON pm.id_proposicao = er.id_proposicao
    LEFT JOIN pa ON pa.id_proposicao = er.id_proposicao
    """
    req_job = client.query(
        requirements_query,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("types", "STRING", list(INQUIRY_TYPES)),
            ],
        ),
    )
    req_rows = list(req_job.result())

    requirements: list[dict[str, Any]] = []
    for row in req_rows:
        orgao_id = str(row["id_orgao"]).strip()
        event_id = str(row["id_evento"]).strip()
        prop_id = str(row["id_proposicao"] or "").strip()
        if not orgao_id or not event_id:
            continue
        if prop_id:
            requirement_id = f"camara-req-{prop_id}-ev-{event_id}"
        else:
            requirement_id = f"camara-req-event-{event_id}"
        if prop_id:
            source_url = f"{CAMARA_BASE_URL}/proposicoes/{prop_id}"
        else:
            source_url = f"{CAMARA_BASE_URL}/eventos/{event_id}"
        requirements.append({
            "requirement_id": requirement_id,
            "inquiry_id": f"camara-{orgao_id}",
            "type": str(row["prop_sigla"] or "REQ").strip(),
            "date": _parse_date(row["prop_data"]),
            "text": str(row["ementa"] or row["titulo_requerimento"] or "").strip(),
            "status": str(row["situacao_ultimo_status"] or "").strip(),
            "author_name": str(row["author_name"] or "").strip(),
            "author_cpf": "",
            "source_url": source_url,
            "source_system": "camara_bq",
            "extraction_method": "evento_requerimento_join",
        })

    return (
        _dedupe(inquiries, "inquiry_id"),
        _dedupe(requirements, "requirement_id"),
        _dedupe(sessions, "session_id"),
    )


def _fetch_from_api_only(
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    inquiries: list[dict[str, Any]] = []
    sessions: list[dict[str, Any]] = []
    requirements: list[dict[str, Any]] = []

    with httpx.Client(headers={"Accept": "application/json"}, follow_redirects=True) as client:
        payload_cpi = _request_json(
            client,
            f"{CAMARA_BASE_URL}/orgaos",
            {"sigla": "CPI", "itens": 100},
        )
        payload_cpmi = _request_json(
            client,
            f"{CAMARA_BASE_URL}/orgaos",
            {"sigla": "CPMI", "itens": 100},
        )
        orgaos = _extract_items(payload_cpi) + _extract_items(payload_cpmi)
        logger.info("API-only mode found %d candidate orgaos", len(orgaos))

        seen_orgaos: set[str] = set()
        for orgao in orgaos:
            orgao_id = str(orgao.get("id", "")).strip()
            if not orgao_id or orgao_id in seen_orgaos:
                continue
            seen_orgaos.add(orgao_id)

            sigla = str(orgao.get("sigla", "")).strip()
            nome = str(orgao.get("nomePublicacao") or orgao.get("nome", "")).strip()
            if "CPI" not in sigla.upper() and "CPI" not in nome.upper():
                continue

            inquiry_id = f"camara-{orgao_id}"
            inquiry_url = f"{CAMARA_BASE_URL}/orgaos/{orgao_id}"
            kind = "CPMI" if "CPMI" in (sigla or nome).upper() else "CPI"

            details = _request_json(client, inquiry_url)
            dado = details.get("dados") if isinstance(details.get("dados"), dict) else {}
            inquiries.append({
                "inquiry_id": inquiry_id,
                "inquiry_code": sigla,
                "name": nome,
                "kind": kind,
                "house": "congresso" if kind == "CPMI" else "camara",
                "status": str(dado.get("situacao") or "").strip(),
                "subject": str(dado.get("descricao") or "").strip(),
                "date_start": str(dado.get("dataInicio") or "").strip()[:10],
                "date_end": str(dado.get("dataFim") or "").strip()[:10],
                "source_url": inquiry_url,
                "source_system": "camara_api",
                "extraction_method": "orgaos_sigla",
            })

            eventos_payload = _request_json(
                client,
                f"{CAMARA_BASE_URL}/orgaos/{orgao_id}/eventos",
                {"itens": 200},
            )
            for event in _extract_items(eventos_payload):
                event_id = str(event.get("id", "")).strip()
                if not event_id:
                    continue
                sessions.append({
                    "session_id": f"camara-event-{event_id}",
                    "inquiry_id": inquiry_id,
                    "date": str(event.get("dataHoraInicio") or "").strip()[:10],
                    "topic": str(event.get("descricaoTipo") or event.get("titulo") or "").strip(),
                    "source_url": str(event.get("uri") or inquiry_url),
                    "source_system": "camara_api",
                    "extraction_method": "orgaos_eventos",
                })

    logger.warning(
        "API-only mode does not build full historical requirements; "
        "use mode=bq_first for complete extraction.",
    )
    return (
        _dedupe(inquiries, "inquiry_id"),
        requirements,
        _dedupe(sessions, "session_id"),
    )


def _write_manifest(
    manifest_path: Path,
    mode: str,
    inquiries: int,
    requirements: int,
    sessions: int,
    status: str,
    error: str | None = None,
) -> None:
    payload = {
        "generated_at_utc": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "mode": mode,
        "status": status,
        "counts": {
            "inquiries": inquiries,
            "requirements": requirements,
            "sessions": sessions,
        },
        "error": error,
    }
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote Camara inquiries manifest: %s", manifest_path)


@click.command()
@click.option("--output-dir", default="./data/camara_inquiries", help="Output directory")
@click.option("--skip-existing/--no-skip-existing", default=True)
@click.option(
    "--mode",
    type=click.Choice(["bq_first", "api_only"], case_sensitive=False),
    default="bq_first",
    show_default=True,
    help="Extraction mode.",
)
@click.option(
    "--billing-project",
    default="icarus-corruptos",
    help="GCP billing project for BQ mode.",
)
@click.option(
    "--manifest-path",
    default=None,
    help="Optional manifest JSON output path (default: <output-dir>/download_manifest.json).",
)
def main(
    output_dir: str,
    skip_existing: bool,
    mode: str,
    billing_project: str,
    manifest_path: str | None,
) -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    inquiries_csv = out / "inquiries.csv"
    req_csv = out / "requirements.csv"
    sessions_csv = out / "sessions.csv"
    manifest_file = Path(manifest_path) if manifest_path else out / "download_manifest.json"

    if skip_existing and inquiries_csv.exists() and req_csv.exists() and sessions_csv.exists():
        logger.info("Skipping download (all outputs exist).")
        return

    try:
        if mode.lower() == "bq_first":
            inquiries, requirements, sessions = _fetch_from_bigquery(billing_project)
        else:
            inquiries, requirements, sessions = _fetch_from_api_only()
    except Exception as exc:  # noqa: BLE001
        _write_manifest(
            manifest_file,
            mode=mode,
            inquiries=0,
            requirements=0,
            sessions=0,
            status="failed",
            error=str(exc),
        )
        raise

    _write_csv(inquiries_csv, inquiries)
    _write_csv(req_csv, requirements)
    _write_csv(sessions_csv, sessions)

    status = "ok"
    if mode.lower() == "api_only":
        status = "partial"
    _write_manifest(
        manifest_file,
        mode=mode,
        inquiries=len(inquiries),
        requirements=len(requirements),
        sessions=len(sessions),
        status=status,
    )


if __name__ == "__main__":
    main()
