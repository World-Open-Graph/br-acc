from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
import contextlib

from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import deduplicate_rows, normalize_name

logger = logging.getLogger(__name__)

class TesouroEmendasPipeline(Pipeline):
    """ETL pipeline for Tesouro Emendas."""

    name = "tesouro_emendas"
    source_id = "tesouro_emendas"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw = pd.DataFrame()
        self.transfers: list[dict[str, Any]] = []
        self.companies: list[dict[str, Any]] = []
        self.transfer_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "tesouro_emendas"
        csv_path = src_dir / "emendas_tesouro.csv"
        if not csv_path.exists():
            msg = f"Tesouro Emendas CSV not found: {csv_path}"
            raise FileNotFoundError(msg)

        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            encoding="latin-1",
            sep=";",
            keep_default_na=False,
        )
        logger.info("[tesouro_emendas] Extracted %d transfer records", len(self._raw))

    def transform(self) -> None:
        transfers: list[dict[str, Any]] = []
        companies: list[dict[str, Any]] = []
        transfer_rels: list[dict[str, Any]] = []

        for _idx, row in self._raw.iterrows():
            ob = str(row.get("OB", "")).strip()
            if not ob:
                continue

            # In excel, 42005 represents 2015-01-01. Convert to typical iso format if possible
            date_val = str(row.get("Data", "")).strip()
            formatted_date = date_val
            if date_val.isdigit():
                with contextlib.suppress(Exception):
                    dt = pd.to_datetime(int(date_val), unit='D', origin='1899-12-30')
                    formatted_date = dt.strftime('%Y-%m-%d')

            ano = str(row.get("Ano", "")).strip()
            mes = str(row.get("Mês", "")).strip()
            emenda_tipo = str(row.get("Nome Emenda", "")).strip()
            especial = str(row.get("Transferência Especial", "")).strip()
            categoria = str(row.get("Categoria Econômica Despesa", "")).strip()
            valor_raw = str(row.get("Valor", "")).strip()
            try:
                valor = float(valor_raw.replace(',', '.'))
            except ValueError:
                valor = 0.0

            transfer_id = f"transfer_tesouro_{ob}"

            transfers.append({
                "transfer_id": transfer_id,
                "ob": ob,
                "date": formatted_date,
                "year": ano,
                "month": mes,
                "amendment_type": emenda_tipo,
                "special_transfer": especial,
                "economic_category": categoria,
                "value": valor,
                "source": self.source_id,
            })

            cnpj_raw = str(row.get("CNPJ do Favorecido", "")).strip()
            nome_fav = normalize_name(str(row.get("Nome Favorecido", "")))

            # Format CNPJ to 14 digits with zeros if needed
            cnpj = cnpj_raw.zfill(14) if cnpj_raw else ""
            if len(cnpj) == 14:
                companies.append({
                    "cnpj": cnpj,
                    "razao_social": nome_fav,
                })
                transfer_rels.append({
                    "source_key": transfer_id,
                    "target_key": cnpj,
                })

            if self.limit and len(transfers) >= self.limit:
                break

        self.transfers = deduplicate_rows(transfers, ["transfer_id"])
        self.companies = deduplicate_rows(companies, ["cnpj"])
        self.transfer_rels = transfer_rels

        logger.info(
            "[tesouro_emendas] Transformed %d transfers, %d companies",
            len(self.transfers),
            len(self.companies),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.transfers:
            loader.load_nodes("Payment", self.transfers, key_field="transfer_id")

        if self.companies:
            loader.load_nodes("Company", self.companies, key_field="cnpj")

        if self.transfer_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Payment {transfer_id: row.source_key}) "
                "MATCH (c:Company {cnpj: row.target_key}) "
                "MERGE (p)-[:PAGO_PARA]->(c)"
            )
            loader.run_query(query, self.transfer_rels)
