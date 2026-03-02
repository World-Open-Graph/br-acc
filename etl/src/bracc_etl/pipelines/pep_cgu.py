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
    format_cpf,
    normalize_name,
    parse_date,
    strip_document,
)

logger = logging.getLogger(__name__)

# Government CSV columns may appear in different cases.
# Map UPPER CASE (as downloaded) -> canonical mixed-case for the pipeline.
_COLUMN_ALIASES: dict[str, str] = {
    # Canonical (space-delimited with accents)
    "CPF": "CPF",
    "NOME": "Nome",
    "SIGLA FUNCAO": "Sigla Função",
    "SIGLA FUNÇÃO": "Sigla Função",
    "DESCRICAO FUNCAO": "Descrição Função",
    "DESCRIÇÃO FUNÇÃO": "Descrição Função",
    "NIVEL FUNCAO": "Nível Função",
    "NÍVEL FUNÇÃO": "Nível Função",
    "NOME ORGAO": "Nome Órgão",
    "NOME ÓRGÃO": "Nome Órgão",
    "DATA INICIO EXERCICIO": "Data Início Exercício",
    "DATA INÍCIO EXERCÍCIO": "Data Início Exercício",
    "DATA FIM EXERCICIO": "Data Fim Exercício",
    "DATA FIM EXERCÍCIO": "Data Fim Exercício",
    "DATA FIM CARENCIA": "Data Fim Carência",
    "DATA FIM CARÊNCIA": "Data Fim Carência",
    # Underscore-delimited format (government CSV as of 2025)
    "NOME_PEP": "Nome",
    "SIGLA_FUNCAO": "Sigla Função",
    "SIGLA_FUNÇÃO": "Sigla Função",
    "DESCRICAO_FUNCAO": "Descrição Função",
    "DESCRIÇÃO_FUNÇÃO": "Descrição Função",
    "NIVEL_FUNCAO": "Nível Função",
    "NÍVEL_FUNÇÃO": "Nível Função",
    "NOME_ORGAO": "Nome Órgão",
    "NOME_ÓRGÃO": "Nome Órgão",
    "DATA_INICIO_EXERCICIO": "Data Início Exercício",
    "DATA_INÍCIO_EXERCÍCIO": "Data Início Exercício",
    "DATA_FIM_EXERCICIO": "Data Fim Exercício",
    "DATA_FIM_EXERCÍCIO": "Data Fim Exercício",
    "DATA_FIM_CARENCIA": "Data Fim Carência",
    "DATA_FIM_CARÊNCIA": "Data Fim Carência",
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names: try exact match, then case-insensitive alias."""
    rename_map: dict[str, str] = {}
    for col in df.columns:
        col_upper = col.strip().upper()
        if col_upper in _COLUMN_ALIASES:
            rename_map[col] = _COLUMN_ALIASES[col_upper]
        elif col.strip() in _COLUMN_ALIASES.values():
            rename_map[col] = col.strip()
    return df.rename(columns=rename_map)


class PepCguPipeline(Pipeline):
    """ETL pipeline for CGU PEP List (official PEP registry)."""

    name = "pep_cgu"
    source_id = "cgu_pep"

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
        self.pep_records: list[dict[str, Any]] = []
        self.person_links: list[dict[str, Any]] = []

    def extract(self) -> None:
        pep_dir = Path(self.data_dir) / "pep_cgu"
        csv_path = pep_dir / "pep.csv"
        if not csv_path.exists():
            msg = f"PEP CSV not found: {csv_path}"
            raise FileNotFoundError(msg)
        self._raw = pd.read_csv(
            csv_path,
            dtype=str,
            delimiter=";",
            encoding="latin-1",
            keep_default_na=False,
        )
        self._raw = _normalize_columns(self._raw)
        logger.info("[pep_cgu] Extracted %d PEP records", len(self._raw))

    def transform(self) -> None:
        records: list[dict[str, Any]] = []
        links: list[dict[str, Any]] = []

        for idx, row in self._raw.iterrows():
            cpf_raw = str(row.get("CPF", "")).strip()
            digits = strip_document(cpf_raw)

            nome = normalize_name(str(row.get("Nome", "")))
            if not nome:
                continue

            # Use full CPF when available, else keep masked format
            cpf_formatted = format_cpf(cpf_raw) if len(digits) == 11 else cpf_raw

            sigla = str(row.get("Sigla Função", "")).strip()
            descricao = str(row.get("Descrição Função", "")).strip()
            nivel = str(row.get("Nível Função", "")).strip()
            orgao = str(row.get("Nome Órgão", "")).strip()
            data_inicio = parse_date(str(row.get("Data Início Exercício", "")))
            data_fim = parse_date(str(row.get("Data Fim Exercício", "")))
            data_carencia = parse_date(str(row.get("Data Fim Carência", "")))

            pep_id = f"pep_{digits}_{idx}"

            records.append({
                "pep_id": pep_id,
                "cpf": cpf_formatted,
                "name": nome,
                "role": sigla,
                "role_description": descricao,
                "level": nivel,
                "org": orgao,
                "start_date": data_inicio,
                "end_date": data_fim,
                "grace_end_date": data_carencia,
                "source": "cgu_pep",
            })

            # Only link to Person nodes when we have a full CPF
            if len(digits) == 11:
                links.append({
                    "source_key": cpf_formatted,
                    "target_key": pep_id,
                })

            if self.limit and len(records) >= self.limit:
                break

        self.pep_records = deduplicate_rows(records, ["pep_id"])
        self.person_links = links
        logger.info(
            "[pep_cgu] Transformed %d PEP records, %d person links",
            len(self.pep_records),
            len(self.person_links),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.pep_records:
            loaded = loader.load_nodes("PEPRecord", self.pep_records, key_field="pep_id")
            logger.info("[pep_cgu] Loaded %d PEPRecord nodes", loaded)

        if self.person_links:
            query = (
                "UNWIND $rows AS row "
                "MERGE (p:Person {cpf: row.source_key}) "
                "ON CREATE SET p.name = '' "
                "WITH p, row "
                "MATCH (pep:PEPRecord {pep_id: row.target_key}) "
                "MERGE (p)-[:PEP_REGISTRADA]->(pep)"
            )
            loaded = loader.run_query_with_retry(query, self.person_links)
            logger.info("[pep_cgu] Loaded %d PEP_REGISTRADA relationships", loaded)
