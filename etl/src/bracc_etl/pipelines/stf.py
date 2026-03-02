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
from bracc_etl.transforms import deduplicate_rows, normalize_name

logger = logging.getLogger(__name__)


def _generate_case_id(case_class: str, case_number: str, year: str) -> str:
    """Deterministic ID from case class + number + year."""
    raw = f"{case_class}:{case_number}:{year}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class StfPipeline(Pipeline):
    """ETL pipeline for STF (Supremo Tribunal Federal) decisions.

    Data source: BigQuery table basedosdados.br_stf_corte_aberta.decisoes,
    pre-exported to CSV via download script.
    """

    name = "stf"
    source_id = "stf"

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
        self.cases: list[dict[str, Any]] = []
        self.rapporteur_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        stf_dir = Path(self.data_dir) / "stf"
        self._raw = pd.read_csv(
            stf_dir / "decisoes.csv",
            dtype=str,
            keep_default_na=False,
        )

    def transform(self) -> None:
        cases: list[dict[str, Any]] = []
        rapporteur_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            case_class = str(row.get("classe", "")).strip()
            case_number = str(row.get("numero", "")).strip()
            year = str(row.get("ano", "")).strip()

            if not case_class or not case_number or not year:
                continue

            case_id = _generate_case_id(case_class, case_number, year)
            rapporteur_raw = str(row.get("relator", "")).strip()
            rapporteur = normalize_name(rapporteur_raw)
            decision_type = str(
                row.get("tipo_decisao", "") or row.get("andamento", "")
            ).strip()
            decision_date = str(row.get("data_decisao", "")).strip()
            subject = str(
                row.get("assunto", "") or row.get("assunto_processo", "")
            ).strip()
            origin = str(
                row.get("procedencia", "") or row.get("ramo_direito", "")
            ).strip()

            case: dict[str, Any] = {
                "case_id": case_id,
                "case_class": case_class,
                "case_number": case_number,
                "year": year,
                "rapporteur": rapporteur,
                "decision_type": decision_type,
                "decision_date": decision_date,
                "subject": subject,
                "origin": origin,
                "source": "stf",
            }
            cases.append(case)

            if rapporteur:
                rapporteur_rels.append(
                    {
                        "source_key": rapporteur,
                        "target_key": case_id,
                    }
                )

        self.cases = deduplicate_rows(cases, ["case_id"])
        self.rapporteur_rels = rapporteur_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.cases:
            loader.load_nodes("LegalCase", self.cases, key_field="case_id")

        if self.rapporteur_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {name: row.source_key}) "
                "MATCH (lc:LegalCase {case_id: row.target_key}) "
                "MERGE (p)-[:RELATOR_DE]->(lc)"
            )
            loader.run_query_with_retry(query, self.rapporteur_rels)
