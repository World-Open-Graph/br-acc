from __future__ import annotations

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
    parse_date,
    strip_document,
)


class CeafPipeline(Pipeline):
    """ETL pipeline for CEAF (Cadastro de Expulsoes da Administracao Federal)."""

    name = "ceaf"
    source_id = "ceaf"

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
        self.expulsions: list[dict[str, Any]] = []
        self.person_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        ceaf_dir = Path(self.data_dir) / "ceaf"
        self._raw = pd.read_csv(
            ceaf_dir / "ceaf.csv",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )

    def transform(self) -> None:
        expulsions: list[dict[str, Any]] = []
        person_rels: list[dict[str, Any]] = []

        for idx, row in self._raw.iterrows():
            cpf_raw = str(row.get("cpf", ""))
            digits = strip_document(cpf_raw)

            nome = normalize_name(str(row.get("nome", "")))
            if not nome:
                continue

            position = str(row.get("cargo_efetivo", "")).strip()
            punishment_type = str(row.get("tipo_punicao", "")).strip()
            date = parse_date(str(row.get("data_publicacao", "")))
            decree = str(row.get("portaria", "")).strip()
            uf = str(row.get("uf", "")).strip()

            # Use full CPF when available, otherwise use partial + index
            if len(digits) == 11:
                cpf_formatted = format_cpf(cpf_raw)
                expulsion_id = f"ceaf_{digits}_{idx}"
            else:
                cpf_formatted = cpf_raw.strip()  # Keep masked format
                expulsion_id = f"ceaf_{digits}_{idx}"

            expulsions.append({
                "expulsion_id": expulsion_id,
                "cpf": cpf_formatted,
                "name": nome,
                "position": position,
                "punishment_type": punishment_type,
                "date": date,
                "decree": decree,
                "uf": uf,
                "source": "ceaf",
            })

            # Only create person relationships for full CPFs
            if len(digits) == 11:
                person_rels.append({
                    "source_key": cpf_formatted,
                    "target_key": expulsion_id,
                    "person_name": nome,
                })

        self.expulsions = deduplicate_rows(expulsions, ["expulsion_id"])
        self.person_rels = person_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.expulsions:
            loader.load_nodes("Expulsion", self.expulsions, key_field="expulsion_id")

        # Ensure Person nodes exist
        for rel in self.person_rels:
            loader.load_nodes(
                "Person",
                [{"cpf": rel["source_key"], "name": rel["person_name"]}],
                key_field="cpf",
            )

        if self.person_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (e:Expulsion {expulsion_id: row.target_key}) "
                "MERGE (p)-[:EXPULSO]->(e)"
            )
            loader.run_query_with_retry(query, self.person_rels)
