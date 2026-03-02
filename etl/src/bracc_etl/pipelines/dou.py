"""ETL pipeline for DOU (Diario Oficial da Uniao) gazette acts.

Ingests structured act data from the official Imprensa Nacional portal
(in.gov.br). Creates DOUAct nodes linked to Person (by CPF) via PUBLICOU
and to Company (by CNPJ) via MENCIONOU.

Data source: Imprensa Nacional XML dumps (preferred) or pre-downloaded
JSON files in data/dou/. See scripts/download_dou.py for acquisition.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from defusedxml.ElementTree import ParseError as _XmlParseError  # type: ignore[import-untyped]
from defusedxml.ElementTree import parse as _safe_xml_parse  # type: ignore[import-untyped,unused-ignore]

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    format_cpf,
    parse_date,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

# DOU sections
_SECTION_MAP: dict[str, str] = {
    "DO1": "secao_1",
    "DO2": "secao_2",
    "DO3": "secao_3",
    "DOE": "secao_extra",
}

# Act-type keywords for classification
_NOMINATION_KEYWORDS = (
    "nomear", "nomeacao", "nomeação", "designar", "designacao", "designação",
)
_EXONERATION_KEYWORDS = (
    "exonerar", "exoneracao", "exoneração", "dispensar",
)
_CONTRACT_KEYWORDS = (
    "contrato", "extrato de contrato", "contratada", "contratante",
)
_PENALTY_KEYWORDS = (
    "penalidade", "suspensao", "suspensão", "impedimento",
    "inidoneidade", "advertencia", "advertência",
)

# Regex for document extraction
_CPF_RE = re.compile(r"\d{3}\.\d{3}\.\d{3}-\d{2}")
_CNPJ_RE = re.compile(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}")
# Also match raw 14-digit CNPJs
_CNPJ_RAW_RE = re.compile(r"\d{14}")


def _classify_act(title: str, abstract: str) -> str:
    """Classify a DOU act by type based on title and abstract text."""
    combined = f"{title} {abstract}".lower()

    if any(kw in combined for kw in _NOMINATION_KEYWORDS):
        return "nomeacao"
    if any(kw in combined for kw in _EXONERATION_KEYWORDS):
        return "exoneracao"
    if any(kw in combined for kw in _CONTRACT_KEYWORDS):
        return "contrato"
    if any(kw in combined for kw in _PENALTY_KEYWORDS):
        return "penalidade"
    return "outro"


def _make_act_id(url_title: str, date: str) -> str:
    """Generate a stable act ID from URL title and date."""
    raw = f"dou_{url_title}_{date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _extract_cpfs(text: str) -> list[str]:
    """Extract formatted CPFs from text."""
    matches = _CPF_RE.findall(text)
    cpfs: list[str] = []
    for m in matches:
        digits = strip_document(m)
        if len(digits) == 11:
            cpfs.append(format_cpf(m))
    return cpfs


def _extract_cnpjs(text: str) -> list[str]:
    """Extract and format CNPJ numbers from text.

    Matches both formatted (XX.XXX.XXX/XXXX-XX) and raw 14-digit CNPJs.
    """
    formatted = _CNPJ_RE.findall(text)
    raw = _CNPJ_RAW_RE.findall(text)

    seen: set[str] = set()
    cnpjs: list[str] = []

    for m in formatted:
        digits = strip_document(m)
        if len(digits) == 14 and digits not in seen:
            seen.add(digits)
            cnpjs.append(format_cnpj(m))

    for m in raw:
        # Skip if this raw match is part of an already-matched formatted CNPJ
        if len(m) == 14 and m not in seen:
            # Verify it's not a substring of CPF or other number
            seen.add(m)
            cnpjs.append(format_cnpj(m))

    return cnpjs


class DouPipeline(Pipeline):
    """ETL pipeline for DOU (Diario Oficial da Uniao) acts.

    Reads JSON files from data/dou/ containing act records from the
    Imprensa Nacional portal (in.gov.br). Each act becomes a DOUAct node,
    with relationships to Person (PUBLICOU) and Company (MENCIONOU) based
    on CPF/CNPJ extraction from act text.
    """

    name = "dou"
    source_id = "imprensa_nacional"

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
        self.person_rels: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        dou_dir = Path(self.data_dir) / "dou"
        if not dou_dir.exists():
            msg = f"DOU data directory not found at {dou_dir}"
            raise FileNotFoundError(msg)

        # Try parquet (BigQuery), then XML (Imprensa Nacional), then JSON (legacy)
        parquet_files = sorted(dou_dir.rglob("*.parquet"))
        xml_files = sorted(dou_dir.rglob("*.xml"))
        json_files = sorted(dou_dir.glob("*.json"))

        if parquet_files:
            self._extract_parquet(parquet_files)
        elif xml_files:
            self._extract_xml(xml_files)
        elif json_files:
            self._extract_json(json_files)
        else:
            logger.warning("[dou] No parquet, XML, or JSON files found in %s", dou_dir)
            return

        logger.info("[dou] Extracted %d act records", len(self._raw_acts))

    def _extract_parquet(self, parquet_files: list[Path]) -> None:
        """Extract acts from BigQuery parquet exports (basedosdados DOU)."""
        import pyarrow as pa  # type: ignore[import-not-found]
        import pyarrow.compute as pc  # type: ignore[import-not-found]
        import pyarrow.parquet as pq  # type: ignore[import-not-found]

        parquet_cols = [
            "titulo", "orgao", "ementa", "excerto",
            "secao", "data_publicacao", "url", "tipo_edicao",
        ]

        for f in parquet_files:
            try:
                table = pq.read_table(f, columns=parquet_cols)
                # Cast all to string — avoids date32/dbdate pandas incompatibility
                str_cols = [pc.cast(table.column(c), pa.string()) for c in table.column_names]
                df = pa.table(dict(zip(table.column_names, str_cols, strict=True))).to_pandas()
            except Exception:
                logger.warning("[dou] Failed to read parquet: %s", f.name)
                continue

            logger.info("[dou] Reading %d rows from %s", len(df), f.name)

            for _, row in df.iterrows():
                titulo = str(row.get("titulo", "") or "").strip()
                orgao = str(row.get("orgao", "") or "").strip()
                ementa = str(row.get("ementa", "") or "").strip()
                excerto = str(row.get("excerto", "") or "").strip()
                secao = str(row.get("secao", "") or "").strip()
                pub_date = str(row.get("data_publicacao", "") or "").strip()
                url = str(row.get("url", "") or "").strip()
                tipo_edicao = str(row.get("tipo_edicao", "") or "").strip()

                # Use URL as identifier (stable across editions)
                url_title = url.rsplit("/", 1)[-1] if url else titulo[:60]

                # Combine ementa + excerto for abstract text
                abstract = f"{ementa} {excerto}".strip()

                self._raw_acts.append({
                    "urlTitle": url_title,
                    "title": titulo,
                    "abstract": abstract[:2000],
                    "pubDate": pub_date,
                    "pubName": f"DO{secao}" if secao else "",
                    "artCategory": tipo_edicao,
                    "hierarchyStr": orgao,
                })

                if self.limit and len(self._raw_acts) >= self.limit:
                    return

    def _extract_xml(self, xml_files: list[Path]) -> None:
        """Extract acts from Imprensa Nacional XML dumps."""
        for f in xml_files:
            try:
                tree = _safe_xml_parse(f)
            except _XmlParseError:
                logger.warning("[dou] Failed to parse XML: %s", f.name)
                continue

            root = tree.getroot()

            # Handle both <article> elements and <xml><article> wrappers
            articles = root.findall(".//article")
            if not articles:
                articles = [root] if root.tag == "article" else []

            for article in articles:
                identifica = article.find(".//identifica")
                texto = article.find(".//Texto")
                if texto is None:
                    texto = article.find(".//texto")
                date_el = identifica.find("data") if identifica is not None else None
                orgao_el = identifica.find("orgao") if identifica is not None else None
                titulo_el = identifica.find("titulo") if identifica is not None else None
                secao_el = identifica.find("secao") if identifica is not None else None

                title = (titulo_el.text or "").strip() if titulo_el is not None else ""
                pub_date = (date_el.text or "").strip() if date_el is not None else ""
                agency = (orgao_el.text or "").strip() if orgao_el is not None else ""
                section = (secao_el.text or "").strip() if secao_el is not None else ""

                # Collect all text from Texto element
                abstract = ""
                if texto is not None:
                    abstract = " ".join(
                        (p.text or "").strip()
                        for p in texto.iter()
                        if p.text and p.text.strip()
                    )

                # Use article id or generate from title+date
                art_id = article.get("id", "") or article.get("artType", "")

                self._raw_acts.append({
                    "urlTitle": art_id,
                    "title": title,
                    "abstract": abstract[:2000],
                    "pubDate": pub_date,
                    "pubName": f"DO{section}" if section else "",
                    "artCategory": article.get("artCategory", ""),
                    "hierarchyStr": agency,
                })

                if self.limit and len(self._raw_acts) >= self.limit:
                    return

    def _extract_json(self, json_files: list[Path]) -> None:
        """Extract acts from legacy JSON format (IN search API)."""
        for f in json_files:
            with open(f, encoding="utf-8") as fh:
                data = json.load(fh)

            if isinstance(data, dict) and "jsonArray" in data:
                items = data["jsonArray"]
            elif isinstance(data, list):
                items = data
            else:
                logger.warning("[dou] Unexpected JSON format in %s", f.name)
                continue

            for item in items:
                self._raw_acts.append({
                    "urlTitle": str(item.get("urlTitle", "")),
                    "title": str(item.get("title", "")),
                    "abstract": str(item.get("abstract", "")),
                    "pubDate": str(item.get("pubDate", "")),
                    "pubName": str(item.get("pubName", "")),
                    "artCategory": str(item.get("artCategory", "")),
                    "hierarchyStr": str(item.get("hierarchyStr", "")),
                })

                if self.limit and len(self._raw_acts) >= self.limit:
                    return

    def transform(self) -> None:
        acts: list[dict[str, Any]] = []
        person_rels: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []
        skipped = 0

        for raw in self._raw_acts:
            url_title = raw["urlTitle"].strip()
            title = raw["title"].strip()
            abstract = raw["abstract"].strip()
            pub_date = raw["pubDate"].strip()

            if not url_title or not pub_date:
                skipped += 1
                continue

            date = parse_date(pub_date)
            act_id = _make_act_id(url_title, date)
            act_type = _classify_act(title, abstract)
            section = _SECTION_MAP.get(raw["pubName"].strip(), raw["pubName"].strip())
            agency = raw["hierarchyStr"].strip()
            category = raw["artCategory"].strip()

            # Build URL from urlTitle
            url = f"https://www.in.gov.br/web/dou/-/{url_title}"

            acts.append({
                "act_id": act_id,
                "title": title,
                "act_type": act_type,
                "date": date,
                "section": section,
                "agency": agency,
                "category": category,
                "text_excerpt": abstract[:500] if abstract else "",
                "url": url,
                "source": "imprensa_nacional",
            })

            # Extract CPFs -> PUBLICOU relationships
            cpfs = _extract_cpfs(abstract)
            for cpf in cpfs:
                person_rels.append({
                    "source_key": cpf,
                    "target_key": act_id,
                })

            # Extract CNPJs -> MENCIONOU relationships
            cnpjs = _extract_cnpjs(abstract)
            for cnpj in cnpjs:
                company_rels.append({
                    "source_key": cnpj,
                    "target_key": act_id,
                })

        self.acts = deduplicate_rows(acts, ["act_id"])
        self.person_rels = person_rels
        self.company_rels = company_rels

        logger.info(
            "[dou] Transformed %d acts (%d person links, %d company links, skipped %d)",
            len(self.acts),
            len(self.person_rels),
            len(self.company_rels),
            skipped,
        )

    def load(self) -> None:
        if not self.acts:
            logger.warning("[dou] No acts to load")
            return

        loader = Neo4jBatchLoader(self.driver)

        # Load DOUAct nodes
        count = loader.load_nodes("DOUAct", self.acts, key_field="act_id")
        logger.info("[dou] Loaded %d DOUAct nodes", count)

        # PUBLICOU: Person -> DOUAct (match existing persons by CPF)
        if self.person_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (a:DOUAct {act_id: row.target_key}) "
                "MERGE (p)-[:PUBLICOU]->(a)"
            )
            count = loader.run_query_with_retry(query, self.person_rels)
            logger.info("[dou] Created %d PUBLICOU relationships", count)

        # MENCIONOU: Company -> DOUAct (match existing companies by CNPJ)
        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (a:DOUAct {act_id: row.target_key}) "
                "MERGE (c)-[:MENCIONOU]->(a)"
            )
            count = loader.run_query_with_retry(query, self.company_rels)
            logger.info("[dou] Created %d MENCIONOU relationships", count)
