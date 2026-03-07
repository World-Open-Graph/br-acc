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


def _generate_participation_id(
    investor_doc: str, fund_cnpj: str,
) -> str:
    """Deterministic ID from investor document + fund CNPJ."""
    raw = f"cvm_own:{investor_doc}:{fund_cnpj}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CvmFullOwnershipPipeline(Pipeline):
    """ETL pipeline for CVM full ownership chains.

    Data source: dados.cvm.gov.br — CSV exports of shareholder
    participation in public companies and investment funds,
    revealing beneficial ownership chains.
    """

    name = "cvm_full_ownership_chain"
    source_id = "cvm_full_ownership_chain"

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
        self.participants: list[dict[str, Any]] = []
        self.ownership_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = (
            Path(self.data_dir) / "cvm_full_ownership_chain"
        )
        csv_path = src_dir / "participantes.csv"
        if not csv_path.exists():
            msg = (
                f"CVM ownership CSV not found: {csv_path}"
            )
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path, sep=";", dtype=str,
            encoding="latin-1", keep_default_na=False,
        )
        logger.info(
            "[cvm_ownership] Extracted %d records",
            len(self._raw),
        )

    def transform(self) -> None:
        participants: list[dict[str, Any]] = []
        ownership_rels: list[dict[str, Any]] = []

        for row in self._raw.itertuples(index=False):
            investor_doc_raw = str(
                getattr(row, "CNPJ_CPF_Investidor", "")
            ).strip()
            fund_cnpj_raw = str(
                getattr(row, "CNPJ_Fundo", "")
            ).strip()

            investor_digits = strip_document(investor_doc_raw)
            fund_digits = strip_document(fund_cnpj_raw)

            if len(fund_digits) != 14:
                continue

            fund_cnpj = format_cnpj(fund_cnpj_raw)
            investor_name = normalize_name(
                str(getattr(row, "Nome_Investidor", ""))
            )
            investor_type = str(
                getattr(row, "Tipo_Investidor", "")
            ).strip()
            share_pct_raw = str(
                getattr(row, "Percentual", "")
            ).strip()
            share_date = str(
                getattr(row, "Data_Referencia", "")
            ).strip()

            try:
                share_pct = float(
                    share_pct_raw.replace(",", ".")
                )
            except ValueError:
                share_pct = 0.0

            part_id = _generate_participation_id(
                investor_digits, fund_digits,
            )

            participants.append({
                "participation_id": part_id,
                "investor_document": investor_digits,
                "investor_name": investor_name,
                "investor_type": investor_type,
                "fund_cnpj": fund_cnpj,
                "share_pct": share_pct,
                "reference_date": share_date,
                "source": self.source_id,
            })

            # Investor is CNPJ = Company-to-Company
            if len(investor_digits) == 14:
                investor_cnpj = format_cnpj(investor_doc_raw)
                ownership_rels.append({
                    "source_key": investor_cnpj,
                    "target_key": fund_cnpj,
                    "share_pct": share_pct,
                })

            if self.limit and len(participants) >= self.limit:
                break

        self.participants = deduplicate_rows(
            participants, ["participation_id"],
        )
        self.ownership_rels = ownership_rels
        logger.info(
            "[cvm_ownership] Transformed %d participants, "
            "%d ownership links",
            len(self.participants),
            len(self.ownership_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.participants:
            loader.load_nodes(
                "CvmParticipation", self.participants,
                key_field="participation_id",
            )

        # Create Company-to-Company ownership edges
        if self.ownership_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (a:Company {cnpj: row.source_key}) "
                "MERGE (b:Company {cnpj: row.target_key}) "
                "MERGE (a)-[r:DETEM_PARTICIPACAO]->(b) "
                "SET r.share_pct = row.share_pct"
            )
            loader.run_query_with_retry(
                query, self.ownership_rels,
            )
