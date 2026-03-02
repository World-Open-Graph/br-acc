from __future__ import annotations

import hashlib
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
    normalize_name,
    strip_document,
)

logger = logging.getLogger(__name__)


def _generate_penalty_id(cnpj_digits: str, process_number: str, penalty_type: str) -> str:
    """Deterministic ID from CNPJ digits + process number + penalty type."""
    raw = f"{cnpj_digits}:{process_number}:{penalty_type}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _parse_brl_value(raw: str) -> float | None:
    """Parse Brazilian currency string (e.g. '1.500.000,50') to float."""
    cleaned = raw.strip().replace(".", "").replace(",", ".")
    if not cleaned:
        return None
    try:
        return float(cleaned)
    except ValueError:
        return None


class BcbPipeline(Pipeline):
    """ETL pipeline for BCB (Banco Central do Brasil) penalties."""

    name = "bcb"
    source_id = "bcb"

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
        self.penalties: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        bcb_dir = Path(self.data_dir) / "bcb"
        self._raw = pd.read_csv(
            bcb_dir / "penalidades.csv",
            sep=";",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )

    def transform(self) -> None:
        penalties: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            cnpj_raw = str(row.get("CNPJ", ""))
            digits = strip_document(cnpj_raw)

            if len(digits) != 14:
                continue

            cnpj_formatted = format_cnpj(cnpj_raw)
            institution_name = normalize_name(str(row.get("Nome Instituição", "")))
            penalty_type = str(row.get("Tipo Penalidade", "")).strip()
            penalty_value_raw = str(row.get("Valor Penalidade", "")).strip()
            process_number = str(row.get("Número Processo", "")).strip()
            decision_date = str(row.get("Data Decisão", "")).strip()

            penalty_value = _parse_brl_value(penalty_value_raw)

            penalty_id = _generate_penalty_id(digits, process_number, penalty_type)

            penalty: dict[str, Any] = {
                "penalty_id": penalty_id,
                "cnpj": cnpj_formatted,
                "institution_name": institution_name,
                "penalty_type": penalty_type,
                "process_number": process_number,
                "decision_date": decision_date,
                "source": "bcb",
            }
            if penalty_value is not None:
                penalty["penalty_value"] = penalty_value

            penalties.append(penalty)

            company_rels.append({
                "source_key": cnpj_formatted,
                "target_key": penalty_id,
            })

        self.penalties = deduplicate_rows(penalties, ["penalty_id"])
        self.company_rels = company_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.penalties:
            loader.load_nodes("BCBPenalty", self.penalties, key_field="penalty_id")

        # Ensure Company nodes exist for CNPJ linking
        if self.company_rels:
            companies = [
                {"cnpj": rel["source_key"]} for rel in self.company_rels
            ]
            loader.load_nodes("Company", deduplicate_rows(companies, ["cnpj"]), key_field="cnpj")

        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (b:BCBPenalty {penalty_id: row.target_key}) "
                "MERGE (c)-[:BCB_PENALIZADA]->(b)"
            )
            loader.run_query_with_retry(query, self.company_rels)
