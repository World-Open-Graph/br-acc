from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    format_cpf,
    normalize_name,
    parse_date,
    strip_document,
)

logger = logging.getLogger(__name__)


class IbamaPipeline(Pipeline):
    """ETL pipeline for IBAMA environmental enforcement data.

    Ingests embargoed areas (Termos de Embargo) from IBAMA open data.
    Each record links a person or company to an environmental embargo
    with associated infraction data, biome, area, and location.
    """

    name = "ibama"
    source_id = "ibama"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw: pd.DataFrame = pd.DataFrame()
        self.embargoes: list[dict[str, Any]] = []
        self.companies: list[dict[str, Any]] = []
        self.persons: list[dict[str, Any]] = []
        self.embargo_rels: list[dict[str, Any]] = []

    def _parse_area(self, value: str) -> float:
        """Parse area in hectares (Brazilian decimal format: comma separator)."""
        value = value.strip().replace(",", ".")
        try:
            return float(value)
        except ValueError:
            return 0.0

    def _primary_biome(self, value: str) -> str:
        """Extract the primary biome from a comma-separated list."""
        value = value.strip()
        if not value:
            return ""
        return value.split(",")[0].strip()

    def extract(self) -> None:
        ibama_dir = Path(self.data_dir) / "ibama"
        if not ibama_dir.exists():
            logger.warning("[%s] Data directory not found: %s", self.name, ibama_dir)
            return
        csv_path = ibama_dir / "areas_embargadas.csv"
        if not csv_path.exists():
            logger.warning("[%s] CSV file not found: %s", self.name, csv_path)
            return
        logger.info("[ibama] Reading %s", csv_path)
        self._raw = pd.read_csv(
            csv_path,
            sep=";",
            dtype=str,
            encoding="utf-8",
            keep_default_na=False,
            on_bad_lines="skip",
            usecols=lambda c: c != "WKT_GEOM_AREA_EMBARGADA",
        )
        if self.limit:
            self._raw = self._raw.head(self.limit)
        logger.info("[ibama] Extracted %d rows", len(self._raw))

    def transform(self) -> None:
        embargoes: list[dict[str, Any]] = []
        companies: list[dict[str, Any]] = []
        persons: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            seq = str(row["SEQ_TAD"]).strip()
            if not seq:
                continue

            doc_raw = str(row["CPF_CNPJ_EMBARGADO"]).strip()
            digits = strip_document(doc_raw)
            nome = normalize_name(str(row["NOME_PESSOA_EMBARGADA"]))
            is_company = len(digits) == 14
            is_person = len(digits) == 11

            if not is_company and not is_person:
                continue

            doc_formatted = format_cnpj(doc_raw) if is_company else format_cpf(doc_raw)

            embargo_id = f"ibama_embargo_{seq}"
            date_embargo = parse_date(str(row["DAT_EMBARGO"]))
            area_ha = self._parse_area(str(row["QTD_AREA_EMBARGADA"]))
            biome = self._primary_biome(str(row["DES_TIPO_BIOMA"]))
            uf = str(row["SIG_UF_TAD"]).strip()
            municipio = str(row["NOM_MUNICIPIO_TAD"]).strip()
            infraction_desc = str(row["DES_INFRACAO"]).strip()[:500]
            auto_num = str(row["NUM_AUTO_INFRACAO"]).strip()
            processo = str(row["NUM_PROCESSO"]).strip()

            embargoes.append({
                "embargo_id": embargo_id,
                "date": date_embargo,
                "area_ha": area_ha,
                "biome": biome,
                "uf": uf,
                "municipio": municipio,
                "infraction": infraction_desc,
                "auto_infracao": auto_num,
                "processo": processo,
                "source": "ibama",
            })

            if is_company:
                companies.append({
                    "cnpj": doc_formatted,
                    "razao_social": nome,
                    "name": nome,
                })
            else:
                persons.append({
                    "cpf": doc_formatted,
                    "name": nome,
                })

            rels.append({
                "source_key": doc_formatted,
                "target_key": embargo_id,
                "is_company": is_company,
            })

        self.embargoes = deduplicate_rows(embargoes, ["embargo_id"])
        self.companies = deduplicate_rows(companies, ["cnpj"])
        self.persons = deduplicate_rows(persons, ["cpf"])
        self.embargo_rels = rels

        logger.info(
            "[ibama] Transformed: %d embargoes, %d companies, %d persons, %d rels",
            len(self.embargoes),
            len(self.companies),
            len(self.persons),
            len(self.embargo_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.embargoes:
            logger.info("[ibama] Loading %d Embargo nodes...", len(self.embargoes))
            loader.load_nodes("Embargo", self.embargoes, key_field="embargo_id")

        if self.companies:
            logger.info("[ibama] MERGEing %d Company nodes...", len(self.companies))
            loader.load_nodes("Company", self.companies, key_field="cnpj")

        if self.persons:
            logger.info("[ibama] MERGEing %d Person nodes...", len(self.persons))
            loader.load_nodes("Person", self.persons, key_field="cpf")

        if self.embargo_rels:
            logger.info("[ibama] Loading %d EMBARGADA rels...", len(self.embargo_rels))
            query = (
                "UNWIND $rows AS row "
                "MATCH (e:Embargo {embargo_id: row.target_key}) "
                "OPTIONAL MATCH (c:Company {cnpj: row.source_key}) "
                "OPTIONAL MATCH (p:Person {cpf: row.source_key}) "
                "WITH e, coalesce(c, p) AS entity "
                "WHERE entity IS NOT NULL "
                "MERGE (entity)-[:EMBARGADA]->(e)"
            )
            loader.run_query(query, self.embargo_rels)

        logger.info("[ibama] Load complete.")
