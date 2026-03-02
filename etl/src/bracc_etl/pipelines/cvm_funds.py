"""ETL pipeline for CVM fund registry data (Fundos de Investimento).

Ingests fund registration data from CVM Dados Abertos (cad_fi.csv).
Creates Fund nodes linked to Company nodes via ADMINISTRA and GERE relationships.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    normalize_name,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

# Keep all fund statuses — historical data valuable for connection analysis.
# Status is stored on each Fund node for downstream filtering.
_EXCLUDED_STATUSES: frozenset[str] = frozenset()


class CvmFundsPipeline(Pipeline):
    """ETL pipeline for CVM fund registry (cad_fi.csv)."""

    name = "cvm_funds"
    source_id = "cvm_funds"

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
        self.funds: list[dict[str, Any]] = []
        self.admin_rels: list[dict[str, Any]] = []
        self.manager_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        cvm_funds_dir = Path(self.data_dir) / "cvm_funds"
        csv_path = cvm_funds_dir / "cad_fi.csv"

        if not csv_path.exists():
            msg = f"CVM fund registry file not found: {csv_path}"
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path,
            sep=";",
            dtype=str,
            keep_default_na=False,
            encoding="latin-1",
        )

        logger.info("[cvm_funds] Extracted %d rows from cad_fi.csv", len(self._raw))

    def transform(self) -> None:
        funds: list[dict[str, Any]] = []
        admin_rels: list[dict[str, Any]] = []
        manager_rels: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            # Fund CNPJ
            fund_cnpj_raw = str(row.get("CNPJ_FUNDO", "")).strip()
            fund_digits = strip_document(fund_cnpj_raw)
            if len(fund_digits) != 14:
                continue

            fund_cnpj = format_cnpj(fund_digits)

            status = str(row.get("SIT", "")).strip().upper()
            if status in _EXCLUDED_STATUSES:
                continue

            fund_name = normalize_name(str(row.get("DENOM_SOCIAL", "")))
            fund_type = str(row.get("CLASSE", "")).strip()

            # Administrator CNPJ
            admin_cnpj_raw = str(row.get("CNPJ_ADMIN", "")).strip()
            admin_digits = strip_document(admin_cnpj_raw)
            admin_cnpj = format_cnpj(admin_digits) if len(admin_digits) == 14 else ""
            admin_name = normalize_name(str(row.get("ADMIN", "")))

            # Manager CNPJ (can be PF or PJ — only use PJ)
            pf_pj = str(row.get("PF_PJ_GESTOR", "")).strip().upper()
            manager_cnpj_raw = str(row.get("CPF_CNPJ_GESTOR", "")).strip()
            manager_digits = strip_document(manager_cnpj_raw)
            manager_cnpj = ""
            if pf_pj == "PJ" and len(manager_digits) == 14:
                manager_cnpj = format_cnpj(manager_digits)
            manager_name = normalize_name(str(row.get("GESTOR", "")))

            funds.append({
                "fund_cnpj": fund_cnpj,
                "fund_name": fund_name,
                "fund_type": fund_type,
                "administrator_cnpj": admin_cnpj,
                "administrator_name": admin_name,
                "manager_cnpj": manager_cnpj,
                "manager_name": manager_name,
                "status": status,
                "source": "cvm_funds",
            })

            # ADMINISTRA relationship
            if admin_cnpj:
                admin_rels.append({
                    "source_key": admin_cnpj,
                    "target_key": fund_cnpj,
                    "admin_name": admin_name,
                })

            # GERE relationship
            if manager_cnpj:
                manager_rels.append({
                    "source_key": manager_cnpj,
                    "target_key": fund_cnpj,
                    "manager_name": manager_name,
                })

        self.funds = deduplicate_rows(funds, ["fund_cnpj"])

        if self.limit:
            self.funds = self.funds[: self.limit]

        # Deduplicate rels based on source+target pair
        seen_admin: set[tuple[str, str]] = set()
        deduped_admin: list[dict[str, Any]] = []
        for rel in admin_rels:
            pair = (rel["source_key"], rel["target_key"])
            if pair not in seen_admin:
                seen_admin.add(pair)
                deduped_admin.append(rel)
        self.admin_rels = deduped_admin

        seen_mgr: set[tuple[str, str]] = set()
        deduped_mgr: list[dict[str, Any]] = []
        for rel in manager_rels:
            pair = (rel["source_key"], rel["target_key"])
            if pair not in seen_mgr:
                seen_mgr.add(pair)
                deduped_mgr.append(rel)
        self.manager_rels = deduped_mgr

        logger.info(
            "[cvm_funds] Transformed: %d funds, %d ADMINISTRA rels, %d GERE rels",
            len(self.funds),
            len(self.admin_rels),
            len(self.manager_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.funds:
            loaded = loader.load_nodes("Fund", self.funds, key_field="fund_cnpj")
            logger.info("[cvm_funds] Loaded %d Fund nodes", loaded)

        if self.admin_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (c:Company {cnpj: row.source_key}) "
                "ON CREATE SET c.razao_social = row.admin_name, c.name = row.admin_name "
                "WITH c, row "
                "MATCH (f:Fund {fund_cnpj: row.target_key}) "
                "MERGE (c)-[:ADMINISTRA]->(f)"
            )
            loaded = loader.run_query_with_retry(query, self.admin_rels, batch_size=500)
            logger.info("[cvm_funds] Loaded %d ADMINISTRA relationships", loaded)

        if self.manager_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (c:Company {cnpj: row.source_key}) "
                "ON CREATE SET c.razao_social = row.manager_name, c.name = row.manager_name "
                "WITH c, row "
                "MATCH (f:Fund {fund_cnpj: row.target_key}) "
                "MERGE (c)-[:GERE]->(f)"
            )
            loaded = loader.run_query_with_retry(query, self.manager_rels, batch_size=500)
            logger.info("[cvm_funds] Loaded %d GERE relationships", loaded)
