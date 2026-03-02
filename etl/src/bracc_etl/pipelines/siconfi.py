from __future__ import annotations

import hashlib
import json
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
    format_cnpj,
    normalize_name,
    strip_document,
)

logger = logging.getLogger(__name__)


class SiconfiPipeline(Pipeline):
    """ETL pipeline for SICONFI (municipal/state finance declarations).

    Data source: Tesouro Nacional API (apidatalake.tesouro.gov.br).
    Loads MunicipalFinance nodes linked to municipalities (Company nodes by CNPJ).
    """

    name = "siconfi"
    source_id = "siconfi"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw: list[dict[str, Any]] = []
        self.finances: list[dict[str, Any]] = []
        self.municipality_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        siconfi_dir = Path(self.data_dir) / "siconfi"
        all_records: list[dict[str, Any]] = []

        # Read CSV files produced by download_siconfi.py
        csv_files = sorted(siconfi_dir.glob("dca_*.csv"))
        for csv_file in csv_files:
            df = pd.read_csv(csv_file, dtype=str, keep_default_na=False)
            all_records.extend(df.to_dict("records"))  # type: ignore[arg-type]
            logger.info("  Loaded %d records from %s", len(df), csv_file.name)

        # Fallback: also try JSON if present (original API format)
        for json_file in sorted(siconfi_dir.glob("*.json")):
            with open(json_file, encoding="utf-8") as f:
                data = json.load(f)
                items = data if isinstance(data, list) else data.get("items", [])
                all_records.extend(items)

        if self.limit:
            all_records = all_records[: self.limit]

        self._raw = all_records
        logger.info("Extracted %d SICONFI records", len(self._raw))

    def transform(self) -> None:
        finances: list[dict[str, Any]] = []
        municipality_rels: list[dict[str, Any]] = []

        for row in self._raw:
            cod_ibge = str(row.get("cod_ibge", "")).strip()
            if not cod_ibge:
                continue

            # CSV uses "instituicao", API JSON uses "ente"
            ente = normalize_name(
                str(row.get("instituicao", "") or row.get("ente", ""))
            )
            exercicio = str(row.get("exercicio", "")).strip()
            conta = str(row.get("conta", "")).strip()
            coluna = str(row.get("coluna", "")).strip()
            valor = row.get("valor")

            if valor is None or valor == "":
                continue

            try:
                amount = float(str(valor).replace(",", "."))
            except (ValueError, TypeError):
                continue

            # CNPJ may be in API JSON but not in CSV downloads
            cnpj_raw = str(row.get("cnpj", "")).strip()
            cnpj_digits = strip_document(cnpj_raw)
            cnpj_formatted = format_cnpj(cnpj_raw) if len(cnpj_digits) == 14 else ""

            id_source = f"{cod_ibge}_{exercicio}_{conta}_{coluna}"
            finance_id = hashlib.sha256(id_source.encode()).hexdigest()[:16]

            finances.append({
                "finance_id": finance_id,
                "cod_ibge": cod_ibge,
                "municipality": ente,
                "year": exercicio,
                "account": conta,
                "column": coluna,
                "amount": amount,
                "source": "siconfi",
            })

            if cnpj_formatted:
                municipality_rels.append({
                    "cnpj": cnpj_formatted,
                    "finance_id": finance_id,
                    "municipality": ente,
                })

        self.finances = deduplicate_rows(finances, ["finance_id"])
        self.municipality_rels = municipality_rels
        logger.info(
            "Transformed %d finance records, %d municipality links",
            len(self.finances),
            len(self.municipality_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.finances:
            loader.load_nodes("MunicipalFinance", self.finances, key_field="finance_id")

        if self.municipality_rels:
            # Ensure Company nodes exist for municipalities
            muni_nodes = deduplicate_rows(
                [
                    {"cnpj": r["cnpj"], "razao_social": r["municipality"]}
                    for r in self.municipality_rels
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", muni_nodes, key_field="cnpj")

            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.cnpj}) "
                "MATCH (f:MunicipalFinance {finance_id: row.finance_id}) "
                "MERGE (c)-[:DECLAROU_FINANCA]->(f)"
            )
            loader.run_query_with_retry(query, self.municipality_rels)
