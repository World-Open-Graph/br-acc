"""ETL pipeline for CVM (Comissao de Valores Mobiliarios) sanctions data.

Ingests PAS (Processo Administrativo Sancionador) results from CVM open data.
Creates CVMProceeding nodes linked to Company/Person nodes via CVM_SANCIONADA.
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
    normalize_name,
    parse_date,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)


class CvmPipeline(Pipeline):
    """ETL pipeline for CVM PAS sanctions data."""

    name = "cvm"
    source_id = "cvm"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_processos: pd.DataFrame = pd.DataFrame()
        self._raw_acusados: pd.DataFrame = pd.DataFrame()
        self.proceedings: list[dict[str, Any]] = []
        self.accused_entities: list[dict[str, Any]] = []

    def extract(self) -> None:
        cvm_dir = Path(self.data_dir) / "cvm"

        # New CVM format (processo_sancionador.zip contents)
        proc_path = cvm_dir / "processo_sancionador.csv"
        acusado_path = cvm_dir / "processo_sancionador_acusado.csv"

        if not proc_path.exists():
            msg = f"CVM proceedings file not found: {proc_path}"
            raise FileNotFoundError(msg)

        self._raw_processos = pd.read_csv(
            proc_path,
            sep=";",
            dtype=str,
            keep_default_na=False,
            encoding="latin-1",
        )
        if acusado_path.exists():
            self._raw_acusados = pd.read_csv(
                acusado_path,
                sep=";",
                dtype=str,
                keep_default_na=False,
                encoding="latin-1",
            )

    def transform(self) -> None:
        # Build accused lookup by NUP
        accused_by_nup: dict[str, list[dict[str, str]]] = {}
        if not self._raw_acusados.empty:
            for _, row in self._raw_acusados.iterrows():
                nup = str(row.get("NUP", "")).strip()
                if not nup:
                    continue
                nome = normalize_name(str(row.get("Nome_Acusado", "")))
                situacao = str(row.get("Situacao", "")).strip()
                data_sit = parse_date(str(row.get("Data_Situacao", "")))
                accused_by_nup.setdefault(nup, []).append({
                    "name": nome,
                    "status": situacao,
                    "date": data_sit,
                })

        proceedings: list[dict[str, Any]] = []
        entities: list[dict[str, Any]] = []

        for _, row in self._raw_processos.iterrows():
            nup = str(row.get("NUP", "")).strip()
            if not nup:
                continue

            date = parse_date(str(row.get("Data_Abertura", "")))
            fase = str(row.get("Fase_Atual", "")).strip()
            objeto = str(row.get("Objeto", "")).strip()
            ementa = str(row.get("Ementa", "")).strip()

            proceedings.append({
                "pas_id": nup,
                "date": date,
                "penalty_type": "",
                "penalty_value": 0.0,
                "status": fase,
                "description": ementa or objeto,
                "numero_processo": nup,
                "relator": "",
                "data_instauracao": date,
                "source": "cvm",
            })

            # Link accused persons (name-based, no CPF/CNPJ in new format)
            for accused in accused_by_nup.get(nup, []):
                entities.append({
                    "target_key": nup,
                    "entity_name": accused["name"],
                    "accused_status": accused["status"],
                    "accused_date": accused["date"],
                })

        self.proceedings = deduplicate_rows(proceedings, ["pas_id"])
        self.accused_entities = entities

        if self.limit:
            self.proceedings = self.proceedings[: self.limit]
            self.accused_entities = self.accused_entities[: self.limit]

        logger.info(
            "Transformed: %d proceedings, %d accused entities",
            len(self.proceedings),
            len(self.accused_entities),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.proceedings:
            loader.load_nodes("CVMProceeding", self.proceedings, key_field="pas_id")

        # Name-based matching: find existing Person/Company by name
        if self.accused_entities:
            rel_rows = [
                {
                    "target_key": e["target_key"],
                    "entity_name": e["entity_name"],
                }
                for e in self.accused_entities
                if e["entity_name"]
            ]

            query = (
                "UNWIND $rows AS row "
                "MATCH (p:CVMProceeding {pas_id: row.target_key}) "
                "OPTIONAL MATCH (pe:Person) WHERE pe.name = row.entity_name "
                "OPTIONAL MATCH (c:Company) WHERE c.razao_social = row.entity_name "
                "WITH p, coalesce(pe, c) AS entity "
                "WHERE entity IS NOT NULL "
                "MERGE (entity)-[:CVM_SANCIONADA]->(p)"
            )
            loader.run_query(query, rel_rows)
