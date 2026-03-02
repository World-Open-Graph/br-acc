from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    cap_contract_value,
    deduplicate_rows,
    format_cnpj,
    normalize_name,
    parse_date,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)


def _stable_id(*parts: str, length: int = 24) -> str:
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:length]


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    text = re.sub(r"[^0-9,.-]", "", text)
    if "," in text and "." in text and text.rfind(",") > text.rfind("."):
        text = text.replace(".", "").replace(",", ".")
    elif "," in text and "." not in text:
        text = text.replace(",", ".")
    try:
        return float(text)
    except ValueError:
        return None


def _pick(row: pd.Series, *keys: str) -> str:
    for key in keys:
        value = str(row.get(key, "")).strip()
        if value:
            return value
    return ""


def _valid_cnpj(value: str) -> str:
    digits = strip_document(value)
    if len(digits) != 14:
        return ""
    return format_cnpj(digits)


class MidesPipeline(Pipeline):
    """ETL pipeline for municipal procurement data (MiDES / Base dos Dados)."""

    name = "mides"
    source_id = "mides"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)

        self._raw_bids: pd.DataFrame = pd.DataFrame()
        self._raw_contracts: pd.DataFrame = pd.DataFrame()
        self._raw_items: pd.DataFrame = pd.DataFrame()

        self.bids: list[dict[str, Any]] = []
        self.contracts: list[dict[str, Any]] = []
        self.items: list[dict[str, Any]] = []
        self.bid_company_rels: list[dict[str, Any]] = []
        self.contract_company_rels: list[dict[str, Any]] = []
        self.contract_bid_rels: list[dict[str, Any]] = []
        self.contract_item_rels: list[dict[str, Any]] = []

    def _read_df_optional(self, path: Path) -> pd.DataFrame:
        if not path.exists():
            return pd.DataFrame()
        if path.suffix == ".parquet":
            return pd.read_parquet(path)
        return pd.read_csv(path, dtype=str, keep_default_na=False)

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "mides"
        self._raw_bids = self._read_df_optional(src_dir / "licitacao.csv")
        if self._raw_bids.empty:
            self._raw_bids = self._read_df_optional(src_dir / "licitacao.parquet")

        self._raw_contracts = self._read_df_optional(src_dir / "contrato.csv")
        if self._raw_contracts.empty:
            self._raw_contracts = self._read_df_optional(src_dir / "contrato.parquet")

        self._raw_items = self._read_df_optional(src_dir / "item.csv")
        if self._raw_items.empty:
            self._raw_items = self._read_df_optional(src_dir / "item.parquet")

        if self._raw_bids.empty and self._raw_contracts.empty and self._raw_items.empty:
            logger.warning("[mides] no input files found in %s", src_dir)
            return

        if self.limit:
            self._raw_bids = self._raw_bids.head(self.limit)
            self._raw_contracts = self._raw_contracts.head(self.limit)
            self._raw_items = self._raw_items.head(self.limit)

        logger.info(
            "[mides] extracted bids=%d contracts=%d items=%d",
            len(self._raw_bids),
            len(self._raw_contracts),
            len(self._raw_items),
        )

    def transform(self) -> None:
        self._transform_bids()
        self._transform_contracts()
        self._transform_items()

    def _transform_bids(self) -> None:
        if self._raw_bids.empty:
            return

        bids: list[dict[str, Any]] = []
        bid_company_rels: list[dict[str, Any]] = []

        for _, row in self._raw_bids.iterrows():
            bid_id = _pick(row, "municipal_bid_id", "licitacao_id", "id_licitacao", "id")
            process_number = _pick(row, "process_number", "numero_processo", "numero")
            org_code = _pick(row, "municipality_code", "cod_ibge", "codigo_ibge")
            org_name = _pick(row, "municipality_name", "municipio", "nome_municipio")
            uf = _pick(row, "uf", "estado")
            modality = _pick(row, "modality", "modalidade")
            obj = normalize_name(_pick(row, "object", "objeto", "descricao"))
            pub_date = parse_date(_pick(row, "published_at", "data_publicacao", "data"))
            year = _pick(row, "year", "ano")
            amount_estimated = cap_contract_value(
                _to_float(_pick(row, "amount_estimated", "valor_estimado", "valor")),
            )
            source_url = _pick(row, "source_url", "url")

            if not bid_id:
                bid_id = _stable_id(process_number, org_code, obj[:180], pub_date)

            bids.append({
                "municipal_bid_id": bid_id,
                "process_number": process_number,
                "municipality_code": org_code,
                "municipality_name": org_name,
                "uf": uf,
                "modality": modality,
                "object": obj,
                "published_at": pub_date,
                "year": year,
                "amount_estimated": amount_estimated,
                "source_url": source_url,
                "source": "mides",
            })

            supplier_cnpj = _valid_cnpj(_pick(
                row,
                "supplier_cnpj",
                "winner_cnpj",
                "cnpj_fornecedor",
                "cnpj_vencedor",
            ))
            if supplier_cnpj:
                bid_company_rels.append({
                    "cnpj": supplier_cnpj,
                    "target_key": bid_id,
                })

        self.bids = deduplicate_rows(bids, ["municipal_bid_id"])
        self.bid_company_rels = deduplicate_rows(bid_company_rels, ["cnpj", "target_key"])

    def _transform_contracts(self) -> None:
        if self._raw_contracts.empty:
            return

        contracts: list[dict[str, Any]] = []
        contract_company_rels: list[dict[str, Any]] = []
        contract_bid_rels: list[dict[str, Any]] = []

        for _, row in self._raw_contracts.iterrows():
            contract_id = _pick(row, "municipal_contract_id", "contrato_id", "id_contrato", "id")
            number = _pick(row, "contract_number", "numero_contrato", "numero")
            bid_ref = _pick(row, "municipal_bid_id", "licitacao_id", "id_licitacao")
            process_number = _pick(row, "process_number", "numero_processo")
            municipality_code = _pick(row, "municipality_code", "cod_ibge", "codigo_ibge")
            municipality_name = _pick(row, "municipality_name", "municipio", "nome_municipio")
            uf = _pick(row, "uf", "estado")
            signed_at = parse_date(_pick(row, "signed_at", "data_assinatura", "data"))
            obj = normalize_name(_pick(row, "object", "objeto", "descricao"))
            amount = cap_contract_value(_to_float(_pick(row, "amount", "valor", "valor_contrato")))
            source_url = _pick(row, "source_url", "url")

            if not contract_id:
                contract_id = _stable_id(number, municipality_code, obj[:160], signed_at)

            contracts.append({
                "municipal_contract_id": contract_id,
                "contract_number": number,
                "process_number": process_number,
                "municipality_code": municipality_code,
                "municipality_name": municipality_name,
                "uf": uf,
                "signed_at": signed_at,
                "object": obj,
                "amount": amount,
                "source_url": source_url,
                "source": "mides",
            })

            supplier_cnpj = _valid_cnpj(
                _pick(row, "supplier_cnpj", "cnpj_fornecedor", "cnpj_vencedor"),
            )
            if supplier_cnpj:
                contract_company_rels.append({
                    "cnpj": supplier_cnpj,
                    "target_key": contract_id,
                })

            if bid_ref:
                contract_bid_rels.append({
                    "source_key": contract_id,
                    "target_key": bid_ref,
                })

        self.contracts = deduplicate_rows(contracts, ["municipal_contract_id"])
        self.contract_company_rels = deduplicate_rows(contract_company_rels, ["cnpj", "target_key"])
        self.contract_bid_rels = deduplicate_rows(contract_bid_rels, ["source_key", "target_key"])

    def _transform_items(self) -> None:
        if self._raw_items.empty:
            return

        items: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []

        for _, row in self._raw_items.iterrows():
            contract_id = _pick(row, "municipal_contract_id", "contrato_id", "id_contrato")
            bid_id = _pick(row, "municipal_bid_id", "licitacao_id", "id_licitacao")

            item_id = _pick(row, "municipal_item_id", "item_id", "id_item")
            item_number = _pick(row, "item_number", "numero_item")
            description = normalize_name(_pick(row, "description", "descricao", "objeto_item"))
            quantity = _to_float(_pick(row, "quantity", "quantidade"))
            unit_price = cap_contract_value(_to_float(_pick(row, "unit_price", "valor_unitario")))
            total_price = cap_contract_value(
                _to_float(_pick(row, "total_price", "valor_total", "valor")),
            )

            if not item_id:
                item_id = _stable_id(contract_id, bid_id, item_number, description[:120])

            items.append({
                "municipal_item_id": item_id,
                "item_number": item_number,
                "description": description,
                "quantity": quantity,
                "unit_price": unit_price,
                "total_price": total_price,
                "source": "mides",
            })

            if contract_id:
                rels.append({"source_key": contract_id, "target_key": item_id})

        self.items = deduplicate_rows(items, ["municipal_item_id"])
        self.contract_item_rels = deduplicate_rows(rels, ["source_key", "target_key"])

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.bids:
            loader.load_nodes("MunicipalBid", self.bids, key_field="municipal_bid_id")

        if self.contracts:
            loader.load_nodes(
                "MunicipalContract",
                self.contracts,
                key_field="municipal_contract_id",
            )

        if self.items:
            loader.load_nodes("MunicipalBidItem", self.items, key_field="municipal_item_id")

        if self.bid_company_rels:
            companies = deduplicate_rows(
                [
                    {
                        "cnpj": row["cnpj"],
                        "razao_social": row["cnpj"],
                    }
                    for row in self.bid_company_rels
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", companies, key_field="cnpj")

            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.cnpj}) "
                "MATCH (b:MunicipalBid {municipal_bid_id: row.target_key}) "
                "MERGE (c)-[:MUNICIPAL_LICITOU]->(b)"
            )
            loader.run_query_with_retry(query, self.bid_company_rels)

        if self.contract_company_rels:
            companies = deduplicate_rows(
                [
                    {
                        "cnpj": row["cnpj"],
                        "razao_social": row["cnpj"],
                    }
                    for row in self.contract_company_rels
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", companies, key_field="cnpj")

            query = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.cnpj}) "
                "MATCH (mc:MunicipalContract {municipal_contract_id: row.target_key}) "
                "MERGE (c)-[:MUNICIPAL_VENCEU]->(mc)"
            )
            loader.run_query_with_retry(query, self.contract_company_rels)

        if self.contract_bid_rels:
            loader.load_relationships(
                rel_type="REFERENTE_A",
                rows=self.contract_bid_rels,
                source_label="MunicipalContract",
                source_key="municipal_contract_id",
                target_label="MunicipalBid",
                target_key="municipal_bid_id",
            )

        if self.contract_item_rels:
            loader.load_relationships(
                rel_type="TEM_ITEM",
                rows=self.contract_item_rels,
                source_label="MunicipalContract",
                source_key="municipal_contract_id",
                target_label="MunicipalBidItem",
                target_key="municipal_item_id",
            )
