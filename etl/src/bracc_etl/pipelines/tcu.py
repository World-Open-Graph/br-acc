from __future__ import annotations

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


class TcuPipeline(Pipeline):
    """ETL pipeline for TCU (Tribunal de Contas da Uniao) accountability data.

    Loads four datasets:
    - inabilitados: individuals barred from public office
    - licitantes inidoneos: companies declared unfit for public bidding
    - contas julgadas irregulares: persons with irregular accounts
    - contas irregulares com implicacao eleitoral: same with electoral context
    """

    name = "tcu"
    source_id = "tcu"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_inabilitados: pd.DataFrame = pd.DataFrame()
        self._raw_inidoneos: pd.DataFrame = pd.DataFrame()
        self._raw_irregulares: pd.DataFrame = pd.DataFrame()
        self._raw_irregulares_eleitorais: pd.DataFrame = pd.DataFrame()
        self.sanctions: list[dict[str, Any]] = []
        self.sanctioned_persons: list[dict[str, Any]] = []
        self.sanctioned_companies: list[dict[str, Any]] = []

    def _read_csv(self, path: Path) -> pd.DataFrame:
        return pd.read_csv(
            path,
            dtype=str,
            sep="|",
            encoding="utf-8",
            keep_default_na=False,
            quotechar='"',
        )

    def extract(self) -> None:
        tcu_dir = Path(self.data_dir) / "tcu"

        self._raw_inabilitados = self._read_csv(
            tcu_dir / "inabilitados-funcao-publica.csv"
        )
        self._raw_inidoneos = self._read_csv(
            tcu_dir / "licitantes-inidoneos.csv"
        )
        self._raw_irregulares = self._read_csv(
            tcu_dir / "resp-contas-julgadas-irregulares.csv"
        )
        self._raw_irregulares_eleitorais = self._read_csv(
            tcu_dir / "resp-contas-julgadas-irreg-implicacao-eleitoral.csv"
        )

        logger.info(
            "[tcu] Extracted: %d inabilitados, %d inidoneos, "
            "%d irregulares, %d irregulares eleitorais",
            len(self._raw_inabilitados),
            len(self._raw_inidoneos),
            len(self._raw_irregulares),
            len(self._raw_irregulares_eleitorais),
        )

    def _process_inabilitados(self) -> None:
        """Persons barred from public office (CPF-only)."""
        for idx, row in self._raw_inabilitados.iterrows():
            cpf_raw = str(row["CPF"]).strip()
            digits = strip_document(cpf_raw)
            if len(digits) != 11:
                continue

            cpf = format_cpf(cpf_raw)
            nome = normalize_name(str(row["NOME"]))
            processo = str(row["PROCESSO"]).strip()
            deliberacao = str(row["DELIBERACAO"]).strip()
            date_start = parse_date(str(row["DATA TRANSITO JULGADO"]))
            date_end = parse_date(str(row["DATA FINAL"]))
            date_acordao = parse_date(str(row["DATA ACORDAO"]))
            uf = str(row["UF"]).strip()
            municipio = str(row["MUNICIPIO"]).strip()

            sanction_id = f"tcu_inabilitado_{digits}_{idx}"
            self.sanctions.append({
                "sanction_id": sanction_id,
                "type": "tcu_inabilitado",
                "court": "TCU",
                "processo": processo,
                "deliberacao": deliberacao,
                "date_start": date_start,
                "date_end": date_end,
                "date_acordao": date_acordao,
                "uf": uf,
                "municipio": municipio,
                "cargo": "",
                "source": "tcu",
            })
            self.sanctioned_persons.append({
                "cpf": cpf,
                "name": nome,
                "sanction_id": sanction_id,
            })

    def _process_inidoneos(self) -> None:
        """Companies declared unfit for public bidding (CNPJ-only)."""
        for idx, row in self._raw_inidoneos.iterrows():
            doc_raw = str(row["CPF_CNPJ"]).strip()
            digits = strip_document(doc_raw)
            nome = normalize_name(str(row["NOME"]))
            processo = str(row["PROCESSO"]).strip()
            deliberacao = str(row["DELIBERACAO"]).strip()
            date_start = parse_date(str(row["DATA TRANSITO JULGADO"]))
            date_end = parse_date(str(row["DATA FINAL"]))
            date_acordao = parse_date(str(row["DATA ACORDAO"]))
            uf = str(row["UF"]).strip()
            municipio = str(row["MUNICIPIO"]).strip()

            sanction_id = f"tcu_inidoneo_{digits}_{idx}"
            self.sanctions.append({
                "sanction_id": sanction_id,
                "type": "tcu_inidoneo",
                "court": "TCU",
                "processo": processo,
                "deliberacao": deliberacao,
                "date_start": date_start,
                "date_end": date_end,
                "date_acordao": date_acordao,
                "uf": uf,
                "municipio": municipio,
                "cargo": "",
                "source": "tcu",
            })

            if len(digits) == 14:
                cnpj = format_cnpj(doc_raw)
                self.sanctioned_companies.append({
                    "cnpj": cnpj,
                    "razao_social": nome,
                    "name": nome,
                    "sanction_id": sanction_id,
                })
            elif len(digits) == 11:
                cpf = format_cpf(doc_raw)
                self.sanctioned_persons.append({
                    "cpf": cpf,
                    "name": nome,
                    "sanction_id": sanction_id,
                })

    def _process_irregulares(self) -> None:
        """Persons with accounts judged irregular (may have CPF or CNPJ)."""
        for idx, row in self._raw_irregulares.iterrows():
            doc_raw = str(row["CPF_CNPJ"]).strip()
            digits = strip_document(doc_raw)
            nome = normalize_name(str(row["NOME"]))
            processo = str(row["PROCESSO"]).strip()
            deliberacao = str(row["DELIBERACAO"]).strip()
            date_start = parse_date(str(row["DATA TRANSITO JULGADO"]))
            uf = str(row["UF"]).strip()
            municipio = str(row["MUNICIPIO"]).strip()

            sanction_id = f"tcu_irregular_{digits}_{idx}"
            self.sanctions.append({
                "sanction_id": sanction_id,
                "type": "tcu_conta_irregular",
                "court": "TCU",
                "processo": processo,
                "deliberacao": deliberacao,
                "date_start": date_start,
                "date_end": "",
                "date_acordao": "",
                "uf": uf,
                "municipio": municipio,
                "cargo": "",
                "source": "tcu",
            })

            if len(digits) == 14:
                cnpj = format_cnpj(doc_raw)
                self.sanctioned_companies.append({
                    "cnpj": cnpj,
                    "razao_social": nome,
                    "name": nome,
                    "sanction_id": sanction_id,
                })
            elif len(digits) == 11:
                cpf = format_cpf(doc_raw)
                self.sanctioned_persons.append({
                    "cpf": cpf,
                    "name": nome,
                    "sanction_id": sanction_id,
                })

    def _process_irregulares_eleitorais(self) -> None:
        """Persons with irregular accounts and electoral implication (CPF-only)."""
        for idx, row in self._raw_irregulares_eleitorais.iterrows():
            cpf_raw = str(row["CPF"]).strip()
            digits = strip_document(cpf_raw)
            if len(digits) != 11:
                continue

            cpf = format_cpf(cpf_raw)
            nome = normalize_name(str(row["NOME"]))
            processo = str(row["PROCESSO"]).strip()
            deliberacao = str(row["DELIBERACAO"]).strip()
            date_start = parse_date(str(row["DATA TRANSITO JULGADO"]))
            date_end = parse_date(str(row["DATA FINAL"]))
            uf = str(row["UF"]).strip()
            municipio = str(row["MUNICIPIO"]).strip()
            cargo = str(row.get("CARGO/FUNCAO", "")).strip()

            sanction_id = f"tcu_irregular_eleitoral_{digits}_{idx}"
            self.sanctions.append({
                "sanction_id": sanction_id,
                "type": "tcu_conta_irregular_eleitoral",
                "court": "TCU",
                "processo": processo,
                "deliberacao": deliberacao,
                "date_start": date_start,
                "date_end": date_end,
                "date_acordao": "",
                "uf": uf,
                "municipio": municipio,
                "cargo": cargo,
                "source": "tcu",
            })
            self.sanctioned_persons.append({
                "cpf": cpf,
                "name": nome,
                "sanction_id": sanction_id,
            })

    def transform(self) -> None:
        self._process_inabilitados()
        self._process_inidoneos()
        self._process_irregulares()
        self._process_irregulares_eleitorais()

        self.sanctions = deduplicate_rows(self.sanctions, ["sanction_id"])

        logger.info(
            "[tcu] Transformed: %d sanctions, %d person links, %d company links",
            len(self.sanctions),
            len(self.sanctioned_persons),
            len(self.sanctioned_companies),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        # Load Sanction nodes
        if self.sanctions:
            loader.load_nodes("Sanction", self.sanctions, key_field="sanction_id")
            logger.info("[tcu] Loaded %d Sanction nodes", len(self.sanctions))

        # Merge Person nodes and create relationships
        if self.sanctioned_persons:
            person_nodes = deduplicate_rows(
                [{"cpf": p["cpf"], "name": p["name"]} for p in self.sanctioned_persons],
                ["cpf"],
            )
            loader.load_nodes("Person", person_nodes, key_field="cpf")
            logger.info("[tcu] Merged %d Person nodes", len(person_nodes))

            person_rels = [
                {"source_key": p["cpf"], "target_key": p["sanction_id"]}
                for p in self.sanctioned_persons
            ]
            query_person = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.source_key}) "
                "MATCH (s:Sanction {sanction_id: row.target_key}) "
                "MERGE (p)-[:SANCIONADA]->(s)"
            )
            loader.run_query(query_person, person_rels)
            logger.info("[tcu] Created %d Person-SANCIONADA->Sanction rels", len(person_rels))

        # Merge Company nodes and create relationships
        if self.sanctioned_companies:
            company_nodes = deduplicate_rows(
                [
                    {"cnpj": c["cnpj"], "razao_social": c["razao_social"], "name": c["name"]}
                    for c in self.sanctioned_companies
                ],
                ["cnpj"],
            )
            loader.load_nodes("Company", company_nodes, key_field="cnpj")
            logger.info("[tcu] Merged %d Company nodes", len(company_nodes))

            company_rels = [
                {"source_key": c["cnpj"], "target_key": c["sanction_id"]}
                for c in self.sanctioned_companies
            ]
            query_company = (
                "UNWIND $rows AS row "
                "MATCH (c:Company {cnpj: row.source_key}) "
                "MATCH (s:Sanction {sanction_id: row.target_key}) "
                "MERGE (c)-[:SANCIONADA]->(s)"
            )
            loader.run_query(query_company, company_rels)
            logger.info("[tcu] Created %d Company-SANCIONADA->Sanction rels", len(company_rels))
