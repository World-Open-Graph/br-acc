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
    format_cpf,
    normalize_name,
    strip_document,
)

logger = logging.getLogger(__name__)


def _parse_value(raw: str) -> float:
    """Parse a monetary value string to float. Returns 0.0 on failure."""
    if not raw:
        return 0.0
    cleaned = raw.strip().replace(",", ".")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


def _make_asset_id(cpf: str, year: str, asset_type: str, value: str, description: str) -> str:
    """Generate deterministic asset_id from key fields."""
    payload = f"{cpf}|{year}|{asset_type}|{value}|{description}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


class TseBensPipeline(Pipeline):
    """ETL pipeline for TSE Bens Declarados (candidate declared assets)."""

    name = "tse_bens"
    source_id = "tse_bens"

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
        self.assets: list[dict[str, Any]] = []
        self.person_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        bens_dir = Path(self.data_dir) / "tse_bens"
        csv_path = bens_dir / "bens.csv"
        if not csv_path.exists():
            msg = f"Data file not found: {csv_path}"
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False,
        )
        if self.limit:
            self._raw = self._raw.head(self.limit)
        logger.info("[tse_bens] Extracted %d rows", len(self._raw))

    def transform(self) -> None:
        assets: list[dict[str, Any]] = []
        person_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            cpf_raw = str(row.get("cpf", ""))
            digits = strip_document(cpf_raw)

            if len(digits) != 11:
                continue

            cpf_formatted = format_cpf(cpf_raw)
            nome = normalize_name(str(row.get("nome_candidato", "")))
            year = str(row.get("ano", "")).strip()
            asset_type = str(row.get("tipo_bem", "")).strip()
            description = str(row.get("descricao_bem", "")).strip()
            value_raw = str(row.get("valor_bem", ""))
            value = _parse_value(value_raw)
            uf = str(row.get("sigla_uf", "")).strip()
            partido = str(row.get("sigla_partido", "")).strip()

            asset_id = _make_asset_id(digits, year, asset_type, value_raw.strip(), description)

            assets.append({
                "asset_id": asset_id,
                "candidate_cpf": cpf_formatted,
                "candidate_name": nome,
                "asset_type": asset_type,
                "asset_description": description,
                "asset_value": value,
                "election_year": int(year) if year.isdigit() else 0,
                "uf": uf,
                "partido": partido,
                "source": "tse_bens",
            })

            person_rels.append({
                "source_key": cpf_formatted,
                "target_key": asset_id,
                "person_name": nome,
            })

        self.assets = deduplicate_rows(assets, ["asset_id"])
        self.person_rels = person_rels
        logger.info(
            "[tse_bens] Transformed: %d assets, %d person rels",
            len(self.assets),
            len(self.person_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.assets:
            loader.load_nodes("DeclaredAsset", self.assets, key_field="asset_id")

        # Ensure Person nodes exist for each candidate
        persons_seen: set[str] = set()
        unique_persons: list[dict[str, Any]] = []
        for rel in self.person_rels:
            cpf = rel["source_key"]
            if cpf not in persons_seen:
                persons_seen.add(cpf)
                unique_persons.append({"cpf": cpf, "name": rel["person_name"]})
        if unique_persons:
            loader.load_nodes("Person", unique_persons, key_field="cpf")

        if self.person_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (a:DeclaredAsset {asset_id: row.target_key}) "
                "MERGE (p)-[:DECLAROU_BEM]->(a)"
            )
            loader.run_query_with_retry(query, self.person_rels)

        logger.info(
            "[tse_bens] Loaded: %d assets, %d persons, %d rels",
            len(self.assets),
            len(persons_seen),
            len(self.person_rels),
        )
