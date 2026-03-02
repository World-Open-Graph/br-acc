from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    cap_contract_value,
    deduplicate_rows,
    format_cnpj,
    normalize_name,
    parse_date,
    strip_document,
)

logger = logging.getLogger(__name__)

# Classified contracts (Polícia Federal etc.) use this sentinel CNPJ.
_SIGILOSO_CNPJ = "-11"


def _parse_brl(value: str | None) -> float:
    """Parse Brazilian monetary string to float.

    Handles formats like "1.234.567,89" and "1234567.89".
    """
    if not value:
        return 0.0
    cleaned = str(value).strip()
    # Remove currency symbol and whitespace
    cleaned = re.sub(r"[R$\s]", "", cleaned)
    if not cleaned:
        return 0.0
    # Brazilian format: dots as thousands sep, comma as decimal
    if "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _extract_cpf_middle6(cpf_raw: str) -> str | None:
    """Extract 6 middle digits from LGPD-masked CPF (***.ABC.DEF-**)."""
    digits = strip_document(cpf_raw)
    if len(digits) == 6:
        return digits
    return None


def _make_servidor_id(cpf_partial: str | None, name: str) -> str:
    """Generate stable ID for servidor Person from partial CPF + name."""
    raw = f"{cpf_partial or ''}_{name}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _make_office_id(cpf_partial: str | None, name: str, org: str) -> str:
    """Generate stable ID for PublicOffice from partial CPF + name + org."""
    raw = f"{cpf_partial or ''}_{name}_{org}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


class TransparenciaPipeline(Pipeline):
    """ETL pipeline for Portal da Transparencia federal spending data."""

    name = "transparencia"
    source_id = "portal_transparencia"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._raw_contratos: pd.DataFrame = pd.DataFrame()
        self._raw_servidores: pd.DataFrame = pd.DataFrame()
        self._raw_emendas: pd.DataFrame = pd.DataFrame()
        self.contracts: list[dict[str, Any]] = []
        self.offices: list[dict[str, Any]] = []
        self.amendments: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "transparencia"
        if not src_dir.exists():
            logger.warning("[%s] Data directory not found: %s", self.name, src_dir)
            return
        contratos_path = src_dir / "contratos.csv"
        servidores_path = src_dir / "servidores.csv"
        emendas_path = src_dir / "emendas.csv"
        if not contratos_path.exists():
            logger.warning("[%s] contratos.csv not found in %s", self.name, src_dir)
        else:
            self._raw_contratos = pd.read_csv(
                contratos_path, dtype=str, keep_default_na=False, encoding="utf-8",
            )
        if not servidores_path.exists():
            logger.warning("[%s] servidores.csv not found in %s", self.name, src_dir)
        else:
            self._raw_servidores = pd.read_csv(
                servidores_path, dtype=str, keep_default_na=False, encoding="utf-8",
            )
        if not emendas_path.exists():
            logger.warning("[%s] emendas.csv not found in %s", self.name, src_dir)
        else:
            self._raw_emendas = pd.read_csv(
                emendas_path, dtype=str, keep_default_na=False, encoding="utf-8",
            )

    def transform(self) -> None:
        contracts: list[dict[str, Any]] = []
        for _, row in self._raw_contratos.iterrows():
            raw_cnpj = str(row["cnpj_contratada"]).strip()

            # Skip classified contracts (sigiloso) — no usable CNPJ
            if raw_cnpj == _SIGILOSO_CNPJ:
                continue

            # Skip rows where CNPJ has no digits (produces malformed contract_ids)
            cnpj_digits = strip_document(raw_cnpj)
            if len(cnpj_digits) != 14:
                continue

            cnpj = format_cnpj(raw_cnpj)
            date = parse_date(str(row["data_inicio"]))
            contracts.append({
                "contract_id": f"{cnpj_digits}_{row['data_inicio']}",
                "object": normalize_name(str(row["objeto"])),
                "value": cap_contract_value(_parse_brl(str(row["valor"]))),
                "contracting_org": normalize_name(str(row["orgao_contratante"])),
                "date": date,
                "cnpj": cnpj,
                "razao_social": normalize_name(str(row["razao_social"])),
            })
        self.contracts = deduplicate_rows(contracts, ["contract_id"])

        offices: list[dict[str, Any]] = []
        for _, row in self._raw_servidores.iterrows():
            raw_cpf = str(row["cpf"])
            cpf_partial = _extract_cpf_middle6(raw_cpf)
            name = normalize_name(str(row["nome"]))
            org = normalize_name(str(row["orgao"]))
            salary = _parse_brl(str(row["remuneracao"]))

            servidor_id = _make_servidor_id(cpf_partial, name)
            office_id = _make_office_id(cpf_partial, name, org)

            offices.append({
                "office_id": office_id,
                "servidor_id": servidor_id,
                "cpf_partial": cpf_partial,
                "name": name,
                "org": org,
                "salary": salary,
            })
        self.offices = deduplicate_rows(offices, ["office_id"])

        amendments: list[dict[str, Any]] = []
        for _, row in self._raw_emendas.iterrows():
            codigo = str(row.get("codigo_autor", "")).strip()
            nome = normalize_name(str(row["nome_autor"]))
            author_key = codigo if codigo else nome.replace(" ", "_")

            amendments.append({
                "amendment_id": f"{author_key}_{normalize_name(str(row['objeto']))}",
                "author_key": author_key,
                "name": nome,
                "object": normalize_name(str(row["objeto"])),
                "value": _parse_brl(str(row["valor"])),
            })
        self.amendments = deduplicate_rows(amendments, ["amendment_id"])

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.contracts:
            loader.load_nodes(
                "Contract",
                [
                    {
                        "contract_id": c["contract_id"],
                        "object": c["object"],
                        "value": c["value"],
                        "contracting_org": c["contracting_org"],
                        "date": c["date"],
                    }
                    for c in self.contracts
                ],
                key_field="contract_id",
            )
            # Ensure Company nodes exist for contracted companies
            companies = deduplicate_rows(
                [{"cnpj": c["cnpj"], "razao_social": c["razao_social"]} for c in self.contracts],
                ["cnpj"],
            )
            loader.load_nodes("Company", companies, key_field="cnpj")

            # VENCEU: Company -> Contract
            loader.load_relationships(
                rel_type="VENCEU",
                rows=[
                    {"source_key": c["cnpj"], "target_key": c["contract_id"]}
                    for c in self.contracts
                ],
                source_label="Company",
                source_key="cnpj",
                target_label="Contract",
                target_key="contract_id",
            )

        if self.offices:
            # PublicOffice nodes — keyed on office_id (hash of cpf_partial+name+org)
            po_query = (
                "UNWIND $rows AS row "
                "MERGE (po:PublicOffice {office_id: row.office_id}) "
                "SET po.cpf_partial = row.cpf_partial, po.name = row.name, "
                "po.org = row.org, po.salary = row.salary"
            )
            loader.run_query(po_query, self.offices)

            # Person nodes — keyed on servidor_id (hash of cpf_partial+name)
            # DO NOT set cpf — would conflict with uniqueness constraint
            persons = deduplicate_rows(
                [
                    {
                        "servidor_id": o["servidor_id"],
                        "cpf_partial": o["cpf_partial"],
                        "name": o["name"],
                    }
                    for o in self.offices
                ],
                ["servidor_id"],
            )
            person_query = (
                "UNWIND $rows AS row "
                "MERGE (p:Person {servidor_id: row.servidor_id}) "
                "SET p.cpf_partial = row.cpf_partial, p.name = row.name, "
                "p.source = 'portal_transparencia'"
            )
            loader.run_query(person_query, persons)

            # RECEBEU_SALARIO: Person -> PublicOffice
            rel_query = (
                "UNWIND $rows AS row "
                "MATCH (p:Person {servidor_id: row.servidor_id}) "
                "MATCH (po:PublicOffice {office_id: row.office_id}) "
                "MERGE (p)-[:RECEBEU_SALARIO]->(po)"
            )
            loader.run_query(
                rel_query,
                [
                    {"servidor_id": o["servidor_id"], "office_id": o["office_id"]}
                    for o in self.offices
                ],
            )

        if self.amendments:
            # Amendment nodes — each emenda is its own entity
            loader.load_nodes(
                "Amendment",
                [
                    {
                        "amendment_id": a["amendment_id"],
                        "object": a["object"],
                        "value": a["value"],
                    }
                    for a in self.amendments
                ],
                key_field="amendment_id",
            )

            # Person nodes for amendment authors (keyed by author_key).
            # Entity resolution links these to TSE candidates later.
            persons = deduplicate_rows(
                [{"name": a["name"], "author_key": a["author_key"]} for a in self.amendments],
                ["author_key"],
            )
            loader.load_nodes("Person", persons, key_field="author_key")

            # AUTOR_EMENDA: Person -> Amendment
            loader.load_relationships(
                rel_type="AUTOR_EMENDA",
                rows=[
                    {"source_key": a["author_key"], "target_key": a["amendment_id"]}
                    for a in self.amendments
                ],
                source_label="Person",
                source_key="author_key",
                target_label="Amendment",
                target_key="amendment_id",
            )
