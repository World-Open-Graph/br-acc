from __future__ import annotations

import hashlib
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
    format_cpf,
    normalize_name,
    parse_date,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

_CNPJ_FMT_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
_CNPJ_RAW_RE = re.compile(r"\d{14}")


def _stable_id(*parts: str, length: int = 20) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _extract_cnpjs(text: str) -> list[str]:
    formatted = _CNPJ_FMT_RE.findall(text)
    raw = _CNPJ_RAW_RE.findall(text)

    seen: set[str] = set()
    out: list[str] = []

    for match in formatted:
        digits = strip_document(match)
        if len(digits) == 14 and digits not in seen:
            seen.add(digits)
            out.append(format_cnpj(match))

    for match in raw:
        if len(match) == 14 and match not in seen:
            seen.add(match)
            out.append(format_cnpj(match))

    return out


class CamaraInquiriesPipeline(Pipeline):
    """ETL pipeline for Câmara CPI/CPMI inquiry metadata and requirements."""

    name = "camara_inquiries"
    source_id = "camara_inquiries"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)

        self._raw_inquiries: pd.DataFrame = pd.DataFrame()
        self._raw_requirements: pd.DataFrame = pd.DataFrame()
        self._raw_sessions: pd.DataFrame = pd.DataFrame()

        self.inquiries: list[dict[str, Any]] = []
        self.requirements: list[dict[str, Any]] = []
        self.sessions: list[dict[str, Any]] = []
        self.inquiry_requirement_rels: list[dict[str, Any]] = []
        self.inquiry_session_rels: list[dict[str, Any]] = []
        self.requirement_author_cpf_rels: list[dict[str, Any]] = []
        self.requirement_author_name_rels: list[dict[str, Any]] = []
        self.requirement_company_mentions: list[dict[str, Any]] = []

        self.run_id = f"{self.name}_{pd.Timestamp.utcnow().strftime('%Y%m%d%H%M%S')}"

    def _read_csv_optional(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        try:
            return pd.read_csv(path, dtype=str, keep_default_na=False)
        except pd.errors.EmptyDataError:
            logger.info("[camara_inquiries] empty file (treated as no data): %s", path.name)
            return pd.DataFrame()

    def _get(self, row: pd.Series, *keys: str) -> str:
        for key in keys:
            value = str(row.get(key, "")).strip()
            if value:
                return value
        return ""

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "camara_inquiries"
        self._raw_inquiries = self._read_csv_optional(src_dir / "inquiries.csv")
        self._raw_requirements = self._read_csv_optional(src_dir / "requirements.csv")
        self._raw_sessions = self._read_csv_optional(src_dir / "sessions.csv")

        if self._raw_inquiries.empty:
            logger.warning("[camara_inquiries] inquiries.csv not found/empty in %s", src_dir)
            return

        if self.limit:
            self._raw_inquiries = self._raw_inquiries.head(self.limit)

        logger.info(
            "[camara_inquiries] extracted inquiries=%d requirements=%d sessions=%d",
            len(self._raw_inquiries),
            len(self._raw_requirements),
            len(self._raw_sessions),
        )

    def transform(self) -> None:
        if self._raw_inquiries.empty:
            return

        self._transform_inquiries()
        self._transform_requirements()
        self._transform_sessions()

    def _transform_inquiries(self) -> None:
        rows: list[dict[str, Any]] = []

        for _, row in self._raw_inquiries.iterrows():
            inquiry_id = self._get(row, "inquiry_id", "id")
            code = self._get(row, "inquiry_code", "codigo")
            name = self._get(row, "name", "titulo", "nome")
            if not name:
                continue

            if not inquiry_id:
                inquiry_id = _stable_id(code, name)

            kind = self._get(row, "kind", "tipo").upper()
            if not kind:
                kind = "CPMI" if "CPMI" in name.upper() else "CPI"
            status = self._get(row, "status", "situacao")
            subject = self._get(row, "subject", "objeto")
            source_url = self._get(row, "source_url", "url")
            source_system = self._get(row, "source_system")
            extraction_method = self._get(row, "extraction_method")
            date_start = parse_date(self._get(row, "date_start", "data_inicio"))
            date_end = parse_date(self._get(row, "date_end", "data_fim"))

            rows.append({
                "inquiry_id": inquiry_id,
                "code": code,
                "name": name,
                "kind": kind,
                "house": "camara",
                "status": status,
                "subject": subject,
                "date_start": date_start,
                "date_end": date_end,
                "source_url": source_url,
                "source": "camara_inquiries",
                "source_system": source_system,
                "extraction_method": extraction_method,
            })

        self.inquiries = deduplicate_rows(rows, ["inquiry_id"])

    def _transform_requirements(self) -> None:
        if self._raw_requirements.empty:
            return

        requirements: list[dict[str, Any]] = []
        inquiry_rels: list[dict[str, Any]] = []
        author_cpf_rels: list[dict[str, Any]] = []
        author_name_rels: list[dict[str, Any]] = []
        mentions: list[dict[str, Any]] = []

        for _, row in self._raw_requirements.iterrows():
            inquiry_id = self._get(row, "inquiry_id")
            if not inquiry_id:
                continue

            requirement_id = self._get(row, "requirement_id", "id", "codigo")
            req_type = self._get(row, "type", "tipo")
            text = self._get(row, "text", "texto", "ementa")
            status = self._get(row, "status", "situacao")
            source_url = self._get(row, "source_url", "url")
            source_system = self._get(row, "source_system")
            extraction_method = self._get(row, "extraction_method")
            date = parse_date(self._get(row, "date", "data"))

            if not requirement_id:
                requirement_id = _stable_id(inquiry_id, req_type, text[:200])

            requirements.append({
                "requirement_id": requirement_id,
                "type": req_type,
                "date": date,
                "text": text,
                "status": status,
                "source_url": source_url,
                "source": "camara_inquiries",
                "source_system": source_system,
                "extraction_method": extraction_method,
            })

            inquiry_rels.append({"source_key": inquiry_id, "target_key": requirement_id})

            author_name = normalize_name(self._get(row, "author_name", "autor"))
            author_cpf_raw = self._get(row, "author_cpf", "cpf_autor")
            author_digits = strip_document(author_cpf_raw)
            if len(author_digits) == 11:
                author_cpf_rels.append(
                    {"source_key": format_cpf(author_digits), "target_key": requirement_id},
                )
            elif author_name:
                author_name_rels.append(
                    {"person_name": author_name, "target_key": requirement_id},
                )

            explicit_mentioned = self._get(row, "mentioned_cnpj", "cnpj")
            explicit_digits = strip_document(explicit_mentioned)
            if len(explicit_digits) == 14:
                mentions.append({
                    "cnpj": format_cnpj(explicit_digits),
                    "target_key": requirement_id,
                    "method": "cnpj_explicit",
                    "confidence": 1.0,
                    "source_ref": source_url or requirement_id,
                    "run_id": self.run_id,
                })

            for cnpj in _extract_cnpjs(text):
                mentions.append({
                    "cnpj": cnpj,
                    "target_key": requirement_id,
                    "method": "text_cnpj_extract",
                    "confidence": 0.8,
                    "source_ref": source_url or requirement_id,
                    "run_id": self.run_id,
                })

        self.requirements = deduplicate_rows(requirements, ["requirement_id"])
        self.inquiry_requirement_rels = inquiry_rels
        self.requirement_author_cpf_rels = author_cpf_rels
        self.requirement_author_name_rels = author_name_rels
        self.requirement_company_mentions = deduplicate_rows(
            mentions,
            ["cnpj", "target_key", "method"],
        )

    def _transform_sessions(self) -> None:
        if self._raw_sessions.empty:
            return

        sessions: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []

        for _, row in self._raw_sessions.iterrows():
            inquiry_id = self._get(row, "inquiry_id")
            if not inquiry_id:
                continue

            session_id = self._get(row, "session_id", "id")
            date = parse_date(self._get(row, "date", "data"))
            topic = self._get(row, "topic", "assunto")
            source_url = self._get(row, "source_url", "url")
            source_system = self._get(row, "source_system")
            extraction_method = self._get(row, "extraction_method")

            if not session_id:
                session_id = _stable_id(inquiry_id, date, topic[:200])

            sessions.append({
                "session_id": session_id,
                "date": date,
                "topic": topic,
                "source_url": source_url,
                "source": "camara_inquiries",
                "source_system": source_system,
                "extraction_method": extraction_method,
            })
            rels.append({"source_key": inquiry_id, "target_key": session_id})

        self.sessions = deduplicate_rows(sessions, ["session_id"])
        self.inquiry_session_rels = rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.inquiries:
            loader.load_nodes("Inquiry", self.inquiries, key_field="inquiry_id")

        if self.requirements:
            loader.load_nodes("InquiryRequirement", self.requirements, key_field="requirement_id")

        if self.sessions:
            loader.load_nodes("InquirySession", self.sessions, key_field="session_id")

        if self.inquiry_requirement_rels:
            loader.load_relationships(
                rel_type="TEM_REQUERIMENTO",
                rows=self.inquiry_requirement_rels,
                source_label="Inquiry",
                source_key="inquiry_id",
                target_label="InquiryRequirement",
                target_key="requirement_id",
            )

        if self.inquiry_session_rels:
            loader.load_relationships(
                rel_type="REALIZOU_SESSAO",
                rows=self.inquiry_session_rels,
                source_label="Inquiry",
                source_key="inquiry_id",
                target_label="InquirySession",
                target_key="session_id",
            )

        if self.requirement_author_cpf_rels:
            loader.load_relationships(
                rel_type="PROPOS_REQUERIMENTO",
                rows=self.requirement_author_cpf_rels,
                source_label="Person",
                source_key="cpf",
                target_label="InquiryRequirement",
                target_key="requirement_id",
            )

        if self.requirement_author_name_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person) WHERE p.name = row.person_name "
                "MATCH (r:InquiryRequirement {requirement_id: row.target_key}) "
                "MERGE (p)-[:PROPOS_REQUERIMENTO]->(r)"
            )
            loader.run_query_with_retry(query, self.requirement_author_name_rels)

        if self.requirement_company_mentions:
            companies = deduplicate_rows(
                [
                    {"cnpj": row["cnpj"], "razao_social": row["cnpj"]}
                    for row in self.requirement_company_mentions
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", companies, key_field="cnpj")

            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.cnpj}) "
                "MATCH (r:InquiryRequirement {requirement_id: row.target_key}) "
                "MERGE (c)-[m:MENCIONADA_EM]->(r) "
                "SET m.method = row.method, "
                "m.confidence = row.confidence, "
                "m.source_ref = row.source_ref, "
                "m.run_id = row.run_id"
            )
            loader.run_query_with_retry(query, self.requirement_company_mentions)
