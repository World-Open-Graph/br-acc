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
from bracc_etl.transforms import deduplicate_rows

logger = logging.getLogger(__name__)

# CAGED tipo_movimentacao: 1 = admission, 2 = dismissal
_MOVEMENT_TYPES: dict[str, str] = {
    "1": "admissao",
    "2": "desligamento",
    "3": "desligamento",  # some codes map to sub-types
}

# Chunk size for streaming CSV reads (100K rows per chunk)
_READ_CHUNK_SIZE = 100_000


def _generate_stats_id(
    year: str,
    month: str,
    uf: str,
    municipality_code: str,
    cnae_subclass: str,
    cbo_code: str,
    movement_type: str,
) -> str:
    """Deterministic id for aggregate CAGED buckets."""
    raw = "|".join([
        year,
        month.zfill(2),
        uf,
        municipality_code,
        cnae_subclass,
        cbo_code,
        movement_type,
    ])
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _build_movement_date(ano: str, mes: str) -> str:
    """Build YYYY-MM date string from year and month columns."""
    month = mes.zfill(2)
    return f"{ano}-{month}"


def _parse_salary(raw: str) -> float | None:
    """Parse salary value to float. Handles both dot-decimal and comma-decimal."""
    cleaned = raw.strip().replace("\u2212", "-")  # unicode minus
    if not cleaned or cleaned == "-":
        return None
    # Brazilian format: 1.500,50 -> dot as thousands, comma as decimal
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        val = float(cleaned)
        return val if val >= 0 else None
    except ValueError:
        return None


class CagedPipeline(Pipeline):
    """ETL pipeline for CAGED labor movement data (aggregate-only mode).

    Public CAGED data is treated as aggregate labor signal. This pipeline
    intentionally avoids Person/Company linkage and only writes LaborStats nodes.
    """

    name = "caged"
    source_id = "caged"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        **kwargs: Any,
    ) -> None:
        super().__init__(driver, data_dir, limit=limit, chunk_size=chunk_size, **kwargs)
        self._csv_files: list[Path] = []

    def extract(self) -> None:
        caged_dir = Path(self.data_dir) / "caged"
        self._csv_files = sorted(caged_dir.glob("caged_*.csv"))
        if not self._csv_files:
            logger.warning("No caged_*.csv files found in %s", caged_dir)

    def transform(self) -> None:
        pass  # Transform happens per chunk in load()

    def _transform_chunk(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Transform a DataFrame chunk into aggregate LaborStats rows."""
        if df.empty:
            return []

        work = df.copy()

        def _col(name: str) -> pd.Series[Any]:
            if name in work.columns:
                return work[name]
            return pd.Series([""] * len(work), index=work.index, dtype="string")

        work["ano"] = _col("ano").astype(str).str.strip()
        work["mes"] = _col("mes").astype(str).str.strip()
        work = work[(work["ano"] != "") & (work["mes"] != "")]
        if work.empty:
            return []

        work["sigla_uf"] = _col("sigla_uf").astype(str).str.strip()
        work["id_municipio"] = _col("id_municipio").astype(str).str.strip()
        work["cnae_2_subclasse"] = _col("cnae_2_subclasse").astype(str).str.strip()
        work["cbo_2002"] = _col("cbo_2002").astype(str).str.strip()
        work["movement_type"] = _col("tipo_movimentacao").astype(str).str.strip().map(
            lambda v: _MOVEMENT_TYPES.get(v, v),
        )
        work["salary"] = _col("salario_mensal").astype(str).map(_parse_salary)
        work["movement_count"] = 1
        work["admissions"] = (work["movement_type"] == "admissao").astype(int)
        work["dismissals"] = (work["movement_type"] == "desligamento").astype(int)

        group_cols = [
            "ano",
            "mes",
            "sigla_uf",
            "id_municipio",
            "cnae_2_subclasse",
            "cbo_2002",
            "movement_type",
        ]
        grouped = (
            work.groupby(group_cols, dropna=False)
            .agg(
                total_movements=("movement_count", "sum"),
                admissions=("admissions", "sum"),
                dismissals=("dismissals", "sum"),
                avg_salary=("salary", "mean"),
            )
            .reset_index()
        )

        rows: list[dict[str, Any]] = []
        for _, row in grouped.iterrows():
            year = str(row["ano"]).strip()
            month = str(row["mes"]).strip().zfill(2)
            uf = str(row["sigla_uf"]).strip()
            municipality_code = str(row["id_municipio"]).strip()
            cnae_subclass = str(row["cnae_2_subclasse"]).strip()
            cbo_code = str(row["cbo_2002"]).strip()
            movement_type = str(row["movement_type"]).strip()

            stats_id = _generate_stats_id(
                year,
                month,
                uf,
                municipality_code,
                cnae_subclass,
                cbo_code,
                movement_type,
            )
            admissions = int(row["admissions"])
            dismissals = int(row["dismissals"])

            item: dict[str, Any] = {
                "stats_id": stats_id,
                "year": year,
                "month": month,
                "movement_date": _build_movement_date(year, month),
                "movement_type": movement_type,
                "uf": uf,
                "municipality_code": municipality_code,
                "cnae_subclass": cnae_subclass,
                "cbo_code": cbo_code,
                "total_movements": int(row["total_movements"]),
                "admissions": admissions,
                "dismissals": dismissals,
                "net_balance": admissions - dismissals,
                "identity_quality": "aggregate",
                "source": "caged",
            }
            if pd.notna(row["avg_salary"]):
                item["avg_salary"] = float(row["avg_salary"])
            rows.append(item)

        return deduplicate_rows(rows, ["stats_id"])

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        for csv_file in self._csv_files:
            logger.info("Processing %s ...", csv_file.name)
            reader = pd.read_csv(
                csv_file,
                dtype=str,
                keep_default_na=False,
                chunksize=_READ_CHUNK_SIZE,
                nrows=self.limit,
            )
            for chunk in reader:
                stats_rows = self._transform_chunk(chunk)
                if stats_rows:
                    loader.load_nodes("LaborStats", stats_rows, key_field="stats_id")
            logger.info("Finished %s", csv_file.name)
