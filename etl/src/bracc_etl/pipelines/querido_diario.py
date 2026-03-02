from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    parse_date,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

_CNPJ_COMBINED_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}|\d{14}")


def _stable_id(*parts: str, length: int = 24) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _extract_cnpjs_with_spans(text: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    seen: set[str] = set()

    for match in _CNPJ_COMBINED_RE.finditer(text):
        raw = match.group(0)
        digits = strip_document(raw)
        if len(digits) != 14 or digits in seen:
            continue
        seen.add(digits)
        cnpj = format_cnpj(digits)
        span = f"{match.start()}:{match.end()}"
        out.append((cnpj, span))

    return out


class QueridoDiarioPipeline(Pipeline):
    """ETL pipeline for municipal gazette acts from Querido Diário."""

    name = "querido_diario"
    source_id = "querido_diario"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_acts: list[dict[str, str]] = []
        self.acts: list[dict[str, Any]] = []
        self.company_mentions: list[dict[str, Any]] = []
        self.run_id = f"{self.name}_{pd.Timestamp.utcnow().strftime('%Y%m%d%H%M%S')}"

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "querido_diario"
        if not src_dir.exists():
            logger.warning("[querido_diario] data dir not found: %s", src_dir)
            return

        records: list[dict[str, str]] = []

        csv_path = src_dir / "acts.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
            for row in df.to_dict("records"):
                records.append({str(k): str(v) for k, v in row.items()})

        jsonl_path = src_dir / "acts.jsonl"
        if jsonl_path.exists():
            for line in jsonl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    payload = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if isinstance(payload, dict):
                    records.append({k: str(v) for k, v in payload.items()})

        json_path = src_dir / "acts.json"
        if json_path.exists():
            try:
                payload = json.loads(json_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = []

            if isinstance(payload, list):
                for row in payload:
                    if isinstance(row, dict):
                        records.append({str(k): str(v) for k, v in row.items()})
            elif isinstance(payload, dict) and isinstance(payload.get("acts"), list):
                for row in payload["acts"]:
                    if isinstance(row, dict):
                        records.append({str(k): str(v) for k, v in row.items()})

        if self.limit:
            records = records[: self.limit]

        self._raw_acts = records
        logger.info("[querido_diario] extracted %d records", len(self._raw_acts))

    def transform(self) -> None:
        if not self._raw_acts:
            return

        acts: list[dict[str, Any]] = []
        mentions: list[dict[str, Any]] = []

        for row in self._raw_acts:
            city = str(row.get("municipality_name") or row.get("municipio") or "").strip()
            city_code = str(row.get("municipality_code") or row.get("cod_ibge") or "").strip()
            uf = str(row.get("uf") or row.get("estado") or "").strip()
            published_at = parse_date(
                str(row.get("date") or row.get("published_at") or row.get("data") or ""),
            )
            title = str(row.get("title") or row.get("titulo") or "").strip()
            text = str(row.get("text") or row.get("conteudo") or "").strip()
            source_url = str(row.get("source_url") or row.get("url") or "").strip()
            edition = str(row.get("edition") or row.get("edicao") or "").strip()
            txt_url = str(row.get("txt_url") or "").strip()
            text_status_raw = str(row.get("text_status") or "").strip().lower()

            if not text and not title:
                continue

            if text_status_raw in {"available", "missing", "forbidden"}:
                text_status = text_status_raw
            elif text:
                text_status = "available"
            elif txt_url.startswith("s3://"):
                text_status = "forbidden"
            else:
                text_status = "missing"

            act_id = str(row.get("act_id", "")).strip()
            if not act_id:
                act_id = _stable_id(city_code, published_at, title[:180], source_url)

            acts.append({
                "municipal_gazette_act_id": act_id,
                "municipality_name": city,
                "municipality_code": city_code,
                "uf": uf,
                "published_at": published_at,
                "title": title,
                "text_hash": _sha256_text(text),
                "text_status": text_status,
                "txt_url": txt_url,
                "edition": edition,
                "source_url": source_url,
                "source": "querido_diario",
            })

            if text_status == "available":
                mention_text = f"{title}\n{text}"
                for cnpj, span in _extract_cnpjs_with_spans(mention_text):
                    mentions.append({
                        "cnpj": cnpj,
                        "target_key": act_id,
                        "method": "text_cnpj_extract",
                        "confidence": 0.75,
                        "source_ref": source_url or act_id,
                        "extract_span": span,
                        "run_id": self.run_id,
                    })

        self.acts = deduplicate_rows(acts, ["municipal_gazette_act_id"])
        self.company_mentions = deduplicate_rows(
            mentions,
            ["cnpj", "target_key", "method", "extract_span"],
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.acts:
            loader.load_nodes(
                "MunicipalGazetteAct",
                self.acts,
                key_field="municipal_gazette_act_id",
            )

        if self.company_mentions:
            companies = deduplicate_rows(
                [
                    {
                        "cnpj": row["cnpj"],
                        "razao_social": row["cnpj"],
                    }
                    for row in self.company_mentions
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", companies, key_field="cnpj")

            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.cnpj}) "
                "MATCH (a:MunicipalGazetteAct {municipal_gazette_act_id: row.target_key}) "
                "MERGE (c)-[m:MENCIONADA_EM]->(a) "
                "SET m.method = row.method, "
                "m.confidence = row.confidence, "
                "m.source_ref = row.source_ref, "
                "m.extract_span = row.extract_span, "
                "m.run_id = row.run_id"
            )
            loader.run_query_with_retry(query, self.company_mentions)
