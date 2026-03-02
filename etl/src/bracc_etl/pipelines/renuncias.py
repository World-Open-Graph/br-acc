from __future__ import annotations

import hashlib
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


def _parse_brl(value: str) -> float | None:
    """Parse Brazilian currency format: 1.234.567,89 -> 1234567.89."""
    clean = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(clean)
    except (ValueError, TypeError):
        return None


class RenunciasPipeline(Pipeline):
    """ETL pipeline for Renúncias Fiscais (tax waivers/exemptions).

    Data source: Portal da Transparência CSV downloads.
    Loads TaxWaiver nodes linked to Company nodes by CNPJ.
    """

    name = "renuncias"
    source_id = "renuncias"

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
        self.waivers: list[dict[str, Any]] = []
        self.company_rels: list[dict[str, Any]] = []

    def extract(self) -> None:
        data_dir = Path(self.data_dir) / "renuncias"
        frames: list[pd.DataFrame] = []

        # Only process RenúnciasFiscais files (have amounts); skip
        # EmpresasHabilitadas and EmpresasImunesOuIsentas (no values).
        for csv_file in sorted(data_dir.glob("*.csv")):
            fname = csv_file.name
            if ("Ren" not in fname and "ren" not in fname) or "PorBen" in fname:
                continue
            df = pd.read_csv(
                csv_file,
                dtype=str,
                delimiter=";",
                encoding="latin-1",
                keep_default_na=False,
            )
            frames.append(df)

        if frames:
            self._raw = pd.concat(frames, ignore_index=True)
        else:
            self._raw = pd.DataFrame()

        if self.limit:
            self._raw = self._raw.head(self.limit)

        logger.info("Extracted %d renuncias records", len(self._raw))

    def transform(self) -> None:
        waivers: list[dict[str, Any]] = []
        company_rels: list[dict[str, Any]] = []

        for _, row in self._raw.iterrows():
            cnpj_raw = str(row.get("CNPJ", "")).strip().strip('"')
            digits = strip_document(cnpj_raw)

            if len(digits) != 14:
                continue

            cnpj_formatted = format_cnpj(cnpj_raw)
            name = normalize_name(str(
                row.get("Razão Social", row.get("Raz\xe3o Social", ""))
            ))
            tributo = str(row.get("Tributo", row.get("TRIBUTO", ""))).strip()
            tipo = str(
                row.get("Tipo Renúncia", row.get("Tipo Ren\xfancia", ""))
                or row.get("Benefício Fiscal", row.get("Benef\xedcio Fiscal", ""))
            ).strip()
            ano = str(
                row.get("Ano-calendário", row.get("Ano-calend\xe1rio", ""))
                or row.get("ANO", "")
            ).strip()

            valor_raw = str(
                row.get("Valor Renúncia Fiscal (R$)",
                         row.get("Valor Ren\xfancia Fiscal (R$)", "0"))
            )
            amount = _parse_brl(valor_raw)
            if amount is None or amount <= 0:
                continue

            id_source = f"{digits}_{ano}_{tributo}_{tipo}"
            waiver_id = hashlib.sha256(id_source.encode()).hexdigest()[:16]

            waivers.append({
                "waiver_id": waiver_id,
                "cnpj": cnpj_formatted,
                "beneficiary_name": name,
                "tax_type": tributo,
                "waiver_type": tipo,
                "year": ano,
                "amount": amount,
                "source": "renuncias_fiscais",
            })

            company_rels.append({
                "cnpj": cnpj_formatted,
                "waiver_id": waiver_id,
                "company_name": name,
            })

        self.waivers = deduplicate_rows(waivers, ["waiver_id"])
        self.company_rels = company_rels
        logger.info(
            "Transformed %d waivers, %d company links",
            len(self.waivers),
            len(self.company_rels),
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.waivers:
            loader.load_nodes("TaxWaiver", self.waivers, key_field="waiver_id")

        if self.company_rels:
            query = (
                "UNWIND $rows AS row "
                "MERGE (c:Company {cnpj: row.cnpj}) "
                "ON CREATE SET c.razao_social = row.company_name "
                "WITH c, row "
                "MATCH (w:TaxWaiver {waiver_id: row.waiver_id}) "
                "MERGE (c)-[:RECEBEU_RENUNCIA]->(w)"
            )
            loader.run_query_with_retry(query, self.company_rels)
