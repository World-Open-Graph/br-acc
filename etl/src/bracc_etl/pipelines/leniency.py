from __future__ import annotations

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
    normalize_name,
    parse_date,
    strip_document,
)


class LeniencyPipeline(Pipeline):
    """ETL pipeline for Acordos de Leniencia (CGU leniency agreements)."""

    name = "leniency"
    source_id = "cgu_leniencia"

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
        self.agreements: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        leniency_dir = Path(self.data_dir) / "leniency"
        self._raw = pd.read_csv(
            leniency_dir / "leniencia.csv",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )

    def transform(self) -> None:
        agreements: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            cnpj_raw = str(row.get("cnpj", ""))
            digits = strip_document(cnpj_raw)

            if len(digits) != 14:
                continue

            cnpj_formatted = format_cnpj(cnpj_raw)
            nome = normalize_name(str(row.get("razao_social", "")))
            start_date = parse_date(str(row.get("data_inicio", "")))
            end_date_raw = parse_date(str(row.get("data_fim", "")))
            end_date = end_date_raw if end_date_raw else None
            status = str(row.get("situacao", "")).strip()
            responsible_agency = str(row.get("orgao_responsavel", "")).strip()
            proceedings_raw = str(row.get("qtd_processos", "")).strip()
            proceedings_count = int(proceedings_raw) if proceedings_raw.isdigit() else 0

            leniency_id = f"leniencia_{digits}"

            agreements.append({
                "leniency_id": leniency_id,
                "cnpj": cnpj_formatted,
                "name": nome,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "responsible_agency": responsible_agency,
                "proceedings_count": proceedings_count,
                "source": "cgu_leniencia",
            })

            company_rels.append({
                "source_key": cnpj_formatted,
                "target_key": leniency_id,
                "company_name": nome,
            })

        self.agreements = deduplicate_rows(agreements, ["leniency_id"])
        self.company_rels = company_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.agreements:
            loader.load_nodes(
                "LeniencyAgreement", self.agreements, key_field="leniency_id",
            )

        # Ensure Company nodes exist
        for rel in self.company_rels:
            loader.load_nodes(
                "Company",
                [{
                    "cnpj": rel["source_key"],
                    "name": rel["company_name"],
                    "razao_social": rel["company_name"],
                }],
                key_field="cnpj",
            )

        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (l:LeniencyAgreement {leniency_id: row.target_key}) "
                "MERGE (c)-[:FIRMOU_LENIENCIA]->(l)"
            )
            loader.run_query_with_retry(query, self.company_rels)
