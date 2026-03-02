from __future__ import annotations

import re
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
    strip_document,
)


def _parse_brl(value: str | None) -> float:
    """Parse Brazilian monetary string to float (e.g. '1.234.567,89')."""
    if not value:
        return 0.0
    cleaned = str(value).strip()
    cleaned = re.sub(r"[R$\s]", "", cleaned)
    if not cleaned:
        return 0.0
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _classify_amendment_type(raw_type: str) -> str:
    """Normalize amendment type to a canonical category."""
    normalized = raw_type.strip().lower()
    if "individual" in normalized:
        return "individual"
    if "bancada" in normalized:
        return "bancada"
    if "comiss" in normalized:
        return "comissao"
    if "relator" in normalized:
        return "relator"
    return raw_type.strip()


class SiopPipeline(Pipeline):
    """ETL pipeline for SIOP parliamentary amendments detail.

    Source: Portal da Transparencia emendas-parlamentares yearly CSVs.
    Enriches existing Amendment nodes (from TransfereGov) or creates new ones
    with budget execution detail (authorized, committed, paid amounts),
    amendment type classification, program/action codes, and author linkage.
    """

    name = "siop"
    source_id = "siop"

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
        self.amendments: list[dict[str, Any]] = []
        self.authors: list[dict[str, Any]] = []
        self.author_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        siop_dir = Path(self.data_dir) / "siop"
        csv_files = sorted(siop_dir.glob("*.csv"))
        if not csv_files:
            return

        frames: list[pd.DataFrame] = []
        for csv_path in csv_files:
            df = pd.read_csv(
                csv_path,
                dtype=str,
                encoding="latin-1",
                sep=";",
                keep_default_na=False,
            )
            frames.append(df)

        self._raw = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    @staticmethod
    def _resolve_col(row: Any, *candidates: str) -> str:
        """Return the first non-empty value found among column name candidates."""
        for c in candidates:
            val = row.get(c)
            if val is not None and str(val).strip():
                return str(val).strip()
        return ""

    def transform(self) -> None:
        if self._raw.empty:
            return

        amendments: list[dict[str, Any]] = []
        authors: list[dict[str, Any]] = []
        author_rels: list[dict[str, Any]] = []

        # Detect the amendment code column (two naming conventions)
        col_code: str | None = None
        for candidate in ("CÓDIGO EMENDA", "Código da Emenda"):
            if candidate in self._raw.columns:
                col_code = candidate
                break
        if col_code is None:
            return

        grouped = self._raw.groupby(col_code)

        for code, group in grouped:
            code_str = str(code).strip()
            if not code_str or code_str.lower() == "sem informação":
                continue

            first = group.iloc[0]

            year = self._resolve_col(first, "ANO", "Ano da Emenda")
            amendment_number = self._resolve_col(
                first, "NÚMERO EMENDA", "Número da emenda"
            )
            raw_type = self._resolve_col(first, "TIPO EMENDA", "Tipo de Emenda")
            amendment_type = _classify_amendment_type(raw_type)
            author_name = normalize_name(
                self._resolve_col(first, "AUTOR EMENDA", "Nome do Autor da Emenda")
            )
            author_doc = self._resolve_col(
                first, "CPF/CNPJ AUTOR", "Código do Autor da Emenda"
            )
            locality = self._resolve_col(
                first, "LOCALIDADE", "Localidade de aplicação do recurso"
            )

            # Program/action from first row (consistent within an amendment)
            program = normalize_name(
                self._resolve_col(first, "NOME PROGRAMA", "Nome Programa")
            )
            program_code = self._resolve_col(
                first, "CÓDIGO PROGRAMA", "Código Programa"
            )
            action = normalize_name(
                self._resolve_col(first, "NOME AÇÃO", "Nome Ação")
            )
            action_code = self._resolve_col(
                first, "CÓDIGO AÇÃO", "Código Ação"
            )
            function_name = normalize_name(
                self._resolve_col(first, "NOME FUNÇÃO", "Nome Função")
            )

            # Sum monetary values across all rows for this amendment
            amount_committed = sum(
                _parse_brl(self._resolve_col(r, "VALOR EMPENHADO", "Valor Empenhado"))
                for _, r in group.iterrows()
            )
            amount_settled = sum(
                _parse_brl(self._resolve_col(r, "VALOR LIQUIDADO", "Valor Liquidado"))
                for _, r in group.iterrows()
            )
            amount_paid = sum(
                _parse_brl(self._resolve_col(r, "VALOR PAGO", "Valor Pago"))
                for _, r in group.iterrows()
            )

            # Build unique amendment_id from code
            amendment_id = f"siop_{code_str}"

            amendments.append({
                "amendment_id": amendment_id,
                "amendment_code": code_str,
                "amendment_number": amendment_number,
                "year": year,
                "amendment_type": amendment_type,
                "author_name": author_name,
                "locality": locality,
                "function": function_name,
                "program": program,
                "program_code": program_code,
                "action": action,
                "action_code": action_code,
                "amount_committed": amount_committed,
                "amount_settled": amount_settled,
                "amount_paid": amount_paid,
                "source": "siop",
            })

            # Author linkage — only if CPF is present (11 digits)
            author_digits = strip_document(author_doc)
            if len(author_digits) == 11 and author_name:
                cpf_formatted = format_cpf(author_doc)
                authors.append({
                    "cpf": cpf_formatted,
                    "name": author_name,
                })
                author_rels.append({
                    "source_key": cpf_formatted,
                    "target_key": amendment_id,
                })

        self.amendments = deduplicate_rows(amendments, ["amendment_id"])
        self.authors = deduplicate_rows(authors, ["cpf"])
        self.author_rels = author_rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        # 1. Amendment nodes
        if self.amendments:
            loader.load_nodes("Amendment", self.amendments, key_field="amendment_id")

        # 2. Person nodes for authors with CPF
        if self.authors:
            loader.load_nodes("Person", self.authors, key_field="cpf")

        # 3. Person -[:AUTOR_EMENDA]-> Amendment
        if self.author_rels:
            query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (a:Amendment {amendment_id: row.target_key}) "
                "MERGE (p)-[:AUTOR_EMENDA]->(a)"
            )
            loader.run_query_with_retry(query, self.author_rels)
