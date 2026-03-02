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
    format_cnpj,
    normalize_name,
    strip_document,
)

logger = logging.getLogger(__name__)


class BndesPipeline(Pipeline):
    """ETL pipeline for BNDES financing operations (non-automatic/direct)."""

    name = "bndes"
    source_id = "bndes"

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
        self.finances: list[dict[str, Any]] = []
        self.relationships: list[dict[str, Any]] = []

    def _parse_value(self, value: str) -> float:
        """Parse Brazilian numeric format (1.234.567,89) to float."""
        if not value or not value.strip():
            return 0.0
        cleaned = value.strip().replace(".", "").replace(",", ".")
        try:
            return float(cleaned)
        except ValueError:
            return 0.0

    def extract(self) -> None:
        bndes_dir = Path(self.data_dir) / "bndes"
        if not bndes_dir.exists():
            logger.warning("[%s] Data directory not found: %s", self.name, bndes_dir)
            return
        csv_path = bndes_dir / "operacoes-nao-automaticas.csv"
        if not csv_path.exists():
            logger.warning("[%s] CSV file not found: %s", self.name, csv_path)
            return
        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            delimiter=";",
            encoding="latin-1",
            keep_default_na=False,
        )
        logger.info("[bndes] Extracted %d rows from non-automatic operations", len(self._raw))

    def transform(self) -> None:
        finances: list[dict[str, Any]] = []
        relationships: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            cnpj_raw = str(row.get("cnpj", "")).strip()
            digits = strip_document(cnpj_raw)
            if len(digits) != 14:
                continue

            cnpj_formatted = format_cnpj(cnpj_raw)
            contrato = str(row.get("numero_do_contrato", "")).strip()
            if not contrato:
                continue

            finance_id = f"bndes_{contrato}"
            valor_contratado = self._parse_value(str(row.get("valor_contratado_reais", "")))
            valor_desembolsado = self._parse_value(str(row.get("valor_desembolsado_reais", "")))
            date = str(row.get("data_da_contratacao", "")).strip()
            description = str(row.get("descricao_do_projeto", "")).strip()
            cliente = normalize_name(str(row.get("cliente", "")))
            produto = str(row.get("produto", "")).strip()
            juros = str(row.get("juros", "")).strip()
            uf = str(row.get("uf", "")).strip()
            municipio = str(row.get("municipio", "")).strip()
            setor = str(row.get("setor_bndes", "")).strip()
            porte = str(row.get("porte_do_cliente", "")).strip()
            situacao = str(row.get("situacao_do_contrato", "")).strip()

            finances.append({
                "finance_id": finance_id,
                "type": "bndes_loan",
                "contract_number": contrato,
                "value": valor_desembolsado or valor_contratado,
                "value_contracted": valor_contratado,
                "value_disbursed": valor_desembolsado,
                "date": date,
                "description": description,
                "product": produto,
                "rate": juros,
                "uf": uf,
                "municipio": municipio,
                "sector": setor,
                "client_size": porte,
                "status": situacao,
                "source": "bndes",
            })

            relationships.append({
                "source_key": cnpj_formatted,
                "target_key": finance_id,
                "value_contracted": valor_contratado,
                "value_disbursed": valor_desembolsado,
                "rate": juros,
                "date": date,
                "client_name": cliente,
            })

        self.finances = deduplicate_rows(finances, ["finance_id"])
        self.relationships = relationships
        logger.info(
            "[bndes] Transformed %d Finance nodes, %d relationships",
            len(self.finances),
            len(self.relationships),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.finances:
            loaded = loader.load_nodes("Finance", self.finances, key_field="finance_id")
            logger.info("[bndes] Loaded %d Finance nodes", loaded)

        if self.relationships:
            query = (
                "UNWIND $rows AS row "
                "MERGE (c:Company {cnpj: row.source_key}) "
                "ON CREATE SET c.razao_social = row.client_name, c.name = row.client_name "
                "WITH c, row "
                "MATCH (f:Finance {finance_id: row.target_key}) "
                "MERGE (c)-[r:RECEBEU_EMPRESTIMO]->(f) "
                "SET r.value_contracted = row.value_contracted, "
                "    r.value_disbursed = row.value_disbursed, "
                "    r.rate = row.rate, "
                "    r.date = row.date"
            )
            loaded = loader.run_query_with_retry(query, self.relationships, batch_size=500)
            logger.info("[bndes] Loaded %d RECEBEU_EMPRESTIMO relationships", loaded)
