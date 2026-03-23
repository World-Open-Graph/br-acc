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


def _generate_case_id(
    case_class: str, case_number: str, year: str,
) -> str:
    """Deterministic ID from case class + number + year."""
    raw = f"stj:{case_class}:{case_number}:{year}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class StjPipeline(Pipeline):
    """ETL pipeline for STJ (Superior Tribunal de Justiça) decisions.

    Data source: dadosabertos.stj.jus.br — CSV export of
    Superior Court decisions and proceedings.
    """

    name = "stj_dados_abertos"
    source_id = "stj_dados_abertos"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            driver, data_dir, limit=limit,
            chunk_size=chunk_size, **kwargs,
        )
        self._raw: pd.DataFrame = pd.DataFrame()
        self.cases: list[dict[str, Any]] = []
        self.rapporteur_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "stj_dados_abertos"
        csv_path = src_dir / "decisoes.csv"
        if not csv_path.exists():
            msg = f"STJ CSV not found: {csv_path}"
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path, dtype=str, keep_default_na=False,
        )
        logger.info(
            "[stj] Extracted %d case records", len(self._raw),
        )

    def transform(self) -> None:
        cases: list[dict[str, Any]] = []
        rapporteur_rels: list[dict[str, Any]] = []

        for row in self._raw.itertuples(index=False):
            case_class = str(
                getattr(row, "classe", "")
            ).strip()
            case_number = str(
                getattr(row, "numero", "")
            ).strip()
            year = str(getattr(row, "ano", "")).strip()

            if not case_class or not case_number:
                continue

            case_id = _generate_case_id(
                case_class, case_number, year,
            )
            rapporteur = normalize_name(
                str(getattr(row, "relator", ""))
            )
            decision_type = str(
                getattr(row, "tipo_decisao", "")
            ).strip()
            decision_date = str(
                getattr(row, "data_decisao", "")
            ).strip()
            subject = str(
                getattr(row, "assunto", "")
            ).strip()
            origin_state = str(
                getattr(row, "uf_origem", "")
            ).strip()

            cases.append({
                "case_id": case_id,
                "case_class": case_class,
                "case_number": case_number,
                "year": year,
                "rapporteur": rapporteur,
                "decision_type": decision_type,
                "decision_date": decision_date,
                "subject": subject,
                "origin_state": origin_state,
                "court": "STJ",
                "source": self.source_id,
            })

            if rapporteur:
                rapporteur_rels.append({
                    "source_key": rapporteur,
                    "target_key": case_id,
                })

            if self.limit and len(cases) >= self.limit:
                break

        self.cases = deduplicate_rows(cases, ["case_id"])
        self.rapporteur_rels = rapporteur_rels
        logger.info(
            "[stj] Transformed %d cases", len(self.cases),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.cases:
            loader.load_nodes(
                "LegalCase", self.cases, key_field="case_id",
            )

        if self.rapporteur_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (p:Person {name: row.source_key}) "
                "WITH p, row "
                "MATCH (lc:LegalCase {case_id: row.target_key}) "
                "MERGE (p)-[:RELATOR_DE]->(lc)"
            )
            loader.run_query_with_retry(
                query, self.rapporteur_rels,
            )
