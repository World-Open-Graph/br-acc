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
    normalize_name,
)

logger = logging.getLogger(__name__)

# OFAC SDN CSV has no header row. Column names assigned positionally.
SDN_COLUMNS = [
    "ent_num",
    "sdn_name",
    "sdn_type",
    "program",
    "title",
    "call_sign",
    "vess_type",
    "tonnage",
    "grt",
    "vess_flag",
    "vess_owner",
    "remarks",
]

# SDN types we care about
SDN_TYPE_INDIVIDUAL = "individual"
SDN_TYPE_ENTITY = "entity"
VALID_SDN_TYPES = {SDN_TYPE_INDIVIDUAL, SDN_TYPE_ENTITY}


def _clean_sdn_type(raw: str) -> str:
    """Normalize SDN_Type field (strip whitespace, dashes, lowercase)."""
    cleaned = raw.strip().strip("-").strip().lower()
    return cleaned


class OfacPipeline(Pipeline):
    """ETL pipeline for OFAC SDN (US Treasury Specially Designated Nationals) data.

    Loads all SDN entries as InternationalSanction nodes.
    Matching to existing Company/Person nodes is done separately
    via entity resolution.
    """

    name = "ofac"
    source_id = "ofac_sdn"

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
        ofac_dir = Path(self.data_dir) / "ofac"
        csv_path = ofac_dir / "sdn.csv"

        if not csv_path.exists():
            logger.warning("[ofac] sdn.csv not found at %s", csv_path)
            return

        logger.info("[ofac] Reading %s", csv_path)
        self._raw = pd.read_csv(
            csv_path,
            header=None,
            names=SDN_COLUMNS,
            dtype=str,
            encoding="utf-8",
            keep_default_na=False,
            on_bad_lines="skip",
        )

        if self.limit:
            self._raw = self._raw.head(self.limit)

        logger.info("[ofac] Extracted %d rows", len(self._raw))

    def transform(self) -> None:
        sanctions: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            ent_num = str(row["ent_num"]).strip()
            if not ent_num:
                continue

            sdn_type = _clean_sdn_type(str(row["sdn_type"]))
            if sdn_type not in VALID_SDN_TYPES:
                continue

            name_raw = str(row["sdn_name"]).strip()
            if not name_raw:
                continue

            sanctions.append({
                "sanction_id": f"ofac_{ent_num}",
                "name": normalize_name(name_raw),
                "original_name": name_raw,
                "sdn_type": sdn_type,
                "program": str(row["program"]).strip(),
                "title": str(row["title"]).strip(),
                "remarks": str(row["remarks"]).strip(),
                "source": "ofac_sdn",
            })

        self.sanctions = deduplicate_rows(sanctions, ["sanction_id"])

        logger.info(
            "[ofac] Transformed %d InternationalSanction nodes",
            len(self.sanctions),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.sanctions:
            loaded = loader.load_nodes(
                "InternationalSanction", self.sanctions, key_field="sanction_id"
            )
            logger.info("[ofac] Loaded %d InternationalSanction nodes", loaded)
