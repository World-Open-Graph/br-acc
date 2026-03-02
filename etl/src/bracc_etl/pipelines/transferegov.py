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
    format_cnpj,
    normalize_name,
    parse_date,
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


class TransferegovPipeline(Pipeline):
    """ETL pipeline for TransfereGov parliamentary amendments data.

    Sources: Portal da Transparência emendas parlamentares bulk download.
    Three CSV files:
    - EmendasParlamentares.csv: amendments with authors, functions, municipalities
    - EmendasParlamentares_PorFavorecido.csv: who received the money (companies/persons)
    - EmendasParlamentares_Convenios.csv: convênios linked to amendments
    """

    name = "transferegov"
    source_id = "transferegov"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_emendas: pd.DataFrame = pd.DataFrame()
        self._raw_favorecidos: pd.DataFrame = pd.DataFrame()
        self._raw_convenios: pd.DataFrame = pd.DataFrame()
        self.amendments: list[dict[str, Any]] = []
        self.authors: list[dict[str, Any]] = []
        self.author_rels: list[dict[str, Any]] = []
        self.favorecido_companies: list[dict[str, Any]] = []
        self.favorecido_persons: list[dict[str, Any]] = []
        self.favorecido_rels: list[dict[str, Any]] = []
        self.convenios: list[dict[str, Any]] = []
        self.convenio_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "transferegov"
        self._raw_emendas = pd.read_csv(
            src_dir / "EmendasParlamentares.csv",
            dtype=str,
            encoding="latin-1",
            sep=";",
            keep_default_na=False,
        )
        self._raw_favorecidos = pd.read_csv(
            src_dir / "EmendasParlamentares_PorFavorecido.csv",
            dtype=str,
            encoding="latin-1",
            sep=";",
            keep_default_na=False,
        )
        self._raw_convenios = pd.read_csv(
            src_dir / "EmendasParlamentares_Convenios.csv",
            dtype=str,
            encoding="latin-1",
            sep=";",
            keep_default_na=False,
        )

    def transform(self) -> None:
        self._transform_amendments()
        self._transform_favorecidos()
        self._transform_convenios()

    def _transform_amendments(self) -> None:
        """Transform main amendments file: Amendment nodes + Person authors."""
        amendments: list[dict[str, Any]] = []
        authors: list[dict[str, Any]] = []
        author_rels: list[dict[str, Any]] = []

        # Group by amendment code to aggregate values
        grouped = self._raw_emendas.groupby("Código da Emenda")

        for code, group in grouped:
            code_str = str(code).strip()
            if not code_str or code_str == "Sem informação":
                continue

            first = group.iloc[0]
            author_code = str(first["Código do Autor da Emenda"]).strip()
            author_name = normalize_name(str(first["Nome do Autor da Emenda"]))
            emenda_type = str(first["Tipo de Emenda"]).strip()
            function_name = normalize_name(str(first["Nome Função"]))
            municipality = str(first["Município"]).strip()
            uf = str(first["UF"]).strip()

            # Sum values across all rows for this amendment
            value_empenhado = sum(
                _parse_brl(str(r["Valor Empenhado"]))
                for _, r in group.iterrows()
            )
            value_pago = sum(
                _parse_brl(str(r["Valor Pago"]))
                for _, r in group.iterrows()
            )

            amendments.append({
                "amendment_id": code_str,
                "type": emenda_type,
                "function": function_name,
                "municipality": municipality,
                "uf": uf,
                "value_committed": value_empenhado,
                "value_paid": value_pago,
            })

            # Author relationship
            if author_code and author_code != "S/I":
                authors.append({
                    "author_key": author_code,
                    "name": author_name,
                })
                author_rels.append({
                    "source_key": author_code,
                    "target_key": code_str,
                })

        self.amendments = deduplicate_rows(amendments, ["amendment_id"])
        self.authors = deduplicate_rows(authors, ["author_key"])
        self.author_rels = author_rels

    def _transform_favorecidos(self) -> None:
        """Transform favorecidos: companies/persons receiving amendment funds."""
        companies: list[dict[str, Any]] = []
        persons: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []

        for _, row in self._raw_favorecidos.iterrows():
            emenda_code = str(row["Código da Emenda"]).strip()
            if not emenda_code or emenda_code == "Sem informação":
                continue

            doc_raw = str(row["Código do Favorecido"]).strip()
            digits = strip_document(doc_raw)
            tipo = str(row["Tipo Favorecido"]).strip()
            nome = normalize_name(str(row["Favorecido"]))
            valor = _parse_brl(str(row["Valor Recebido"]))
            municipio = str(row["Município Favorecido"]).strip()
            uf = str(row["UF Favorecido"]).strip()

            if tipo == "Pessoa Jurídica" and len(digits) == 14:
                cnpj = format_cnpj(doc_raw)
                companies.append({
                    "cnpj": cnpj,
                    "razao_social": nome,
                })
                rels.append({
                    "amendment_id": emenda_code,
                    "doc": cnpj,
                    "entity_type": "Company",
                    "doc_field": "cnpj",
                    "value": valor,
                    "municipality": municipio,
                    "uf": uf,
                })
            elif tipo == "Pessoa Fisica" and len(digits) == 11:
                # Individual CPFs — we don't store raw CPFs for non-PEPs,
                # but we still create Person nodes for graph linkage
                from bracc_etl.transforms import format_cpf

                cpf = format_cpf(doc_raw)
                persons.append({
                    "cpf": cpf,
                    "name": nome,
                })
                rels.append({
                    "amendment_id": emenda_code,
                    "doc": cpf,
                    "entity_type": "Person",
                    "doc_field": "cpf",
                    "value": valor,
                    "municipality": municipio,
                    "uf": uf,
                })
            # Skip Unidade Gestora, Inscrição Genérica, Inválido

        self.favorecido_companies = deduplicate_rows(companies, ["cnpj"])
        self.favorecido_persons = deduplicate_rows(persons, ["cpf"])
        self.favorecido_rels = rels

    def _transform_convenios(self) -> None:
        """Transform convênios linked to amendments."""
        convenios: list[dict[str, Any]] = []
        rels: list[dict[str, Any]] = []

        for _, row in self._raw_convenios.iterrows():
            emenda_code = str(row["Código da Emenda"]).strip()
            if not emenda_code or emenda_code == "Sem informação":
                continue

            numero = str(row["Número Convênio"]).strip()
            if not numero:
                continue

            convenente = normalize_name(str(row["Convenente"]))
            objeto = normalize_name(str(row["Objeto Convênio"]))
            valor = _parse_brl(str(row["Valor Convênio"]))
            data_pub = parse_date(str(row["Data Publicação Convênio"]))
            funcao = normalize_name(str(row["Nome Função"]))

            convenios.append({
                "convenio_id": numero,
                "convenente": convenente,
                "object": objeto,
                "value": valor,
                "date_published": data_pub,
                "function": funcao,
            })

            rels.append({
                "source_key": emenda_code,
                "target_key": numero,
            })

        self.convenios = deduplicate_rows(convenios, ["convenio_id"])
        self.convenio_rels = rels

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        # 1. Amendment nodes
        if self.amendments:
            loader.load_nodes("Amendment", self.amendments, key_field="amendment_id")

        # 2. Person nodes for authors (keyed by author_key for entity resolution)
        if self.authors:
            loader.load_nodes("Person", self.authors, key_field="author_key")

        # 3. Person -[:AUTOR_EMENDA]-> Amendment
        if self.author_rels:
            loader.load_relationships(
                rel_type="AUTOR_EMENDA",
                rows=self.author_rels,
                source_label="Person",
                source_key="author_key",
                target_label="Amendment",
                target_key="amendment_id",
            )

        # 4. Company nodes for favorecidos
        if self.favorecido_companies:
            loader.load_nodes(
                "Company", self.favorecido_companies, key_field="cnpj"
            )

        # 5. Person nodes for favorecidos
        if self.favorecido_persons:
            loader.load_nodes(
                "Person", self.favorecido_persons, key_field="cpf"
            )

        # 6. Amendment -[:BENEFICIOU]-> Company/Person
        if self.favorecido_rels:
            company_rels = [
                r for r in self.favorecido_rels if r["entity_type"] == "Company"
            ]
            person_rels = [
                r for r in self.favorecido_rels if r["entity_type"] == "Person"
            ]

            if company_rels:
                query = (
                    "UNWIND $rows AS row "
                    "MATCH (a:Amendment {amendment_id: row.amendment_id}) "
                    "MATCH (c:Company {cnpj: row.doc}) "
                    "MERGE (a)-[r:BENEFICIOU]->(c) "
                    "SET r.value = row.value, "
                    "r.municipality = row.municipality, "
                    "r.uf = row.uf"
                )
                loader.run_query(query, company_rels)

            if person_rels:
                query = (
                    "UNWIND $rows AS row "
                    "MATCH (a:Amendment {amendment_id: row.amendment_id}) "
                    "MATCH (p:Person {cpf: row.doc}) "
                    "MERGE (a)-[r:BENEFICIOU]->(p) "
                    "SET r.value = row.value, "
                    "r.municipality = row.municipality, "
                    "r.uf = row.uf"
                )
                loader.run_query(query, person_rels)

        # 7. Convenio nodes
        if self.convenios:
            loader.load_nodes("Convenio", self.convenios, key_field="convenio_id")

        # 8. Amendment -[:GEROU_CONVENIO]-> Convenio
        if self.convenio_rels:
            loader.load_relationships(
                rel_type="GEROU_CONVENIO",
                rows=self.convenio_rels,
                source_label="Amendment",
                source_key="amendment_id",
                target_label="Convenio",
                target_key="convenio_id",
            )
