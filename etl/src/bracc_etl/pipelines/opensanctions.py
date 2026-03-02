from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

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

# Brazilian-related terms for filtering
BRAZIL_COUNTRY_CODES = {"br", "bra", "brazil", "brasil"}
BRAZIL_POSITION_TERMS = {
    "brasil", "brazil", "brasileiro", "brasileira",
    "deputado", "senador", "governador", "prefeito", "vereador",
    "ministro", "secretario", "presidente da republica",
}

# Confidence threshold for CPF-based matching (name matching in link_global_peps.cypher)
EXACT_CPF_MATCH = 1.0


def _is_brazilian_entity(entity: dict[str, Any]) -> bool:
    """Check if a FtM entity has Brazilian connections."""
    props = entity.get("properties", {})

    # Check country field
    countries = props.get("country", [])
    for c in countries:
        if c.lower() in BRAZIL_COUNTRY_CODES:
            return True

    # Check nationality
    nationalities = props.get("nationality", [])
    for n in nationalities:
        if n.lower() in BRAZIL_COUNTRY_CODES:
            return True

    # Check position for Brazilian government roles
    positions = props.get("position", [])
    for pos in positions:
        pos_lower = pos.lower()
        for term in BRAZIL_POSITION_TERMS:
            if term in pos_lower:
                return True

    return False


def _extract_cpf(entity: dict[str, Any]) -> str | None:
    """Extract CPF from FtM taxNumber property."""
    props = entity.get("properties", {})
    tax_numbers = props.get("taxNumber", [])
    for tn in tax_numbers:
        digits = strip_document(tn)
        if len(digits) == 11:
            return format_cpf(digits)
    return None


class OpenSanctionsPipeline(Pipeline):
    """ETL pipeline for OpenSanctions PEP data (FollowTheMoney format)."""

    name = "opensanctions"
    source_id = "opensanctions"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_entities: list[dict[str, Any]] = []
        self.global_peps: list[dict[str, Any]] = []
        self.pep_match_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        data_dir = Path(self.data_dir) / "opensanctions"
        ftm_path = data_dir / "entities.ftm.json"

        if not ftm_path.exists():
            logger.warning("[opensanctions] entities.ftm.json not found at %s", ftm_path)
            return

        entities: list[dict[str, Any]] = []
        with open(ftm_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entity = json.loads(line)
                    entities.append(entity)
                except json.JSONDecodeError:
                    continue

        self._raw_entities = entities
        logger.info("[opensanctions] Extracted %d raw entities", len(self._raw_entities))

    def _transform_peps(self) -> list[dict[str, Any]]:
        """Filter and transform Brazilian-connected PEP entities."""
        peps: list[dict[str, Any]] = []

        for entity in self._raw_entities:
            schema = entity.get("schema", "")
            if schema != "Person":
                continue

            if not _is_brazilian_entity(entity):
                continue

            entity_id = entity.get("id", "").strip()
            if not entity_id:
                continue

            props = entity.get("properties", {})
            names = props.get("name", [])
            if not names:
                continue

            primary_name = names[0]
            countries = props.get("country", [])
            positions = props.get("position", [])
            start_dates = props.get("startDate", [])
            end_dates = props.get("endDate", [])
            datasets = entity.get("datasets", [])

            cpf = _extract_cpf(entity)

            peps.append({
                "pep_id": f"os_{entity_id}",
                "name": normalize_name(primary_name),
                "original_name": primary_name,
                "country": countries[0] if countries else "",
                "position": positions[0] if positions else "",
                "all_positions": "; ".join(positions) if positions else "",
                "start_date": start_dates[0] if start_dates else "",
                "end_date": end_dates[0] if end_dates else "",
                "datasets": "; ".join(datasets) if datasets else "",
                "cpf": cpf or "",
                "source": "opensanctions",
            })

        return peps

    def _build_cpf_match_rels(self) -> list[dict[str, Any]]:
        """Build GLOBAL_PEP_MATCH relationships based on CPF."""
        rels: list[dict[str, Any]] = []
        for pep in self.global_peps:
            cpf = pep.get("cpf", "")
            if not cpf:
                continue
            rels.append({
                "source_key": cpf,
                "target_key": pep["pep_id"],
                "match_type": "cpf_exact",
                "confidence": EXACT_CPF_MATCH,
            })
        return rels

    def transform(self) -> None:
        self.global_peps = deduplicate_rows(self._transform_peps(), ["pep_id"])
        self.pep_match_rels = self._build_cpf_match_rels()

        logger.info(
            "[opensanctions] Transformed %d GlobalPEP nodes, %d CPF match relationships",
            len(self.global_peps),
            len(self.pep_match_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.global_peps:
            loaded = loader.load_nodes("GlobalPEP", self.global_peps, key_field="pep_id")
            logger.info("[opensanctions] Loaded %d GlobalPEP nodes", loaded)

        if self.pep_match_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (g:GlobalPEP {pep_id: row.target_key}) "
                "MERGE (p)-[r:GLOBAL_PEP_MATCH]->(g) "
                "SET r.match_type = row.match_type, "
                "    r.confidence = row.confidence"
            )
            loaded = loader.run_query_with_retry(query, self.pep_match_rels)
            logger.info("[opensanctions] Loaded %d GLOBAL_PEP_MATCH relationships", loaded)
