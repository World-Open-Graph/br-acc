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


def _generate_liquidation_id(cnpj_digits: str, regime: str) -> str:
    """Deterministic ID from CNPJ + regime type."""
    raw = f"{cnpj_digits}:{regime}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class BcbLiquidacaoPipeline(Pipeline):
    """ETL pipeline for BCB (Banco Central) liquidated financial institutions.

    Data source: dados.bcb.gov.br — CSV export of institutions
    under special regimes (intervention, liquidation, RAET).
    """

    name = "bcb_liquidacao"
    source_id = "bcb_liquidacao"

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
        self.liquidations: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "bcb_liquidacao"
        csv_path = src_dir / "regimes_especiais.csv"
        if not csv_path.exists():
            msg = f"BCB Liquidacao CSV not found: {csv_path}"
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path,
            sep=";",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )
        logger.info(
            "[bcb_liquidacao] Extracted %d records", len(self._raw),
        )

    def transform(self) -> None:
        liquidations: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []

        for row in self._raw.itertuples(index=False):
            cnpj_raw = str(getattr(row, "CNPJ", "")).strip()
            digits = strip_document(cnpj_raw)
            if len(digits) != 14:
                continue

            cnpj = format_cnpj(cnpj_raw)
            name = normalize_name(
                str(getattr(row, "Instituicao", ""))
            )
            regime = str(getattr(row, "Regime", "")).strip()
            decree_date = str(
                getattr(row, "Data_Decreto", "")
            ).strip()
            end_date = str(
                getattr(row, "Data_Encerramento", "")
            ).strip()
            situation = str(
                getattr(row, "Situacao", "")
            ).strip()

            liq_id = _generate_liquidation_id(digits, regime)

            liquidations.append({
                "liquidation_id": liq_id,
                "cnpj": cnpj,
                "institution_name": name,
                "regime": regime,
                "decree_date": decree_date,
                "end_date": end_date,
                "situation": situation,
                "source": self.source_id,
            })

            company_rels.append({
                "source_key": cnpj,
                "target_key": liq_id,
            })

            if self.limit and len(liquidations) >= self.limit:
                break

        self.liquidations = deduplicate_rows(
            liquidations, ["liquidation_id"],
        )
        self.company_rels = company_rels
        logger.info(
            "[bcb_liquidacao] Transformed %d liquidations",
            len(self.liquidations),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.liquidations:
            loader.load_nodes(
                "BankLiquidation", self.liquidations,
                key_field="liquidation_id",
            )

        if self.company_rels:
            companies = [
                {"cnpj": rel["source_key"]}
                for rel in self.company_rels
            ]
            loader.load_nodes(
                "Company",
                deduplicate_rows(companies, ["cnpj"]),
                key_field="cnpj",
            )

        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (b:BankLiquidation "
                "{liquidation_id: row.target_key}) "
                "MERGE (c)-[:REGIME_ESPECIAL]->(b)"
            )
            loader.run_query_with_retry(query, self.company_rels)
