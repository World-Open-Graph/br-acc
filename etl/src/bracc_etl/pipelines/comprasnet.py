"""ETL pipeline for PNCP (Portal Nacional de Contratações Públicas) data.

Ingests federal procurement contracts from the PNCP API JSON files.
Creates Contract nodes linked to Company nodes via VENCEU relationships.
Distinct from Transparência convênios — these are procurement contracts
(licitações, pregões, dispensas, inexigibilidades).
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any

from bracc_etl.base import Pipeline
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    cap_contract_value,
    deduplicate_rows,
    format_cnpj,
    normalize_name,
    strip_document,
)

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)

_ISO_DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")
_MAX_FUTURE_DAYS = 365


def _sanitize_iso_date(raw_value: str) -> str:
    """Return ISO date if valid and not absurdly in the future, else empty."""
    candidate = raw_value.strip()[:10]
    if not _ISO_DATE_RE.fullmatch(candidate):
        return ""
    try:
        parsed = date.fromisoformat(candidate)
    except ValueError:
        return ""
    if parsed > date.today() + timedelta(days=_MAX_FUTURE_DAYS):
        return ""
    return candidate

# Map PNCP modalidade IDs to short labels
_MODALIDADE_MAP: dict[int, str] = {
    1: "leilao_eletronico",
    3: "concurso",
    5: "concorrencia",
    6: "pregao_eletronico",
    8: "dispensa",
    9: "inexigibilidade",
    11: "pre_qualificacao",
}


class ComprasnetPipeline(Pipeline):
    """ETL pipeline for PNCP federal procurement contracts."""

    name = "comprasnet"
    source_id = "pncp"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size)
        self.contracts: list[dict[str, Any]] = []

    def extract(self) -> None:
        src_dir = Path(self.data_dir) / "comprasnet"
        json_files = sorted(src_dir.glob("*_contratos.json"))
        if not json_files:
            logger.warning("No PNCP JSON files found in %s", src_dir)
            return

        all_records: list[dict[str, Any]] = []
        for f in json_files:
            records = json.loads(f.read_text(encoding="utf-8"))
            all_records.extend(records)
            logger.info("  Loaded %d records from %s", len(records), f.name)

        logger.info("Total raw records: %d", len(all_records))
        self._raw_records = all_records

    def transform(self) -> None:
        if not hasattr(self, "_raw_records"):
            return

        contracts: list[dict[str, Any]] = []
        skipped_no_cnpj = 0
        skipped_no_value = 0

        for rec in self._raw_records:
            # Extract supplier CNPJ
            ni_fornecedor = str(rec.get("niFornecedor", "")).strip()
            cnpj_digits = strip_document(ni_fornecedor)

            # Only process companies (PJ with 14-digit CNPJ)
            tipo_pessoa = str(rec.get("tipoPessoa", "")).strip()
            if tipo_pessoa != "PJ" or len(cnpj_digits) != 14:
                skipped_no_cnpj += 1
                continue

            # Skip zero-value contracts
            valor = rec.get("valorGlobal") or rec.get("valorInicial") or 0
            if not valor or float(valor) <= 0:
                skipped_no_value += 1
                continue

            cnpj = format_cnpj(ni_fornecedor)

            # Build stable contract ID from PNCP control number
            numero_controle = str(
                rec.get("numeroControlePNCP", "")
            ).strip()
            if not numero_controle:
                # Fallback: compose from org CNPJ + sequence
                org_cnpj = strip_document(
                    str(rec.get("orgaoEntidade", {}).get("cnpj", ""))
                )
                seq = rec.get("sequencialContrato", "")
                ano = rec.get("anoContrato", "")
                numero_controle = f"{org_cnpj}-{seq}-{ano}"

            bid_reference = str(
                rec.get("numeroControlePncpCompra")
                or rec.get("numeroControlePNCPCompra")
                or ""
            ).strip()

            # Extract contracting org info
            org = rec.get("orgaoEntidade", {})
            org_name = normalize_name(
                str(org.get("razaoSocial", ""))
            )

            # Contract type (Empenho, Contrato, etc.)
            tipo_contrato = rec.get("tipoContrato", {})
            tipo_nome = str(tipo_contrato.get("nome", "")) if tipo_contrato else ""

            # Dates
            data_assinatura = _sanitize_iso_date(str(rec.get("dataAssinatura", "")))
            data_fim = _sanitize_iso_date(str(rec.get("dataVigenciaFim", "")))

            # Supplier name
            razao_social = normalize_name(
                str(rec.get("nomeRazaoSocialFornecedor", ""))
            )

            contracts.append({
                "contract_id": numero_controle,
                "bid_id": bid_reference,
                "object": normalize_name(
                    str(rec.get("objetoContrato", ""))
                ),
                "value": cap_contract_value(float(valor)),
                "contracting_org": org_name,
                "date": data_assinatura,
                "date_end": data_fim,
                "cnpj": cnpj,
                "razao_social": razao_social,
                "tipo_contrato": tipo_nome,
                "source": "comprasnet",
            })

        self.contracts = deduplicate_rows(contracts, ["contract_id"])

        logger.info(
            "Transformed: %d contracts (skipped %d no-CNPJ, %d zero-value)",
            len(self.contracts),
            skipped_no_cnpj,
            skipped_no_value,
        )

        if self.limit:
            self.contracts = self.contracts[: self.limit]

    def load(self) -> None:
        if not self.contracts:
            logger.warning("No contracts to load")
            return

        loader = Neo4jBatchLoader(self.driver)

        # Load Contract nodes (MERGE on contract_id to avoid duplicates)
        contract_nodes = [
            {
                "contract_id": c["contract_id"],
                "object": c["object"],
                "value": c["value"],
                "contracting_org": c["contracting_org"],
                "date": c["date"],
                "date_end": c["date_end"],
                "tipo_contrato": c["tipo_contrato"],
                "source": c["source"],
            }
            for c in self.contracts
        ]
        count = loader.load_nodes(
            "Contract", contract_nodes, key_field="contract_id",
        )
        logger.info("Loaded %d Contract nodes", count)

        # Ensure Company nodes exist for suppliers
        companies = deduplicate_rows(
            [
                {"cnpj": c["cnpj"], "razao_social": c["razao_social"]}
                for c in self.contracts
            ],
            ["cnpj"],
        )
        count = loader.load_nodes("Company", companies, key_field="cnpj")
        logger.info("Merged %d Company nodes", count)

        # VENCEU: Company -> Contract
        rels = [
            {"source_key": c["cnpj"], "target_key": c["contract_id"]}
            for c in self.contracts
        ]
        count = loader.load_relationships(
            rel_type="VENCEU",
            rows=rels,
            source_label="Company",
            source_key="cnpj",
            target_label="Contract",
            target_key="contract_id",
        )
        logger.info("Created %d VENCEU relationships", count)

        # REFERENTE_A: Contract -> Bid (deterministic PNCP linkage)
        contract_bid_rels = [
            {"source_key": c["contract_id"], "target_key": c["bid_id"]}
            for c in self.contracts
            if c.get("bid_id")
        ]
        count = loader.load_relationships(
            rel_type="REFERENTE_A",
            rows=contract_bid_rels,
            source_label="Contract",
            source_key="contract_id",
            target_label="Bid",
            target_key="bid_id",
        )
        logger.info("Created %d REFERENTE_A relationships", count)
