from __future__ import annotations

import hashlib
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    normalize_name,
    strip_document,
)


def _generate_ngo_id(cnpj_digits: str, agreement_number: str) -> str:
    """Deterministic ID from CNPJ digits + agreement number."""
    raw = f"{cnpj_digits}:{agreement_number}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class CepimPipeline(Pipeline):
    """ETL pipeline for CEPIM (Cadastro de Entidades Privadas sem Fins Lucrativos Impedidas)."""

    name = "cepim"
    source_id = "cepim"

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
        self.ngos: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        cepim_dir = Path(self.data_dir) / "cepim"
        self._raw = pd.read_csv(
            cepim_dir / "cepim.csv",
            sep=";",
            dtype=str,
            encoding="latin-1",
            keep_default_na=False,
        )

    def transform(self) -> None:
        ngos: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            cnpj_raw = str(row.get("CNPJ ENTIDADE", ""))
            digits = strip_document(cnpj_raw)

            if len(digits) != 14:
                continue

            cnpj_formatted = format_cnpj(cnpj_raw)
            name = normalize_name(str(row.get("NOME ENTIDADE", "")))
            agreement_number = str(row.get("NÚMERO CONVÊNIO", "")).strip()
            agency = str(row.get("ÓRGÃO CONCEDENTE", "")).strip()
            reason = str(
                row.get("MOTIVO IMPEDIMENTO", row.get("MOTIVO DO IMPEDIMENTO", ""))
            ).strip()

            ngo_id = _generate_ngo_id(digits, agreement_number)

            ngos.append({
                "ngo_id": ngo_id,
                "cnpj": cnpj_formatted,
                "name": name,
                "reason": reason,
                "agreement_number": agreement_number,
                "agency": agency,
                "source": "cepim",
            })

            company_rels.append({
                "source_key": cnpj_formatted,
                "target_key": ngo_id,
            })

        self.ngos = deduplicate_rows(ngos, ["ngo_id"])
        self.company_rels = company_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.ngos:
            loader.load_nodes("BarredNGO", self.ngos, key_field="ngo_id")

        # Ensure Company nodes exist for CNPJ linking
        if self.company_rels:
            companies = [
                {"cnpj": rel["source_key"]} for rel in self.company_rels
            ]
            loader.load_nodes("Company", deduplicate_rows(companies, ["cnpj"]), key_field="cnpj")

        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (b:BarredNGO {ngo_id: row.target_key}) "
                "MERGE (c)-[:IMPEDIDA]->(b)"
            )
            loader.run_query_with_retry(query, self.company_rels)
