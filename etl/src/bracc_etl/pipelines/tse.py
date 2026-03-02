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
    format_cpf,
    normalize_name,
    strip_document,
)

logger = logging.getLogger(__name__)

# TSE 2024 masks ALL candidate CPFs as "-4". After strip_document → "4",
# format_cpf → "4" — every candidate MERGEs into one ghost node.
# We use SQ_CANDIDATO (unique sequential ID per candidate per election) instead.
_MASKED_CPF_SENTINEL = "-4"


class TSEPipeline(Pipeline):
    """Electoral data pipeline — candidates and campaign donations."""

    name = "tse"
    source_id = "tribunal_superior_eleitoral"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self.candidates: list[dict[str, Any]] = []
        self.donations: list[dict[str, Any]] = []
        self.elections: list[dict[str, Any]] = []

    def extract(self) -> None:
        tse_dir = Path(self.data_dir) / "tse"
        if not tse_dir.exists():
            logger.warning("[%s] Data directory not found: %s", self.name, tse_dir)
            self._raw_candidatos = pd.DataFrame()
            self._raw_doacoes = pd.DataFrame()
            return
        candidatos_path = tse_dir / "candidatos.csv"
        doacoes_path = tse_dir / "doacoes.csv"
        if not candidatos_path.exists() or not doacoes_path.exists():
            logger.warning("[%s] Required CSV files not found in %s", self.name, tse_dir)
            self._raw_candidatos = pd.DataFrame()
            self._raw_doacoes = pd.DataFrame()
            return
        self._raw_candidatos = pd.read_csv(
            candidatos_path, encoding="latin-1", dtype=str,
            nrows=self.limit,
        )
        self._raw_doacoes = pd.read_csv(
            doacoes_path, encoding="latin-1", dtype=str,
            nrows=self.limit,
        )

    def transform(self) -> None:
        self._transform_candidates()
        self._transform_donations()

    def _transform_candidates(self) -> None:
        candidates: list[dict[str, Any]] = []
        elections: list[dict[str, Any]] = []

        for _, row in self._raw_candidatos.iterrows():
            sq = str(row["sq_candidato"]).strip()
            raw_cpf = str(row["cpf"]).strip()
            name = normalize_name(str(row["nome"]))
            ano = int(row["ano"])
            cargo = normalize_name(str(row["cargo"]))
            uf = str(row["uf"]).strip().upper()
            municipio = normalize_name(str(row.get("municipio", "")))
            partido = str(row.get("partido", "")).strip().upper()

            # Only store CPF if it's a real value (not the TSE "-4" mask)
            cpf = None
            if raw_cpf != _MASKED_CPF_SENTINEL:
                cpf = format_cpf(strip_document(raw_cpf))

            candidate: dict[str, Any] = {
                "sq_candidato": sq,
                "name": name,
                "partido": partido,
                "uf": uf,
            }
            if cpf:
                candidate["cpf"] = cpf

            candidates.append(candidate)
            elections.append({
                "year": ano,
                "cargo": cargo,
                "uf": uf,
                "municipio": municipio,
                "candidate_sq": sq,
            })

        self.candidates = deduplicate_rows(candidates, ["sq_candidato"])
        self.elections = deduplicate_rows(
            elections, ["year", "cargo", "uf", "municipio", "candidate_sq"]
        )

    def _transform_donations(self) -> None:
        donations: list[dict[str, Any]] = []

        for _, row in self._raw_doacoes.iterrows():
            candidate_sq = str(row["sq_candidato"]).strip()
            donor_doc = strip_document(str(row["cpf_cnpj_doador"]))
            donor_name = normalize_name(str(row["nome_doador"]))
            valor = float(str(row["valor"]).replace(",", "."))
            ano = int(row["ano"])

            is_company = len(donor_doc) == 14
            donor_doc_fmt = format_cnpj(donor_doc)
            if not is_company:
                donor_doc_fmt = format_cpf(donor_doc)

            donations.append({
                "candidate_sq": candidate_sq,
                "donor_doc": donor_doc_fmt,
                "donor_name": donor_name,
                "donor_is_company": is_company,
                "valor": valor,
                "year": ano,
            })

        self.donations = donations

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        # Split candidates: CPF-keyed (dedup by CPF) vs sq_candidato-only
        cpf_candidates = [c for c in self.candidates if c.get("cpf")]
        nocpf_candidates = [c for c in self.candidates if not c.get("cpf")]

        # Merge by CPF, also store sq_candidato as a list for cross-referencing
        if cpf_candidates:
            cpf_deduped = deduplicate_rows(cpf_candidates, ["cpf"])
            loader.load_nodes("Person", cpf_deduped, key_field="cpf")

        # For candidates without CPF, merge by sq_candidato
        if nocpf_candidates:
            loader.load_nodes("Person", nocpf_candidates, key_field="sq_candidato")

        # Build sq_candidato→cpf lookup for linking
        sq_to_cpf: dict[str, str] = {}
        for c in self.candidates:
            if c.get("cpf"):
                sq_to_cpf[c["sq_candidato"]] = c["cpf"]

        # Map sq_candidato to Person node via Cypher SET for CANDIDATO_EM linking
        sq_cpf_rows = [{"sq": sq, "cpf": cpf} for sq, cpf in sq_to_cpf.items()]
        if sq_cpf_rows:
            loader.run_query(
                "UNWIND $rows AS row "
                "MATCH (p:Person {cpf: row.cpf}) "
                "SET p.sq_candidato = row.sq",
                sq_cpf_rows,
            )

        # Election nodes
        election_nodes = deduplicate_rows(
            [
                {"year": e["year"], "cargo": e["cargo"], "uf": e["uf"], "municipio": e["municipio"]}
                for e in self.elections
            ],
            ["year", "cargo", "uf", "municipio"],
        )
        if election_nodes:
            loader.run_query(
                "UNWIND $rows AS row "
                "MERGE (e:Election {year: row.year, cargo: row.cargo, "
                "uf: row.uf, municipio: row.municipio})",
                election_nodes,
            )

        # CANDIDATO_EM relationships — find person by CPF first, fallback to sq_candidato
        candidato_rels = []
        for e in self.elections:
            rel: dict[str, Any] = {
                "target_year": e["year"],
                "target_cargo": e["cargo"],
                "target_uf": e["uf"],
                "target_municipio": e["municipio"],
            }
            cpf = sq_to_cpf.get(e["candidate_sq"])
            if cpf:
                rel["cpf"] = cpf
                rel["sq"] = ""
            else:
                rel["cpf"] = ""
                rel["sq"] = e["candidate_sq"]
            candidato_rels.append(rel)

        if candidato_rels:
            loader.run_query(
                "UNWIND $rows AS row "
                "OPTIONAL MATCH (p1:Person {cpf: row.cpf}) WHERE row.cpf <> '' "
                "OPTIONAL MATCH (p2:Person {sq_candidato: row.sq}) WHERE row.sq <> '' "
                "WITH coalesce(p1, p2) AS p, row "
                "WHERE p IS NOT NULL "
                "MATCH (e:Election {year: row.target_year, cargo: row.target_cargo, "
                "uf: row.target_uf, municipio: row.target_municipio}) "
                "MERGE (p)-[:CANDIDATO_EM]->(e)",
                candidato_rels,
            )

        # Donor nodes and DOOU relationships
        person_donors = [
            {"cpf": d["donor_doc"], "name": d["donor_name"]}
            for d in self.donations
            if not d["donor_is_company"]
        ]
        company_donors = [
            {"cnpj": d["donor_doc"], "name": d["donor_name"], "razao_social": d["donor_name"]}
            for d in self.donations
            if d["donor_is_company"]
        ]

        if person_donors:
            loader.load_nodes("Person", deduplicate_rows(person_donors, ["cpf"]), key_field="cpf")
        if company_donors:
            loader.load_nodes(
                "Company", deduplicate_rows(company_donors, ["cnpj"]), key_field="cnpj"
            )

        # DOOU from Person donors → candidate
        person_donation_rels = []
        for d in self.donations:
            if d["donor_is_company"]:
                continue
            target_cpf = sq_to_cpf.get(d["candidate_sq"], "")
            person_donation_rels.append({
                "source_key": d["donor_doc"],
                "target_cpf": target_cpf,
                "target_sq": d["candidate_sq"] if not target_cpf else "",
                "valor": d["valor"],
                "year": d["year"],
            })
        if person_donation_rels:
            loader.run_query(
                "UNWIND $rows AS row "
                "MATCH (d:Person {cpf: row.source_key}) "
                "OPTIONAL MATCH (c1:Person {cpf: row.target_cpf}) WHERE row.target_cpf <> '' "
                "OPTIONAL MATCH (c2:Person {sq_candidato: row.target_sq}) "
                "WHERE row.target_sq <> '' "
                "WITH d, coalesce(c1, c2) AS c, row "
                "WHERE c IS NOT NULL "
                "MERGE (d)-[r:DOOU {year: row.year}]->(c) "
                "SET r.valor = row.valor",
                person_donation_rels,
            )

        # DOOU from Company donors → candidate
        company_donation_rels = []
        for d in self.donations:
            if not d["donor_is_company"]:
                continue
            target_cpf = sq_to_cpf.get(d["candidate_sq"], "")
            company_donation_rels.append({
                "source_key": d["donor_doc"],
                "target_cpf": target_cpf,
                "target_sq": d["candidate_sq"] if not target_cpf else "",
                "valor": d["valor"],
                "year": d["year"],
            })
        if company_donation_rels:
            loader.run_query(
                "UNWIND $rows AS row "
                "MATCH (d:Company {cnpj: row.source_key}) "
                "OPTIONAL MATCH (c1:Person {cpf: row.target_cpf}) WHERE row.target_cpf <> '' "
                "OPTIONAL MATCH (c2:Person {sq_candidato: row.target_sq}) "
                "WHERE row.target_sq <> '' "
                "WITH d, coalesce(c1, c2) AS c, row "
                "WHERE c IS NOT NULL "
                "MERGE (d)-[r:DOOU {year: row.year}]->(c) "
                "SET r.valor = row.valor",
                company_donation_rels,
            )
