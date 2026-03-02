"""ETL pipeline for TSE Filiados (party membership) data.

Data source: BigQuery table basedosdados.br_tse_filiacao_partidaria.microdados
Pre-exported to CSV via download script.

Limitation: TSE filiados data does NOT contain CPF. Matching to existing
Person nodes uses tiered confidence: name+UF+birth_date (high),
name+UF+municipality (medium), name+UF only (low). A match_confidence
property is stored on the relationship to make this transparent.
"""

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
    parse_date,
)

logger = logging.getLogger(__name__)


def _membership_id(name: str, party: str, uf: str, affiliation_date: str) -> str:
    """Deterministic ID from name + party + UF + date."""
    raw = f"{name}|{party}|{uf}|{affiliation_date}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class TseFiliadosPipeline(Pipeline):
    """ETL pipeline for TSE party membership (filiacao partidaria)."""

    name = "tse_filiados"
    source_id = "tse_filiados"

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
        self.memberships: list[dict[str, Any]] = []
        self.person_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        filiados_dir = Path(self.data_dir) / "tse_filiados"
        csv_path = filiados_dir / "filiados.csv"

        if not csv_path.exists():
            logger.warning("[tse_filiados] filiados.csv not found at %s", csv_path)
            return

        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            keep_default_na=False,
        )
        if self.limit:
            self._raw = self._raw.head(self.limit)

        logger.info("[tse_filiados] Extracted %d raw rows", len(self._raw))

    def transform(self) -> None:
        memberships: list[dict[str, Any]] = []
        person_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            nome_raw = str(row.get("nome", "")).strip()
            if not nome_raw:
                continue

            nome = normalize_name(nome_raw)
            if not nome:
                continue

            party = str(row.get("sigla_partido", "")).strip().upper()
            if not party:
                continue

            uf = str(row.get("sigla_uf", "")).strip().upper()
            affiliation_date = parse_date(str(row.get("data_filiacao", "")))
            status = str(row.get("situacao_registro", "")).strip()
            municipality_id = str(row.get("id_municipio_tse", "")).strip()
            birth_date = parse_date(str(row.get("data_nascimento", "")))

            mid = _membership_id(nome, party, uf, affiliation_date)

            memberships.append({
                "membership_id": mid,
                "name": nome,
                "party": party,
                "uf": uf,
                "affiliation_date": affiliation_date,
                "status": status,
                "municipality_id": municipality_id,
                "birth_date": birth_date,
                "source": "tse_filiados",
            })

            person_rels.append({
                "source_name": nome,
                "source_uf": uf,
                "source_birth_date": birth_date,
                "source_municipality_id": municipality_id,
                "target_key": mid,
                "party": party,
                "affiliation_date": affiliation_date,
                "status": status,
            })

        self.memberships = deduplicate_rows(memberships, ["membership_id"])
        self.person_rels = person_rels

        logger.info(
            "[tse_filiados] Transformed %d PartyMembership nodes, %d person relationships",
            len(self.memberships),
            len(self.person_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.memberships:
            loaded = loader.load_nodes(
                "PartyMembership", self.memberships, key_field="membership_id",
            )
            logger.info("[tse_filiados] Loaded %d PartyMembership nodes", loaded)

        if not self.person_rels:
            return

        # Tiered matching: try narrower criteria first, then fall back.
        # All unmatched rows always get attempted at the lowest tier.
        # Note: Person nodes currently have name + uf (from TSE candidates).
        # birth_date and municipality_id are NOT yet on Person nodes, so
        # higher tiers will match 0 until those properties are populated.

        tier_high: list[dict[str, Any]] = []    # name + UF + birth_date
        tier_medium: list[dict[str, Any]] = []   # name + UF + municipality
        all_rels = self.person_rels  # ALL go through low tier as fallback

        for rel in self.person_rels:
            has_birth = bool(rel["source_birth_date"])
            has_muni = bool(rel["source_municipality_id"])
            if has_birth:
                tier_high.append(rel)
            elif has_muni:
                tier_medium.append(rel)

        logger.info(
            "[tse_filiados] Tiered: %d high, %d medium, %d total (all fall through to low)",
            len(tier_high), len(tier_medium), len(all_rels),
        )

        # Tier 1 (high): name + UF + birth_date
        if tier_high:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person) "
                "WHERE p.name = row.source_name AND p.uf = row.source_uf "
                "  AND p.birth_date = row.source_birth_date "
                "MATCH (m:PartyMembership {membership_id: row.target_key}) "
                "MERGE (p)-[r:FILIADO_A]->(m) "
                "SET r.party = row.party, "
                "    r.affiliation_date = row.affiliation_date, "
                "    r.status = row.status, "
                "    r.match_confidence = 'high'"
            )
            loaded = loader.run_query_with_retry(query, tier_high)
            logger.info("[tse_filiados] High-confidence FILIADO_A: %d", loaded)

        # Tier 2 (medium): name + UF + municipality
        if tier_medium:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person) "
                "WHERE p.name = row.source_name AND p.uf = row.source_uf "
                "  AND p.municipality_id = row.source_municipality_id "
                "MATCH (m:PartyMembership {membership_id: row.target_key}) "
                "WHERE NOT (p)-[:FILIADO_A]->(m) "
                "MERGE (p)-[r:FILIADO_A]->(m) "
                "SET r.party = row.party, "
                "    r.affiliation_date = row.affiliation_date, "
                "    r.status = row.status, "
                "    r.match_confidence = 'medium'"
            )
            loaded = loader.run_query_with_retry(query, tier_medium)
            logger.info("[tse_filiados] Medium-confidence FILIADO_A: %d", loaded)

        # Tier 3 (low): name + UF only — runs ALL rels as fallback
        # WHERE NOT (p)-[:FILIADO_A]->(m) skips rows already matched above
        query = (
            "UNWIND $rows AS row "
            "MATCH (p:Person) "
            "WHERE p.name = row.source_name AND p.uf = row.source_uf "
            "MATCH (m:PartyMembership {membership_id: row.target_key}) "
            "WHERE NOT (p)-[:FILIADO_A]->(m) "
            "MERGE (p)-[r:FILIADO_A]->(m) "
            "SET r.party = row.party, "
            "    r.affiliation_date = row.affiliation_date, "
            "    r.status = row.status, "
            "    r.match_confidence = 'low'"
        )
        loaded = loader.run_query_with_retry(query, all_rels)
        logger.info("[tse_filiados] Low-confidence FILIADO_A: %d", loaded)
