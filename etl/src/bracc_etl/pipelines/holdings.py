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
    format_cnpj,
    strip_document,
)

logger = logging.getLogger(__name__)


class HoldingsPipeline(Pipeline):
    """ETL pipeline for Brasil.IO company-company ownership (holdings) data.

    Creates HOLDING_DE relationships between existing Company nodes.
    A HOLDING_DE relationship means Company A holds shares in Company B
    (Company A is a corporate shareholder of Company B).
    """

    name = "holdings"
    source_id = "brasil_io_holdings"

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
        self.holding_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        holdings_dir = Path(self.data_dir) / "holdings"

        # Try gzipped CSV first, then plain CSV
        gz_path = holdings_dir / "holding.csv.gz"
        csv_path = holdings_dir / "holding.csv"

        read_opts: dict[str, Any] = {
            "dtype": str,
            "keep_default_na": False,
        }

        if gz_path.exists():
            logger.info("[holdings] Reading %s", gz_path)
            self._raw = pd.read_csv(gz_path, compression="gzip", **read_opts)
        elif csv_path.exists():
            logger.info("[holdings] Reading %s", csv_path)
            self._raw = pd.read_csv(csv_path, **read_opts)
        else:
            logger.warning(
                "[holdings] No holding.csv or holding.csv.gz found at %s", holdings_dir
            )
            return

        if self.limit:
            self._raw = self._raw.head(self.limit)

        logger.info("[holdings] Extracted %d rows", len(self._raw))

    def transform(self) -> None:
        rels: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            # Support both column naming conventions
            cnpj_empresa_raw = str(
                row.get("cnpj_empresa") or row.get("cnpj") or ""
            ).strip()
            cnpj_socia_raw = str(
                row.get("cnpj_socia") or row.get("holding_cnpj") or ""
            ).strip()

            # Validate both CNPJs have exactly 14 digits
            digits_empresa = strip_document(cnpj_empresa_raw)
            digits_socia = strip_document(cnpj_socia_raw)

            if len(digits_empresa) != 14 or len(digits_socia) != 14:
                continue

            cnpj_empresa = format_cnpj(digits_empresa)
            cnpj_socia = format_cnpj(digits_socia)

            # Skip self-holding (company owns itself)
            if cnpj_empresa == cnpj_socia:
                continue

            rels.append({
                "source_key": cnpj_socia,
                "target_key": cnpj_empresa,
            })

        self.holding_rels = rels

        logger.info(
            "[holdings] Transformed %d HOLDING_DE relationships",
            len(self.holding_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.holding_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (holder:Company {cnpj: row.source_key}) "
                "MATCH (held:Company {cnpj: row.target_key}) "
                "MERGE (holder)-[:HOLDING_DE]->(held)"
            )
            loaded = loader.run_query_with_retry(query, self.holding_rels)
            logger.info("[holdings] Loaded %d HOLDING_DE relationships", loaded)
