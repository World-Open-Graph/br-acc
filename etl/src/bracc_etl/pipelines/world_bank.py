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
    normalize_name,
)

logger = logging.getLogger(__name__)


def _make_debarment_id(firm_name: str, country: str, from_date: str) -> str:
    """Deterministic ID from firm name + country + from_date."""
    raw = f"{firm_name}|{country}|{from_date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class WorldBankPipeline(Pipeline):
    """ETL pipeline for World Bank Debarred Firms & Individuals.

    Data source: World Bank Group sanctions list (CSV).
    Loads InternationalSanction nodes with source_list='WORLD_BANK'.
    """

    name = "world_bank"
    source_id = "world_bank"

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
        self.sanctions: list[dict[str, Any]] = []

    def extract(self) -> None:
        wb_dir = Path(self.data_dir) / "world_bank"
        csv_path = wb_dir / "debarred.csv"

        if not csv_path.exists():
            logger.warning("[world_bank] debarred.csv not found at %s", csv_path)
            return

        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False,
        )

        if self.limit:
            self._raw = self._raw.head(self.limit)

        logger.info("[world_bank] Extracted %d rows", len(self._raw))

    def transform(self) -> None:
        sanctions: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            # Support both old column names (Firm Name) and new API format (SUPP_NAME)
            firm_name_raw = str(
                row.get("Firm Name") or row.get("SUPP_NAME") or ""
            ).strip()
            if not firm_name_raw:
                continue

            country = str(
                row.get("Country") or row.get("COUNTRY_NAME") or ""
            ).strip()
            from_date = str(
                row.get("From Date") or row.get("DEBAR_FROM_DATE") or ""
            ).strip()
            to_date = str(
                row.get("To Date") or row.get("DEBAR_TO_DATE") or ""
            ).strip()
            grounds = str(
                row.get("Grounds") or row.get("DEBAR_REASON") or ""
            ).strip()

            sanction_id = _make_debarment_id(firm_name_raw, country, from_date)

            sanctions.append({
                "sanction_id": sanction_id,
                "name": normalize_name(firm_name_raw),
                "original_name": firm_name_raw,
                "country": country,
                "from_date": from_date,
                "to_date": to_date,
                "grounds": grounds,
                "source": "world_bank",
                "source_list": "WORLD_BANK",
            })

        self.sanctions = deduplicate_rows(sanctions, ["sanction_id"])
        logger.info(
            "[world_bank] Transformed %d InternationalSanction nodes",
            len(self.sanctions),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.sanctions:
            loaded = loader.load_nodes(
                "InternationalSanction",
                self.sanctions,
                key_field="sanction_id",
            )
            logger.info("[world_bank] Loaded %d InternationalSanction nodes", loaded)
