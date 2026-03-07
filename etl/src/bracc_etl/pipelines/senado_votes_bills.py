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


def _generate_vote_id(
    session_id: str, senator_id: str,
) -> str:
    """Deterministic ID from session + senator."""
    raw = f"senado_vote:{session_id}:{senator_id}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _generate_bill_id(
    bill_type: str, bill_number: str, year: str,
) -> str:
    """Deterministic ID from type + number + year."""
    raw = f"senado_bill:{bill_type}:{bill_number}:{year}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SenadoVotesBillsPipeline(Pipeline):
    """ETL pipeline for Senado Federal votes and bills.

    Data source: legis.senado.leg.br/dadosabertos — CSV exports
    of senator votes on propositions and bill metadata.
    """

    name = "senado_votes_bills"
    source_id = "senado_votes_bills"

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
        self._votes_raw: pd.DataFrame = pd.DataFrame()
        self._bills_raw: pd.DataFrame = pd.DataFrame()
        self.bills: list[dict[str, Any]] = []
        self.votes: list[dict[str, Any]] = []
        self.vote_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "senado_votes_bills"

        votes_path = src_dir / "votacoes.csv"
        if votes_path.exists():
            self._votes_raw = pd.read_csv(
                votes_path, sep=";", dtype=str,
                keep_default_na=False,
            )
        else:
            logger.warning("[senado_votes] votes CSV not found")

        bills_path = src_dir / "materias.csv"
        if bills_path.exists():
            self._bills_raw = pd.read_csv(
                bills_path, sep=";", dtype=str,
                keep_default_na=False,
            )
        else:
            logger.warning("[senado_votes] bills CSV not found")

        total = len(self._votes_raw) + len(self._bills_raw)
        logger.info(
            "[senado_votes] Extracted %d total records", total,
        )

    def transform(self) -> None:
        bills: list[dict[str, Any]] = []
        votes: list[dict[str, Any]] = []
        vote_rels: list[dict[str, Any]] = []

        # Transform bills
        for row in self._bills_raw.itertuples(index=False):
            bill_type = str(
                getattr(row, "SiglaTipo", "")
            ).strip()
            bill_number = str(
                getattr(row, "NumeroMateria", "")
            ).strip()
            year = str(
                getattr(row, "AnoMateria", "")
            ).strip()

            if not bill_type or not bill_number:
                continue

            bill_id = _generate_bill_id(
                bill_type, bill_number, year,
            )
            subject = str(
                getattr(row, "EmentaMateria", "")
            ).strip()[:500]
            author = normalize_name(
                str(getattr(row, "NomeAutor", ""))
            )

            bills.append({
                "bill_id": bill_id,
                "bill_type": bill_type,
                "bill_number": bill_number,
                "year": year,
                "subject": subject,
                "author": author,
                "chamber": "Senado",
                "source": self.source_id,
            })

        # Transform votes
        for row in self._votes_raw.itertuples(index=False):
            session_id = str(
                getattr(row, "CodigoSessaoVotacao", "")
            ).strip()
            senator_id = str(
                getattr(row, "CodigoParlamentar", "")
            ).strip()
            senator_name = normalize_name(
                str(getattr(row, "NomeParlamentar", ""))
            )
            party = str(
                getattr(row, "SiglaPartido", "")
            ).strip()
            vote_value = str(
                getattr(row, "DescricaoVoto", "")
            ).strip()
            vote_date = str(
                getattr(row, "DataSessao", "")
            ).strip()

            if not session_id or not senator_id:
                continue

            vote_id = _generate_vote_id(
                session_id, senator_id,
            )
            votes.append({
                "vote_id": vote_id,
                "session_id": session_id,
                "senator_id": senator_id,
                "senator_name": senator_name,
                "party": party,
                "vote_value": vote_value,
                "vote_date": vote_date,
                "source": self.source_id,
            })

            if senator_name:
                vote_rels.append({
                    "source_key": senator_name,
                    "target_key": vote_id,
                })

            if self.limit and len(votes) >= self.limit:
                break

        self.bills = deduplicate_rows(bills, ["bill_id"])
        self.votes = deduplicate_rows(votes, ["vote_id"])
        self.vote_rels = vote_rels
        logger.info(
            "[senado_votes] Transformed %d bills, %d votes",
            len(self.bills), len(self.votes),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.bills:
            loader.load_nodes(
                "Bill", self.bills, key_field="bill_id",
            )

        if self.votes:
            loader.load_nodes(
                "SenateVote", self.votes,
                key_field="vote_id",
            )

        if self.vote_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (p:Person {name: row.source_key}) "
                "WITH p, row "
                "MATCH (v:SenateVote "
                "{vote_id: row.target_key}) "
                "MERGE (p)-[:VOTOU]->(v)"
            )
            loader.run_query_with_retry(
                query, self.vote_rels,
            )
