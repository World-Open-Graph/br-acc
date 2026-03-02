from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader

logger = logging.getLogger(__name__)

# UF IBGE numeric code -> state abbreviation
UF_CODE_MAP = {
    "11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA",
    "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
    "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE",
    "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
    "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT",
    "52": "GO", "53": "DF",
}


class RaisPipeline(Pipeline):
    """ETL pipeline for RAIS (Relacao Anual de Informacoes Sociais) labor data.

    RAIS public microdata is de-identified (no CNPJ/CPF). This pipeline
    aggregates establishment-level data by CNAE subclass + UF into
    LaborStats nodes. These are sector-level reference data (not entity-level),
    joined to Company nodes at query time via CNAE prefix matching.

    Data source: ftp://ftp.mtps.gov.br/pdet/microdados/RAIS/
    """

    name = "rais"
    source_id = "rais_mte"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self.labor_stats: list[dict[str, Any]] = []

    def extract(self) -> None:
        """Read RAIS establishment microdata and aggregate by CNAE + UF.

        If a pre-aggregated CSV exists, use it directly. Otherwise,
        aggregate from the raw .txt file.
        """
        rais_dir = Path(self.data_dir) / "rais"

        # Try pre-aggregated CSV first
        agg_path = rais_dir / "rais_2022_aggregated.csv"
        if agg_path.exists():
            logger.info("Reading pre-aggregated RAIS data from %s", agg_path.name)
            df = pd.read_csv(agg_path, dtype=str, keep_default_na=False)
            self._from_aggregated(df)
            return

        # Otherwise aggregate from raw microdata
        raw_files = sorted(rais_dir.glob("RAIS_ESTAB_PUB*.txt*"))
        if not raw_files:
            logger.warning("No RAIS data files found in %s", rais_dir)
            return

        self._aggregate_raw(raw_files[0])

    def _from_aggregated(self, df: pd.DataFrame) -> None:
        """Load from pre-aggregated CSV."""
        rows: list[dict[str, Any]] = []
        for _, row in df.iterrows():
            cnae = str(row.get("cnae_subclass", "")).strip()
            uf = str(row.get("uf", "")).strip()
            if not cnae or not uf:
                continue
            rows.append({
                "stats_id": f"rais_2022_{cnae}_{uf}",
                "cnae_subclass": cnae,
                "uf": uf,
                "year": 2022,
                "establishment_count": int(row.get("establishment_count", 0)),
                "total_employees": int(row.get("total_employees", 0)),
                "total_clt": int(row.get("total_clt", 0)),
                "total_statutory": int(row.get("total_statutory", 0)),
                "avg_employees": float(row.get("avg_employees", 0)),
                "source": "rais_mte",
            })
        self.labor_stats = rows
        logger.info("Loaded %d aggregated RAIS records", len(rows))

    def _aggregate_raw(self, raw_path: Path) -> None:
        """Aggregate raw RAIS microdata file by CNAE + UF."""
        logger.info("Aggregating raw RAIS data from %s", raw_path.name)

        agg: dict[tuple[str, str], dict[str, Any]] = {}
        total_rows = 0

        chunks = pd.read_csv(
            raw_path,
            sep=";",
            encoding="latin-1",
            dtype=str,
            keep_default_na=False,
            usecols=[
                "CNAE 2.0 Subclasse", "Qtd Vínculos Ativos",
                "Qtd Vínculos CLT", "Qtd Vínculos Estatutários", "UF",
            ],
            chunksize=self.chunk_size,
        )

        for chunk in chunks:
            total_rows += len(chunk)
            for _, row in chunk.iterrows():
                cnae = str(row["CNAE 2.0 Subclasse"]).strip()
                uf_code = str(row["UF"]).strip()
                if not cnae or cnae == "0":
                    continue
                uf = UF_CODE_MAP.get(uf_code, uf_code)
                vinculos = int(str(row["Qtd Vínculos Ativos"]).strip() or "0")
                vinculos_clt = int(str(row["Qtd Vínculos CLT"]).strip() or "0")
                vinculos_estat = int(
                    str(row["Qtd Vínculos Estatutários"]).strip() or "0"
                )
                key = (cnae, uf)
                if key not in agg:
                    agg[key] = {
                        "cnae_subclass": cnae,
                        "uf": uf,
                        "establishment_count": 0,
                        "total_employees": 0,
                        "total_clt": 0,
                        "total_statutory": 0,
                    }
                agg[key]["establishment_count"] += 1
                agg[key]["total_employees"] += vinculos
                agg[key]["total_clt"] += vinculos_clt
                agg[key]["total_statutory"] += vinculos_estat
            logger.info("  Processed %d rows", total_rows)

        rows: list[dict[str, Any]] = []
        for v in agg.values():
            est_count = v["establishment_count"]
            rows.append({
                "stats_id": f"rais_2022_{v['cnae_subclass']}_{v['uf']}",
                "cnae_subclass": v["cnae_subclass"],
                "uf": v["uf"],
                "year": 2022,
                "establishment_count": est_count,
                "total_employees": v["total_employees"],
                "total_clt": v["total_clt"],
                "total_statutory": v["total_statutory"],
                "avg_employees": round(v["total_employees"] / est_count, 1)
                if est_count > 0
                else 0,
                "source": "rais_mte",
            })

        self.labor_stats = rows
        logger.info(
            "Aggregated %d rows into %d CNAE+UF stats from %d raw records",
            total_rows, len(rows), total_rows,
        )

    def transform(self) -> None:
        """No additional transform needed — aggregation is done in extract."""

    def load(self) -> None:
        """Load LaborStats nodes (sector reference data, no relationships)."""
        loader = Neo4jBatchLoader(self.driver)

        if not self.labor_stats:
            logger.warning("No RAIS labor stats to load")
            return

        # Load LaborStats nodes
        logger.info("Loading %d LaborStats nodes...", len(self.labor_stats))
        loader.load_nodes("LaborStats", self.labor_stats, key_field="stats_id")

        # Create index for efficient matching
        with self.driver.session(database=self.neo4j_database) as session:
            session.run(
                "CREATE INDEX labor_stats_cnae IF NOT EXISTS "
                "FOR (l:LaborStats) ON (l.cnae_subclass)"
            )
            session.run(
                "CREATE INDEX labor_stats_uf IF NOT EXISTS "
                "FOR (l:LaborStats) ON (l.uf)"
            )

        logger.info("LaborStats nodes loaded. Indexes created.")
        logger.info(
            "Total: %d stats covering %d establishments, %d employees",
            len(self.labor_stats),
            sum(s["establishment_count"] for s in self.labor_stats),
            sum(s["total_employees"] for s in self.labor_stats),
        )
