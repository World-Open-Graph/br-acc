"""ETL pipeline for Senado Federal CEAPS expense data.

Ingests CEAPS (Cota para o Exercicio da Atividade Parlamentar dos Senadores)
expenses. Creates Expense nodes linked to Person (senator) via GASTOU
and to Company (supplier) via FORNECEU.

Senator identity enrichment: loads parlamentares.json (from Dados Abertos API)
to map parliamentary names to CPFs for deterministic matching.
"""

from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    deduplicate_rows,
    format_cnpj,
    format_cpf,
    normalize_name,
    parse_date,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)


def _parse_brl_value(value: str) -> float:
    """Parse Brazilian numeric format (1.234,56) to float."""
    if not value or not value.strip():
        return 0.0
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _make_expense_id(senator_name: str, date: str, supplier_doc: str, value: str) -> str:
    """Generate a stable expense ID from key fields."""
    raw = f"senado_{senator_name}_{date}_{supplier_doc}_{value}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class SenadoPipeline(Pipeline):
    """ETL pipeline for Senado Federal CEAPS expenses."""

    name = "senado"
    source_id = "senado"

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
        self._senator_lookup: dict[str, dict[str, str]] = {}
        self.expenses: list[dict[str, Any]] = []
        self.suppliers: list[dict[str, Any]] = []
        self.gastou_rels: list[dict[str, Any]] = []
        self.gastou_by_name_rels: list[dict[str, Any]] = []
        self.forneceu_rels: list[dict[str, Any]] = []

    def _load_senator_lookup(self) -> dict[str, dict[str, str]]:
        """Load senator identity lookup from parlamentares.json.

        Returns a dict mapping normalized parliamentary name to senator info
        (cpf, codigo, nome_completo).
        """
        lookup_path = Path(self.data_dir) / "senado" / "parlamentares.json"
        if not lookup_path.exists():
            logger.info("No parlamentares.json found — senator CPF enrichment disabled")
            return {}

        with open(lookup_path, encoding="utf-8") as f:
            senators = json.load(f)

        lookup: dict[str, dict[str, str]] = {}
        for s in senators:
            nome = normalize_name(s.get("nome_parlamentar", ""))
            if nome:
                lookup[nome] = {
                    "cpf": s.get("cpf", ""),
                    "codigo": s.get("codigo", ""),
                    "nome_completo": s.get("nome_completo", ""),
                }
            # Also index by full civil name for broader matching
            nome_completo = normalize_name(s.get("nome_completo", ""))
            if nome_completo and nome_completo != nome:
                lookup[nome_completo] = {
                    "cpf": s.get("cpf", ""),
                    "codigo": s.get("codigo", ""),
                    "nome_completo": s.get("nome_completo", ""),
                }

        logger.info(
            "Loaded senator lookup: %d entries (%d with CPF)",
            len(lookup),
            sum(1 for v in lookup.values() if v["cpf"]),
        )
        return lookup

    def extract(self) -> None:
        senado_dir = Path(self.data_dir) / "senado"

        # Load senator identity lookup for CPF enrichment
        self._senator_lookup = self._load_senator_lookup()

        csv_files = sorted(senado_dir.glob("*.csv"))
        if not csv_files:
            logger.warning("No CSV files found in %s", senado_dir)
            return

        frames: list[pd.DataFrame] = []
        for f in csv_files:
            df = pd.read_csv(
                f,
                sep=";",
                dtype=str,
                encoding="latin-1",
                keep_default_na=False,
                skiprows=1,
            )
            frames.append(df)
            logger.info("  Loaded %d rows from %s", len(df), f.name)

        self._raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
        logger.info("Total raw rows: %d", len(self._raw))

    def transform(self) -> None:
        if self._raw.empty:
            return

        expenses: list[dict[str, Any]] = []
        suppliers_map: dict[str, dict[str, Any]] = {}
        gastou: list[dict[str, Any]] = []
        gastou_by_name: list[dict[str, Any]] = []
        forneceu: list[dict[str, Any]] = []
        skipped = 0

        for _, row in self._raw.iterrows():
            senator_name = normalize_name(str(row.get("SENADOR", "")))
            expense_type = str(row.get("TIPO_DESPESA", "")).strip()

            supplier_doc_raw = str(row.get("CNPJ_CPF", ""))
            supplier_digits = strip_document(supplier_doc_raw)
            supplier_name = normalize_name(str(row.get("FORNECEDOR", "")))

            if not supplier_digits:
                skipped += 1
                continue

            # Format supplier document
            if len(supplier_digits) == 14:
                supplier_doc = format_cnpj(supplier_doc_raw)
            elif len(supplier_digits) == 11:
                supplier_doc = format_cpf(supplier_doc_raw)
            else:
                skipped += 1
                continue

            date = parse_date(str(row.get("DATA", "")))
            value = _parse_brl_value(str(row.get("VALOR_REEMBOLSADO", "")))
            documento = str(row.get("DOCUMENTO", "")).strip()
            detalhamento = str(row.get("DETALHAMENTO", "")).strip()

            expense_id = _make_expense_id(senator_name, date, supplier_doc, str(value))

            expenses.append({
                "expense_id": expense_id,
                "senator_name": senator_name,
                "type": expense_type,
                "supplier_doc": supplier_doc,
                "value": value,
                "date": date,
                "description": detalhamento or expense_type,
                "documento": documento,
                "source": "senado",
            })

            # Track senator -> expense (CPF-first, name fallback)
            senator_info = self._senator_lookup.get(senator_name, {})
            senator_cpf_raw = senator_info.get("cpf", "")
            senator_cpf_digits = strip_document(senator_cpf_raw)
            if len(senator_cpf_digits) == 11:
                senator_cpf = format_cpf(senator_cpf_raw)
                gastou.append({
                    "source_key": senator_cpf,
                    "target_key": expense_id,
                })
            elif senator_name:
                gastou_by_name.append({
                    "senator_name": senator_name,
                    "target_key": expense_id,
                })

            # Track supplier
            if len(supplier_digits) == 14:
                suppliers_map[supplier_doc] = {
                    "cnpj": supplier_doc,
                    "razao_social": supplier_name,
                }
            elif len(supplier_digits) == 11:
                suppliers_map[supplier_doc] = {
                    "cpf": supplier_doc,
                    "name": supplier_name,
                }

            forneceu.append({
                "source_key": supplier_doc,
                "target_key": expense_id,
            })

        self.expenses = deduplicate_rows(expenses, ["expense_id"])
        self.suppliers = list(suppliers_map.values())
        self.gastou_rels = gastou
        self.gastou_by_name_rels = gastou_by_name
        self.forneceu_rels = forneceu

        if self.limit:
            self.expenses = self.expenses[: self.limit]

        logger.info(
            "Transformed: %d expenses, %d suppliers, "
            "%d GASTOU (CPF) + %d GASTOU (name) (skipped %d)",
            len(self.expenses),
            len(self.suppliers),
            len(self.gastou_rels),
            len(self.gastou_by_name_rels),
            skipped,
        )

    def load(self) -> None:
        if not self.expenses:
            logger.warning("No expenses to load")
            return

        loader = Neo4jBatchLoader(self.driver)

        # Load Expense nodes
        expense_nodes = [
            {
                "expense_id": e["expense_id"],
                "type": e["type"],
                "value": e["value"],
                "date": e["date"],
                "description": e["description"],
                "source": e["source"],
            }
            for e in self.expenses
        ]
        count = loader.load_nodes("Expense", expense_nodes, key_field="expense_id")
        logger.info("Loaded %d Expense nodes", count)

        # Load/merge Company nodes for CNPJ suppliers
        company_suppliers = [s for s in self.suppliers if "cnpj" in s]
        if company_suppliers:
            count = loader.load_nodes("Company", company_suppliers, key_field="cnpj")
            logger.info("Merged %d supplier Company nodes", count)

        # Load/merge Person nodes for CPF suppliers
        person_suppliers = [s for s in self.suppliers if "cpf" in s]
        if person_suppliers:
            count = loader.load_nodes("Person", person_suppliers, key_field="cpf")
            logger.info("Merged %d supplier Person nodes", count)

        # GASTOU: Person (senator) -> Expense
        # Tier 1: CPF-based (from senator lookup enrichment)
        if self.gastou_rels:
            count = loader.load_relationships(
                rel_type="GASTOU",
                rows=self.gastou_rels,
                source_label="Person",
                source_key="cpf",
                target_label="Expense",
                target_key="expense_id",
            )
            logger.info("Created %d GASTOU relationships (CPF)", count)

        # Tier 2: Name-based (no CANDIDATO_EM filter — matches suplentes and
        # pre-2002 senators who lack TSE candidacy records)
        if self.gastou_by_name_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (e:Expense {expense_id: row.target_key}) "
                "MATCH (p:Person {name: row.senator_name}) "
                "MERGE (p)-[:GASTOU]->(e)"
            )
            count = loader.run_query(query, self.gastou_by_name_rels)
            logger.info("Created %d GASTOU relationships (name)", count)

        # FORNECEU: Company/Person -> Expense
        if self.forneceu_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (e:Expense {expense_id: row.target_key}) "
                "OPTIONAL MATCH (c:Company {cnpj: row.source_key}) "
                "OPTIONAL MATCH (p:Person {cpf: row.source_key}) "
                "WITH e, coalesce(c, p) AS supplier "
                "WHERE supplier IS NOT NULL "
                "MERGE (supplier)-[:FORNECEU]->(e)"
            )
            count = loader.run_query(query, self.forneceu_rels)
            logger.info("Created %d FORNECEU relationships", count)
