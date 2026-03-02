from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pandas as pd

from bracc_etl.base import Pipeline

if TYPE_CHECKING:
    from neo4j import Driver
from bracc_etl.loader import Neo4jBatchLoader
from bracc_etl.transforms import (
    classify_document,
    deduplicate_rows,
    format_cnpj,
    format_cpf,
    normalize_name,
    parse_date,
    strip_document,
)

logger = logging.getLogger(__name__)

# Receita Federal CSV column names (files have no headers)
EMPRESAS_COLS = [
    "cnpj_basico",
    "razao_social",
    "natureza_juridica",
    "qualificacao_responsavel",
    "capital_social",
    "porte_empresa",
    "ente_federativo",
]

SOCIOS_COLS = [
    "cnpj_basico",
    "identificador_socio",
    "nome_socio",
    "cpf_cnpj_socio",
    "qualificacao_socio",
    "data_entrada",
    "pais",
    "representante_legal",
    "nome_representante",
    "qualificacao_representante",
    "faixa_etaria",
]

ESTABELECIMENTOS_COLS = [
    "cnpj_basico",
    "cnpj_ordem",
    "cnpj_dv",
    "identificador_matriz_filial",
    "nome_fantasia",
    "situacao_cadastral",
    "data_situacao_cadastral",
    "motivo_situacao_cadastral",
    "nome_cidade_exterior",
    "pais",
    "data_inicio_atividade",
    "cnae_principal",
    "cnae_secundaria",
    "tipo_logradouro",
    "logradouro",
    "numero",
    "complemento",
    "bairro",
    "cep",
    "uf",
    "municipio",
    "ddd1",
    "telefone1",
    "ddd2",
    "telefone2",
    "ddd_fax",
    "fax",
    "email",
    "situacao_especial",
    "data_situacao_especial",
]

# Reference tables: 2-column CSVs (codigo, descricao)
REFERENCE_TABLES = [
    "Naturezas",
    "Qualificacoes",
    "Cnaes",
    "Municipios",
    "Paises",
    "Motivos",
]

# Base dos Dados (BigQuery) -> Receita Federal column name mapping.
# BQ renames many RF columns. These maps translate BQ names back to RF names
# so the transform step can use a single code path.
BQ_EMPRESAS_RENAME = {
    "porte": "porte_empresa",
}
BQ_EMPRESAS_DROP = {"ano", "mes", "data"}

BQ_SOCIOS_RENAME = {
    "tipo": "identificador_socio",
    "nome": "nome_socio",
    "documento": "cpf_cnpj_socio",
    "qualificacao": "qualificacao_socio",
    "data_entrada_sociedade": "data_entrada",
    "id_pais": "pais",
    "cpf_representante_legal": "representante_legal",
    "nome_representante_legal": "nome_representante",
    "qualificacao_representante_legal": "qualificacao_representante",
}
BQ_SOCIOS_DROP = {"ano", "mes", "data"}

BQ_ESTABELECIMENTOS_RENAME = {
    "id_pais": "pais",
    "cnae_fiscal_principal": "cnae_principal",
    "cnae_fiscal_secundaria": "cnae_secundaria",
    "sigla_uf": "uf",
    "id_municipio": "municipio",
    "ddd_1": "ddd1",
    "telefone_1": "telefone1",
    "ddd_2": "ddd2",
    "telefone_2": "telefone2",
}
BQ_ESTABELECIMENTOS_DROP = {"ano", "mes", "data", "cnpj", "id_municipio_rf"}
BQ_EMPRESAS_DROP_HISTORY: set[str] = set()
BQ_SOCIOS_DROP_HISTORY: set[str] = set()
BQ_ESTABELECIMENTOS_DROP_HISTORY: set[str] = {"cnpj", "id_municipio_rf"}


class _BQChunkAdapter:
    """Wraps a pandas TextFileReader to rename/drop columns on each chunk.

    Makes BQ-format CSVs yield chunks with RF-compatible column names,
    so the same transform methods work for both formats.
    """

    def __init__(
        self,
        reader: pd.io.parsers.readers.TextFileReader,
        rename_map: dict[str, str],
        drop_cols: set[str],
    ) -> None:
        self._reader = reader
        self._rename_map = rename_map
        self._drop_cols = drop_cols

    def __iter__(self) -> _BQChunkAdapter:
        return self

    def __next__(self) -> pd.DataFrame:
        chunk = next(self._reader)
        chunk = chunk.drop(columns=[c for c in self._drop_cols if c in chunk.columns])
        return chunk.rename(columns=self._rename_map)


def parse_capital_social(value: str) -> float:
    """Parse Receita Federal capital_social format.

    RF uses comma as decimal separator: '750000000,00' -> 750000000.00
    Simple format uses plain numbers: '7500000000' -> 7500000000.0
    """
    if not value or value.strip() == "":
        return 0.0
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _make_partner_id(
    name: str,
    doc_raw: str,
    tipo_socio: str,
) -> str:
    """Build stable ID for partial/invalid partner identities."""
    doc_digits = strip_document(doc_raw)
    raw = f"{name}|{doc_digits}|{doc_raw.strip()}|{tipo_socio}|receita_federal"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _make_membership_id(
    source_key: str,
    target_key: str,
    tipo_socio: str,
    qualificacao: str,
    snapshot_date: str,
    data_entrada: str,
) -> str:
    raw = (
        f"{source_key}|{target_key}|{tipo_socio}|{qualificacao}|"
        f"{snapshot_date}|{data_entrada}|receita_federal"
    )
    return hashlib.sha256(raw.encode()).hexdigest()[:24]


class CNPJPipeline(Pipeline):
    """ETL pipeline for Receita Federal CNPJ open data.

    Supports two data formats:
    - Real Receita Federal: headerless CSVs (`;` delimiter, latin-1) with multiple files
    - Simple CSV: header-based CSVs for testing/development
    """

    name = "cnpj"
    source_id = "receita_federal"

    def __init__(
        self,
        driver: Driver,
        data_dir: str = "./data",
        limit: int | None = None,
        chunk_size: int = 50_000,
        history: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            driver, data_dir, limit=limit, chunk_size=chunk_size, history=history, **kwargs,
        )
        self.run_id = f"cnpj-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}"
        self._raw_empresas: pd.DataFrame = pd.DataFrame()
        self._raw_socios: pd.DataFrame = pd.DataFrame()
        self._raw_estabelecimentos: pd.DataFrame = pd.DataFrame()
        self._reference_tables: dict[str, dict[str, str]] = {}
        # basico -> (cnpj_full, cnae_principal, uf, municipio)
        self._estab_lookup: dict[str, tuple[str, str, str, str]] = {}
        self.companies: list[dict[str, Any]] = []
        # PF partners with strong CPF identity
        self.partners: list[dict[str, Any]] = []
        # PF partners with masked/partial/invalid docs
        self.partial_partners: list[dict[str, Any]] = []
        # Person -> Company
        self.relationships: list[dict[str, Any]] = []
        # Partner -> Company
        self.partner_relationships: list[dict[str, Any]] = []
        # Company -> Company
        self.pj_relationships: list[dict[str, Any]] = []
        # Historical socio snapshots
        self.snapshot_relationships: list[dict[str, Any]] = []

    # --- Reference tables ---

    def _load_reference_tables(self) -> None:
        """Load reference lookup tables (naturezas, qualificacoes, etc.)."""
        ref_dir = Path(self.data_dir) / "cnpj" / "reference"
        if not ref_dir.exists():
            return

        for table_name in REFERENCE_TABLES:
            files = list(ref_dir.glob(f"*{table_name}*"))
            if not files:
                continue
            try:
                df = pd.read_csv(
                    files[0],
                    sep=";",
                    encoding="latin-1",
                    header=None,
                    names=["codigo", "descricao"],
                    dtype=str,
                    keep_default_na=False,
                )
                lookup = dict(zip(df["codigo"], df["descricao"], strict=False))
                self._reference_tables[table_name.lower()] = lookup
                logger.info("Loaded reference table %s: %d entries", table_name, len(lookup))
            except Exception:
                logger.warning("Could not load reference table %s", table_name)

    def _resolve_reference(self, table: str, code: str) -> str:
        """Look up a code in a reference table. Returns code if not found."""
        lookup = self._reference_tables.get(table, {})
        return lookup.get(code.strip(), code) if code else code

    # --- Reading ---

    def _read_bq_csv(
        self,
        pattern: str,
        rename_map: dict[str, str],
        drop_cols: set[str],
    ) -> pd.DataFrame:
        """Read Base dos Dados (BigQuery) exported CSVs with header row.

        BQ exports use different column names than Receita Federal raw files.
        This method reads header-based CSVs, drops BQ metadata columns, and
        renames columns to match the RF schema used by transform().
        """
        cnpj_dir = Path(self.data_dir) / "cnpj"
        files = sorted(cnpj_dir.glob(f"extracted/{pattern}"))
        if not files:
            return pd.DataFrame()

        frames: list[pd.DataFrame] = []
        total_rows = 0
        for f in files:
            logger.info("Reading BQ export %s...", f.name)
            for chunk in pd.read_csv(
                f, dtype=str, keep_default_na=False, chunksize=self.chunk_size,
            ):
                chunk = chunk.drop(columns=[c for c in drop_cols if c in chunk.columns])
                chunk = chunk.rename(columns=rename_map)
                frames.append(chunk)
                total_rows += len(chunk)
                if self.limit and total_rows >= self.limit:
                    break
            if self.limit and total_rows >= self.limit:
                break

        if not frames:
            return pd.DataFrame()
        result = pd.concat(frames, ignore_index=True)
        if self.limit:
            result = result.head(self.limit)
        logger.info("Read %d rows from BQ export %s", len(result), pattern)
        return result

    def _read_rf_chunks(self, pattern: str, columns: list[str]) -> pd.DataFrame:
        """Read Receita Federal headerless CSVs with chunking for memory efficiency."""
        cnpj_dir = Path(self.data_dir) / "cnpj"
        # Search both extracted/ subdirectory and cnpj/ root
        files = sorted(cnpj_dir.glob(f"extracted/{pattern}"))
        if not files:
            files = sorted(cnpj_dir.glob(pattern))
        if not files:
            return pd.DataFrame(columns=columns)

        frames: list[pd.DataFrame] = []
        total_rows = 0
        for f in files:
            logger.info("Reading %s...", f.name)
            for chunk in pd.read_csv(
                f,
                sep=";",
                encoding="latin-1",
                header=None,
                names=columns,
                dtype=str,
                keep_default_na=False,
                chunksize=self.chunk_size,
            ):
                frames.append(chunk)
                total_rows += len(chunk)
                if self.limit and total_rows >= self.limit:
                    break
            if self.limit and total_rows >= self.limit:
                break

        if not frames:
            return pd.DataFrame(columns=columns)
        result = pd.concat(frames, ignore_index=True)
        if self.limit:
            result = result.head(self.limit)
        logger.info("Read %d rows from %s", len(result), pattern)
        return result

    def extract(self) -> None:
        """Extract data from Receita Federal open data files.

        Tries three formats in order:
        1. Real RF format: headerless `;`-delimited CSVs (production)
        2. Base dos Dados (BigQuery) exports: header-based CSVs with BQ column names
        3. Simple CSV: header-based CSVs with our own column names (dev/test)
        """
        # Load reference tables if available
        self._load_reference_tables()

        cnpj_dir = Path(self.data_dir) / "cnpj"

        # History mode from canonical *_history.csv exports (preferred)
        if self.history:
            hist_empresas = self._read_bq_csv(
                "empresas_history.csv",
                BQ_EMPRESAS_RENAME,
                BQ_EMPRESAS_DROP_HISTORY,
            )
            hist_socios = self._read_bq_csv(
                "socios_history.csv",
                BQ_SOCIOS_RENAME,
                BQ_SOCIOS_DROP_HISTORY,
            )
            hist_estabelecimentos = self._read_bq_csv(
                "estabelecimentos_history.csv",
                BQ_ESTABELECIMENTOS_RENAME,
                BQ_ESTABELECIMENTOS_DROP_HISTORY,
            )
            if not hist_empresas.empty and not hist_socios.empty:
                logger.info("Using CNPJ history mode from *_history.csv files")
                self._raw_empresas = hist_empresas
                self._raw_socios = hist_socios
                self._raw_estabelecimentos = hist_estabelecimentos
                logger.info(
                    "Extracted (history): %d empresas, %d socios, %d estabelecimentos",
                    len(self._raw_empresas),
                    len(self._raw_socios),
                    len(self._raw_estabelecimentos),
                )
                return

        # 1. Try real RF format: *EMPRE* or Empresas*
        rf_empresas = self._read_rf_chunks("*EMPRE*", EMPRESAS_COLS)
        if rf_empresas.empty:
            rf_empresas = self._read_rf_chunks("Empresas*", EMPRESAS_COLS)

        if not rf_empresas.empty:
            self._raw_empresas = rf_empresas
            self._raw_socios = self._read_rf_chunks("*SOCIO*", SOCIOS_COLS)
            if self._raw_socios.empty:
                self._raw_socios = self._read_rf_chunks("Socios*", SOCIOS_COLS)
            self._raw_estabelecimentos = self._read_rf_chunks(
                "*ESTABELE*", ESTABELECIMENTOS_COLS,
            )
            if self._raw_estabelecimentos.empty:
                self._raw_estabelecimentos = self._read_rf_chunks(
                    "Estabelecimentos*", ESTABELECIMENTOS_COLS,
                )
        else:
            # 2. Try BigQuery exports (empresas_*.csv with headers)
            bq_empresas = self._read_bq_csv(
                "empresas_*.csv", BQ_EMPRESAS_RENAME, BQ_EMPRESAS_DROP,
            )
            if not bq_empresas.empty:
                logger.info("Using Base dos Dados (BigQuery) exported data")
                self._raw_empresas = bq_empresas
                self._raw_socios = self._read_bq_csv(
                    "socios_*.csv", BQ_SOCIOS_RENAME, BQ_SOCIOS_DROP,
                )
                self._raw_estabelecimentos = self._read_bq_csv(
                    "estabelecimentos_*.csv",
                    BQ_ESTABELECIMENTOS_RENAME,
                    BQ_ESTABELECIMENTOS_DROP,
                )
            else:
                # 3. Simple CSV fallback (dev/test)
                empresas_path = cnpj_dir / "empresas.csv"
                socios_path = cnpj_dir / "socios.csv"
                estabelecimentos_path = cnpj_dir / "estabelecimentos.csv"
                if empresas_path.exists():
                    self._raw_empresas = pd.read_csv(
                        empresas_path, dtype=str, keep_default_na=False,
                    )
                if socios_path.exists():
                    self._raw_socios = pd.read_csv(
                        socios_path, dtype=str, keep_default_na=False,
                    )
                if estabelecimentos_path.exists():
                    self._raw_estabelecimentos = pd.read_csv(
                        estabelecimentos_path, dtype=str, keep_default_na=False,
                    )

        logger.info(
            "Extracted: %d empresas, %d socios, %d estabelecimentos",
            len(self._raw_empresas),
            len(self._raw_socios),
            len(self._raw_estabelecimentos),
        )

    def _snapshot_from_row(self, row: pd.Series) -> str:
        """Extract canonical snapshot date from row metadata."""
        if "data" in row and str(row["data"]).strip():
            return parse_date(str(row["data"]).strip())

        ano = str(row.get("ano", "")).strip()
        mes = str(row.get("mes", "")).strip()
        if ano and mes:
            try:
                return f"{int(ano):04d}-{int(mes):02d}-01"
            except ValueError:
                return ""
        return ""

    # --- Vectorized transform helpers ---

    def _build_estab_lookup(self, df: pd.DataFrame) -> None:
        """Add estabelecimentos rows to estab_lookup (vectorized prep, zip on deduped)."""
        df = df.copy()
        df["basico"] = df["cnpj_basico"].astype(str).str.zfill(8)
        df["ordem"] = df["cnpj_ordem"].astype(str).str.zfill(4)
        df["dv"] = df["cnpj_dv"].astype(str).str.zfill(2)
        df["cnpj_raw"] = df["basico"] + df["ordem"] + df["dv"]
        # Skip already-seen basico keys, then dedup within chunk
        mask = ~df["basico"].isin(self._estab_lookup)
        df = df.loc[mask].drop_duplicates(subset="basico", keep="first")
        if df.empty:
            return
        for basico, cnpj_raw, cnae, uf, mun in zip(
            df["basico"],
            df["cnpj_raw"],
            df["cnae_principal"].astype(str),
            df["uf"].astype(str),
            df["municipio"].astype(str),
            strict=False,
        ):
            self._estab_lookup[basico] = (format_cnpj(cnpj_raw), cnae, uf, mun)

    def _transform_empresas_rf(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Vectorized transform for RF-format empresas."""
        df = df.copy()
        df["basico"] = df["cnpj_basico"].astype(str).str.zfill(8)
        lookup = self._estab_lookup
        df["cnpj"] = df["basico"].map(
            lambda b: lookup[b][0] if b in lookup else format_cnpj(b + "000100"),
        )
        df["capital_social"] = df["capital_social"].astype(str).map(parse_capital_social)
        df["razao_social"] = df["razao_social"].astype(str).map(normalize_name)
        df["natureza_juridica"] = df["natureza_juridica"].astype(str).map(
            lambda c: self._resolve_reference("naturezas", c),
        )
        df["cnae_principal"] = df["basico"].map(
            lambda b: self._resolve_reference(
                "cnaes", lookup[b][1] if b in lookup else "",
            ),
        )
        df["uf"] = df["basico"].map(lambda b: lookup[b][2] if b in lookup else "")
        df["municipio"] = df["basico"].map(
            lambda b: self._resolve_reference(
                "municipios", lookup[b][3] if b in lookup else "",
            ),
        )
        df["porte_empresa"] = df["porte_empresa"].astype(str)
        cols = ["cnpj", "razao_social", "natureza_juridica", "cnae_principal",
                "capital_social", "uf", "municipio", "porte_empresa"]
        return df[cols].to_dict("records")  # type: ignore[return-value]

    def _transform_empresas_simple(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """Vectorized transform for simple-format empresas."""
        df = df.copy()
        df["cnpj"] = df["cnpj"].astype(str).map(format_cnpj)
        df["capital_social"] = df["capital_social"].astype(str).map(parse_capital_social)
        df["razao_social"] = df["razao_social"].astype(str).map(normalize_name)
        default = pd.Series("", index=df.index)
        df["natureza_juridica"] = df.get("natureza_juridica", default).astype(str)
        df["cnae_principal"] = df["cnae_principal"].astype(str)
        df["uf"] = df["uf"].astype(str)
        df["municipio"] = df["municipio"].astype(str)
        df["porte_empresa"] = df.get("porte_empresa", pd.Series("", index=df.index)).astype(str)
        cols = ["cnpj", "razao_social", "natureza_juridica", "cnae_principal",
                "capital_social", "uf", "municipio", "porte_empresa"]
        return df[cols].to_dict("records")  # type: ignore[return-value]

    def _transform_socios_rf(
        self, df: pd.DataFrame,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Vectorized transform for RF-format socios.

        Returns:
          (pf_person_nodes, pf_partial_partner_nodes, pf_relationships,
           pf_partial_relationships, pj_relationships)
        PJ partners (identificador_socio="1") create Company→Company SOCIO_DE.
        PF partners with valid CPF create Person→Company SOCIO_DE.
        PF partners with masked/invalid docs create Partner→Company SOCIO_DE.
        """
        df = df.copy()
        lookup = self._estab_lookup
        df["basico"] = df["cnpj_basico"].astype(str).str.zfill(8)
        df["cnpj"] = df["basico"].map(
            lambda b: lookup[b][0] if b in lookup else format_cnpj(b + "000100"),
        )
        df["nome"] = df["nome_socio"].astype(str).map(normalize_name)
        df["tipo"] = df["identificador_socio"].astype(str)
        df["qualificacao"] = df["qualificacao_socio"].astype(str).map(
            lambda c: self._resolve_reference("qualificacoes", c),
        )
        df["data_entrada"] = df["data_entrada"].astype(str).map(parse_date)
        df["snapshot_date"] = df.apply(self._snapshot_from_row, axis=1)

        # Split PJ (tipo=1) from PF (tipo=2 or other)
        pj_mask = df["tipo"] == "1"
        pf_df = df[~pj_mask].copy()
        pj_df = df[pj_mask].copy()

        # PF partners: split strong CPF identities from partial/invalid docs
        pf_df["doc_raw"] = pf_df["cpf_cnpj_socio"].astype(str).str.strip()
        pf_df["doc_class"] = pf_df["doc_raw"].map(classify_document)
        pf_df["doc_digits"] = pf_df["doc_raw"].map(strip_document)

        pf_strong = pf_df[pf_df["doc_class"] == "cpf_valid"].copy()
        pf_strong["doc"] = pf_strong["doc_raw"].map(format_cpf)

        pf_partners: list[dict[str, Any]] = pf_strong[["nome", "doc", "tipo"]].rename(
            columns={"nome": "name", "doc": "cpf", "tipo": "tipo_socio"},
        ).to_dict("records")  # type: ignore[assignment]
        pf_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pf_strong["doc"],
            "target_key": pf_strong["cnpj"],
            "tipo_socio": pf_strong["tipo"],
            "qualificacao": pf_strong["qualificacao"],
            "data_entrada": pf_strong["data_entrada"],
            "snapshot_date": pf_strong["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        pf_partial = pf_df[pf_df["doc_class"] != "cpf_valid"].copy()
        pf_partial["partner_id"] = pf_partial.apply(
            lambda row: _make_partner_id(
                str(row["nome"]),
                str(row["doc_raw"]),
                str(row["tipo"]),
            ),
            axis=1,
        )
        pf_partial["doc_partial"] = pf_partial.apply(
            lambda row: str(row["doc_digits"]) if str(row["doc_class"]) == "cpf_partial" else "",
            axis=1,
        )
        pf_partial["identity_quality"] = pf_partial["doc_class"].map(
            lambda cls: "partial" if cls == "cpf_partial" else "unknown",
        )

        partial_partner_nodes: list[dict[str, Any]] = pd.DataFrame({
            "partner_id": pf_partial["partner_id"],
            "name": pf_partial["nome"],
            "doc_raw": pf_partial["doc_raw"],
            "doc_digits": pf_partial["doc_digits"],
            "doc_partial": pf_partial["doc_partial"],
            "doc_type": pf_partial["doc_class"],
            "tipo_socio": pf_partial["tipo"],
            "identity_quality": pf_partial["identity_quality"],
            "source": "receita_federal",
        }).to_dict("records")  # type: ignore[assignment]

        partial_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pf_partial["partner_id"],
            "target_key": pf_partial["cnpj"],
            "tipo_socio": pf_partial["tipo"],
            "qualificacao": pf_partial["qualificacao"],
            "data_entrada": pf_partial["data_entrada"],
            "snapshot_date": pf_partial["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        # PJ partners: keep only CNPJ-like docs for Company→Company relationships
        pj_df["doc_raw"] = pj_df["cpf_cnpj_socio"].astype(str).str.strip()
        pj_df["doc_class"] = pj_df["doc_raw"].map(classify_document)
        pj_df = pj_df[pj_df["doc_class"] == "cnpj_valid"].copy()
        pj_df["doc"] = pj_df["doc_raw"].map(format_cnpj)
        pj_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pj_df["doc"],
            "target_key": pj_df["cnpj"],
            "tipo_socio": pj_df["tipo"],
            "qualificacao": pj_df["qualificacao"],
            "data_entrada": pj_df["data_entrada"],
            "snapshot_date": pj_df["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        return (
            pf_partners,
            partial_partner_nodes,
            pf_relationships,
            partial_relationships,
            pj_relationships,
        )

    def _transform_socios_simple(
        self, df: pd.DataFrame,
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Vectorized transform for simple-format socios.

        Returns:
          (pf_person_nodes, pf_partial_partner_nodes, pf_relationships,
           pf_partial_relationships, pj_relationships)
        """
        df = df.copy()
        df["cnpj"] = df["cnpj"].astype(str).map(format_cnpj)
        df["nome"] = df["nome_socio"].astype(str).map(normalize_name)
        df["tipo"] = df["tipo_socio"].astype(str)
        df["qualificacao"] = df.get(
            "qualificacao_socio", pd.Series("", index=df.index),
        ).astype(str)
        df["data_entrada"] = df.get(
            "data_entrada", pd.Series("", index=df.index),
        ).astype(str).map(parse_date)
        df["snapshot_date"] = df.apply(self._snapshot_from_row, axis=1)

        # Split PJ (tipo=1) from PF (tipo=2 or other)
        pj_mask = df["tipo"] == "1"
        pf_df = df[~pj_mask].copy()
        pj_df = df[pj_mask].copy()

        # PF partners
        pf_df["doc_raw"] = pf_df["cpf_socio"].astype(str).str.strip()
        pf_df["doc_class"] = pf_df["doc_raw"].map(classify_document)
        pf_df["doc_digits"] = pf_df["doc_raw"].map(strip_document)

        pf_strong = pf_df[pf_df["doc_class"] == "cpf_valid"].copy()
        pf_strong["doc"] = pf_strong["doc_raw"].map(format_cpf)

        pf_partners: list[dict[str, Any]] = pf_strong[["nome", "doc", "tipo"]].rename(
            columns={"nome": "name", "doc": "cpf", "tipo": "tipo_socio"},
        ).to_dict("records")  # type: ignore[assignment]
        pf_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pf_strong["doc"],
            "target_key": pf_strong["cnpj"],
            "tipo_socio": pf_strong["tipo"],
            "qualificacao": pf_strong["qualificacao"],
            "data_entrada": pf_strong["data_entrada"],
            "snapshot_date": pf_strong["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        pf_partial = pf_df[pf_df["doc_class"] != "cpf_valid"].copy()
        pf_partial["partner_id"] = pf_partial.apply(
            lambda row: _make_partner_id(
                str(row["nome"]),
                str(row["doc_raw"]),
                str(row["tipo"]),
            ),
            axis=1,
        )
        pf_partial["doc_partial"] = pf_partial.apply(
            lambda row: str(row["doc_digits"]) if str(row["doc_class"]) == "cpf_partial" else "",
            axis=1,
        )
        pf_partial["identity_quality"] = pf_partial["doc_class"].map(
            lambda cls: "partial" if cls == "cpf_partial" else "unknown",
        )

        partial_partner_nodes: list[dict[str, Any]] = pd.DataFrame({
            "partner_id": pf_partial["partner_id"],
            "name": pf_partial["nome"],
            "doc_raw": pf_partial["doc_raw"],
            "doc_digits": pf_partial["doc_digits"],
            "doc_partial": pf_partial["doc_partial"],
            "doc_type": pf_partial["doc_class"],
            "tipo_socio": pf_partial["tipo"],
            "identity_quality": pf_partial["identity_quality"],
            "source": "receita_federal",
        }).to_dict("records")  # type: ignore[assignment]

        partial_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pf_partial["partner_id"],
            "target_key": pf_partial["cnpj"],
            "tipo_socio": pf_partial["tipo"],
            "qualificacao": pf_partial["qualificacao"],
            "data_entrada": pf_partial["data_entrada"],
            "snapshot_date": pf_partial["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        # PJ partners
        pj_df["doc_raw"] = pj_df["cpf_socio"].astype(str).str.strip()
        pj_df["doc_class"] = pj_df["doc_raw"].map(classify_document)
        pj_df = pj_df[pj_df["doc_class"] == "cnpj_valid"].copy()
        pj_df["doc"] = pj_df["doc_raw"].map(format_cnpj)
        pj_relationships: list[dict[str, Any]] = pd.DataFrame({
            "source_key": pj_df["doc"],
            "target_key": pj_df["cnpj"],
            "tipo_socio": pj_df["tipo"],
            "qualificacao": pj_df["qualificacao"],
            "data_entrada": pj_df["data_entrada"],
            "snapshot_date": pj_df["snapshot_date"],
        }).to_dict("records")  # type: ignore[assignment]

        return (
            pf_partners,
            partial_partner_nodes,
            pf_relationships,
            partial_relationships,
            pj_relationships,
        )

    def _build_snapshot_relationships(
        self,
        pf_rels: list[dict[str, Any]],
        partial_rels: list[dict[str, Any]],
        pj_rels: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []

        def _mk_temporal_status(data_entrada: str, snapshot_date: str) -> str:
            if not snapshot_date or not data_entrada:
                return "unknown"
            if data_entrada > snapshot_date:
                return "invalid"
            return "valid"

        for rel in pf_rels:
            snapshot = str(rel.get("snapshot_date", "")).strip()
            data_entrada = str(rel.get("data_entrada", "")).strip()
            rows.append(
                {
                    "source_label": "Person",
                    "source_key": rel["source_key"],
                    "target_key": rel["target_key"],
                    "tipo_socio": rel.get("tipo_socio", ""),
                    "qualificacao": rel.get("qualificacao", ""),
                    "data_entrada": data_entrada,
                    "snapshot_date": snapshot,
                    "membership_id": _make_membership_id(
                        str(rel["source_key"]),
                        str(rel["target_key"]),
                        str(rel.get("tipo_socio", "")),
                        str(rel.get("qualificacao", "")),
                        snapshot,
                        data_entrada,
                    ),
                    "run_id": self.run_id,
                    "source_ref": "basedosdados.br_me_cnpj.socios",
                    "temporal_status": _mk_temporal_status(data_entrada, snapshot),
                    "temporal_rule": "data_entrada_lte_snapshot_date",
                },
            )

        for rel in partial_rels:
            snapshot = str(rel.get("snapshot_date", "")).strip()
            data_entrada = str(rel.get("data_entrada", "")).strip()
            rows.append(
                {
                    "source_label": "Partner",
                    "source_key": rel["source_key"],
                    "target_key": rel["target_key"],
                    "tipo_socio": rel.get("tipo_socio", ""),
                    "qualificacao": rel.get("qualificacao", ""),
                    "data_entrada": data_entrada,
                    "snapshot_date": snapshot,
                    "membership_id": _make_membership_id(
                        str(rel["source_key"]),
                        str(rel["target_key"]),
                        str(rel.get("tipo_socio", "")),
                        str(rel.get("qualificacao", "")),
                        snapshot,
                        data_entrada,
                    ),
                    "run_id": self.run_id,
                    "source_ref": "basedosdados.br_me_cnpj.socios",
                    "temporal_status": _mk_temporal_status(data_entrada, snapshot),
                    "temporal_rule": "data_entrada_lte_snapshot_date",
                },
            )

        for rel in pj_rels:
            snapshot = str(rel.get("snapshot_date", "")).strip()
            data_entrada = str(rel.get("data_entrada", "")).strip()
            rows.append(
                {
                    "source_label": "Company",
                    "source_key": rel["source_key"],
                    "target_key": rel["target_key"],
                    "tipo_socio": rel.get("tipo_socio", ""),
                    "qualificacao": rel.get("qualificacao", ""),
                    "data_entrada": data_entrada,
                    "snapshot_date": snapshot,
                    "membership_id": _make_membership_id(
                        str(rel["source_key"]),
                        str(rel["target_key"]),
                        str(rel.get("tipo_socio", "")),
                        str(rel.get("qualificacao", "")),
                        snapshot,
                        data_entrada,
                    ),
                    "run_id": self.run_id,
                    "source_ref": "basedosdados.br_me_cnpj.socios",
                    "temporal_status": _mk_temporal_status(data_entrada, snapshot),
                    "temporal_rule": "data_entrada_lte_snapshot_date",
                },
            )
        return rows

    def _latest_projection(
        self, rows: list[dict[str, Any]],
    ) -> tuple[
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
    ]:
        """Build latest SOCIO_DE projection from history rows."""
        if not rows:
            return [], [], []
        df = pd.DataFrame(rows)
        if df.empty:
            return [], [], []

        sortable = df.copy()
        sortable["snapshot_date"] = sortable["snapshot_date"].fillna("")
        sortable["data_entrada"] = sortable["data_entrada"].fillna("")
        sortable = sortable.sort_values(
            by=["source_label", "source_key", "target_key", "snapshot_date", "data_entrada"],
            ascending=[True, True, True, False, False],
        )
        latest = sortable.drop_duplicates(
            subset=["source_label", "source_key", "target_key"],
            keep="first",
        )
        rel_cols = ["source_key", "target_key", "tipo_socio", "qualificacao", "data_entrada"]
        person_rows = [
            {str(k): v for k, v in row.items()}
            for row in latest[latest["source_label"] == "Person"][rel_cols].to_dict("records")
        ]
        partner_rows = [
            {str(k): v for k, v in row.items()}
            for row in latest[latest["source_label"] == "Partner"][rel_cols].to_dict("records")
        ]
        company_rows = [
            {str(k): v for k, v in row.items()}
            for row in latest[latest["source_label"] == "Company"][rel_cols].to_dict("records")
        ]
        return person_rows, partner_rows, company_rows

    def _load_snapshot_relationship_rows(
        self,
        loader: Neo4jBatchLoader,
        rows: list[dict[str, Any]],
    ) -> None:
        for source_label, source_key in [
            ("Person", "cpf"),
            ("Partner", "partner_id"),
            ("Company", "cnpj"),
        ]:
            label_rows = [r for r in rows if r["source_label"] == source_label]
            if not label_rows:
                continue
            query = (
                "UNWIND $rows AS row "
                f"MATCH (a:{source_label} {{{source_key}: row.source_key}}) "
                "MATCH (b:Company {cnpj: row.target_key}) "
                "MERGE (a)-[r:SOCIO_DE_SNAPSHOT {membership_id: row.membership_id}]->(b) "
                "SET r.snapshot_date = row.snapshot_date, "
                "    r.data_entrada = row.data_entrada, "
                "    r.tipo_socio = row.tipo_socio, "
                "    r.qualificacao = row.qualificacao, "
                "    r.run_id = row.run_id, "
                "    r.source_ref = row.source_ref, "
                "    r.temporal_status = row.temporal_status, "
                "    r.temporal_rule = row.temporal_rule"
            )
            loader.run_query(query, label_rows)

    def _rebuild_latest_projection_from_snapshots(self) -> None:
        """Rebuild factual SOCIO_DE from latest snapshot per source/target pair."""
        with self.driver.session(database=self.neo4j_database) as session:
            session.run(
                "MATCH ()-[r:SOCIO_DE]->() DELETE r",
            )
            session.run(
                """
                CALL {
                  MATCH (a)-[r:SOCIO_DE_SNAPSHOT]->(b:Company)
                  WHERE coalesce(r.snapshot_date, '') <> ''
                  WITH a, b, max(r.snapshot_date) AS max_snapshot
                  MATCH (a)-[r2:SOCIO_DE_SNAPSHOT]->(b)
                  WHERE r2.snapshot_date = max_snapshot
                  WITH a, b, r2
                  ORDER BY r2.data_entrada DESC
                  WITH a, b, collect(r2)[0] AS latest
                  MERGE (a)-[s:SOCIO_DE]->(b)
                  SET s.tipo_socio = latest.tipo_socio,
                      s.qualificacao = latest.qualificacao,
                      s.data_entrada = latest.data_entrada
                }
                RETURN 1
                """,
            )

    def transform(self) -> None:
        """Transform raw data into normalized company, partner, and relationship records."""
        if not self._raw_estabelecimentos.empty:
            self._build_estab_lookup(self._raw_estabelecimentos)

        is_rf = "cnpj_basico" in self._raw_empresas.columns
        if is_rf:
            companies = self._transform_empresas_rf(self._raw_empresas)
        else:
            companies = self._transform_empresas_simple(self._raw_empresas)
        self.companies = deduplicate_rows(companies, ["cnpj"])
        logger.info("Transformed %d companies", len(self.companies))

        is_rf_socios = "cpf_cnpj_socio" in self._raw_socios.columns
        if is_rf_socios:
            partners, partial_partners, pf_rels, partial_rels, pj_rels = self._transform_socios_rf(
                self._raw_socios,
            )
        else:
            (
                partners,
                partial_partners,
                pf_rels,
                partial_rels,
                pj_rels,
            ) = self._transform_socios_simple(self._raw_socios)
        self.partners = deduplicate_rows(partners, ["cpf"])
        self.partial_partners = deduplicate_rows(partial_partners, ["partner_id"])
        if self.history:
            self.snapshot_relationships = self._build_snapshot_relationships(
                pf_rels,
                partial_rels,
                pj_rels,
            )
            (
                self.relationships,
                self.partner_relationships,
                self.pj_relationships,
            ) = self._latest_projection(self.snapshot_relationships)
        else:
            self.relationships = pf_rels
            self.partner_relationships = partial_rels
            self.pj_relationships = pj_rels
        logger.info(
            "Transformed %d strong PF partners, %d partial partners, "
            "%d PF relationships, %d Partner relationships, %d PJ relationships",
            len(self.partners),
            len(self.partial_partners),
            len(self.relationships),
            len(self.partner_relationships),
            len(self.pj_relationships),
        )
        if self.history:
            logger.info(
                "Transformed %d historical SOCIO_DE_SNAPSHOT rows",
                len(self.snapshot_relationships),
            )

    # --- Streaming pipeline for large datasets ---

    def _find_rf_files(self, pattern: str) -> list[Path]:
        """Find RF-format data files, checking extracted/ then cnpj/ root."""
        cnpj_dir = Path(self.data_dir) / "cnpj"
        files = sorted(cnpj_dir.glob(f"extracted/{pattern}"))
        if not files:
            files = sorted(cnpj_dir.glob(pattern))
        return files

    def _find_bq_files(self, pattern: str) -> list[Path]:
        """Find BQ-format CSVs in extracted/ directory."""
        cnpj_dir = Path(self.data_dir) / "cnpj"
        return sorted(cnpj_dir.glob(f"extracted/{pattern}"))

    def _read_rf_file_chunks(
        self, path: Path, columns: list[str],
    ) -> pd.io.parsers.readers.TextFileReader:
        """Return a chunked reader for a single RF-format CSV."""
        return pd.read_csv(
            path,
            sep=";",
            encoding="latin-1",
            header=None,
            names=columns,
            dtype=str,
            keep_default_na=False,
            chunksize=self.chunk_size,
        )

    def _read_bq_file_chunks(
        self,
        path: Path,
        rename_map: dict[str, str],
        drop_cols: set[str],
    ) -> pd.io.parsers.readers.TextFileReader:
        """Return a chunked reader for a BQ-format CSV that renames/drops per chunk.

        Yields DataFrames with columns renamed to RF schema and BQ metadata dropped.
        """
        reader = pd.read_csv(
            path, dtype=str, keep_default_na=False, chunksize=self.chunk_size,
        )
        return _BQChunkAdapter(reader, rename_map, drop_cols)  # type: ignore[return-value]

    def run_streaming(self, start_phase: int = 1) -> None:
        """Stream-process data files chunk-by-chunk. For datasets that don't fit in memory.

        Tries RF-format files first, falls back to BQ-format CSVs.

        Phase 1: Build estab_lookup from all Estabelecimentos files.
        Phase 2: Stream Empresas -> transform -> load Company nodes.
        Phase 3: Stream Socios -> transform -> load Person nodes + SOCIO_DE relationships.
        """
        self._load_reference_tables()
        loader = Neo4jBatchLoader(self.driver, batch_size=self.chunk_size)
        total_companies = 0
        total_person_partners = 0
        total_partial_partners = 0
        total_person_rels = 0
        total_partial_rels = 0

        # Detect format: RF files first, then BQ files
        estab_files = self._find_rf_files("*ESTABELE*")
        if not estab_files:
            estab_files = self._find_rf_files("Estabelecimentos*")
        use_bq = not estab_files

        if use_bq:
            if self.history:
                bq_estab = self._find_bq_files("estabelecimentos_history.csv")
                bq_emp = self._find_bq_files("empresas_history.csv")
                bq_socio = self._find_bq_files("socios_history.csv")
            else:
                bq_estab = self._find_bq_files("estabelecimentos*.csv")
                bq_emp = self._find_bq_files("empresas*.csv")
                bq_socio = self._find_bq_files("socios*.csv")
            if not bq_estab and not bq_emp and not bq_socio:
                logger.warning("No RF or BQ data files found")
                return
            logger.info("Using Base dos Dados (BigQuery) format for streaming")
        else:
            bq_estab = bq_emp = bq_socio = []

        # Phase 1: Build estab_lookup
        if use_bq:
            logger.info("Phase 1: Building estab_lookup from %d BQ files", len(bq_estab))
            for f in bq_estab:
                logger.info("  Reading %s...", f.name)
                for chunk in self._read_bq_file_chunks(
                    f,
                    BQ_ESTABELECIMENTOS_RENAME,
                    (
                        BQ_ESTABELECIMENTOS_DROP_HISTORY
                        if self.history
                        else BQ_ESTABELECIMENTOS_DROP
                    ),
                ):
                    self._build_estab_lookup(chunk)
        else:
            logger.info("Phase 1: Building estab_lookup from %d RF files", len(estab_files))
            for f in estab_files:
                logger.info("  Reading %s...", f.name)
                for chunk in self._read_rf_file_chunks(f, ESTABELECIMENTOS_COLS):
                    self._build_estab_lookup(chunk)
        logger.info(
            "  estab_lookup: %d unique basico keys", len(self._estab_lookup),
        )

        # Phase 2: Stream Empresas -> load
        if start_phase > 2:
            logger.info("Skipping Phase 2 (empresas) — start_phase=%d", start_phase)
        elif use_bq:
            emp_files = bq_emp
            logger.info("Phase 2: Streaming %d BQ Empresas files", len(emp_files))
            for f in emp_files:
                logger.info("  Processing %s...", f.name)
                for chunk in self._read_bq_file_chunks(
                    f,
                    BQ_EMPRESAS_RENAME,
                    BQ_EMPRESAS_DROP_HISTORY if self.history else BQ_EMPRESAS_DROP,
                ):
                    companies = self._transform_empresas_rf(chunk)
                    if companies:
                        loader.load_nodes("Company", companies, key_field="cnpj")
                        total_companies += len(companies)
                logger.info("  Companies loaded so far: %d", total_companies)
        else:
            emp_files = self._find_rf_files("*EMPRE*")
            if not emp_files:
                emp_files = self._find_rf_files("Empresas*")
            logger.info("Phase 2: Streaming %d RF Empresas files", len(emp_files))
            for f in emp_files:
                logger.info("  Processing %s...", f.name)
                for chunk in self._read_rf_file_chunks(f, EMPRESAS_COLS):
                    companies = self._transform_empresas_rf(chunk)
                    if companies:
                        loader.load_nodes("Company", companies, key_field="cnpj")
                        total_companies += len(companies)
                logger.info("  Companies loaded so far: %d", total_companies)

        # Phase 3: Stream Socios -> load
        if use_bq:
            socio_files = bq_socio
            logger.info("Phase 3: Streaming %d BQ Socios files", len(socio_files))
        else:
            socio_files = self._find_rf_files("*SOCIO*")
            if not socio_files:
                socio_files = self._find_rf_files("Socios*")
            logger.info("Phase 3: Streaming %d RF Socios files", len(socio_files))

        total_pj_rels = 0
        for f in socio_files:
            logger.info("  Processing %s...", f.name)
            chunks = (
                self._read_bq_file_chunks(
                    f,
                    BQ_SOCIOS_RENAME,
                    BQ_SOCIOS_DROP_HISTORY if self.history else BQ_SOCIOS_DROP,
                )
                if use_bq
                else self._read_rf_file_chunks(f, SOCIOS_COLS)
            )
            for chunk in chunks:
                (
                    person_partners,
                    partial_partners,
                    pf_rels,
                    partial_rels,
                    pj_rels,
                ) = self._transform_socios_rf(chunk)
                if person_partners:
                    loader.load_nodes("Person", person_partners, key_field="cpf")
                    total_person_partners += len(person_partners)
                if partial_partners:
                    loader.load_nodes("Partner", partial_partners, key_field="partner_id")
                    total_partial_partners += len(partial_partners)
                if self.history:
                    snapshot_rows = self._build_snapshot_relationships(
                        pf_rels,
                        partial_rels,
                        pj_rels,
                    )
                    self._load_snapshot_relationship_rows(loader, snapshot_rows)
                    total_person_rels += len(pf_rels)
                    total_partial_rels += len(partial_rels)
                    total_pj_rels += len(pj_rels)
                else:
                    if pf_rels:
                        loader.load_relationships(
                            rel_type="SOCIO_DE",
                            rows=pf_rels,
                            source_label="Person",
                            source_key="cpf",
                            target_label="Company",
                            target_key="cnpj",
                            properties=["tipo_socio", "qualificacao", "data_entrada"],
                        )
                        total_person_rels += len(pf_rels)
                    if partial_rels:
                        loader.load_relationships(
                            rel_type="SOCIO_DE",
                            rows=partial_rels,
                            source_label="Partner",
                            source_key="partner_id",
                            target_label="Company",
                            target_key="cnpj",
                            properties=["tipo_socio", "qualificacao", "data_entrada"],
                        )
                        total_partial_rels += len(partial_rels)
                    if pj_rels:
                        loader.load_relationships(
                            rel_type="SOCIO_DE",
                            rows=pj_rels,
                            source_label="Company",
                            source_key="cnpj",
                            target_label="Company",
                            target_key="cnpj",
                            properties=["tipo_socio", "qualificacao", "data_entrada"],
                        )
                        total_pj_rels += len(pj_rels)
            logger.info(
                "  Person partners: %d, partial partners: %d, "
                "Person rels: %d, Partner rels: %d, PJ rels: %d so far",
                total_person_partners,
                total_partial_partners,
                total_person_rels,
                total_partial_rels,
                total_pj_rels,
            )

        if self.history:
            logger.info("Rebuilding latest SOCIO_DE projection from SOCIO_DE_SNAPSHOT...")
            self._rebuild_latest_projection_from_snapshots()

        logger.info(
            "Streaming complete: %d companies, %d Person partners, %d partial partners, "
            "%d Person rels, %d Partner rels, %d PJ rels",
            total_companies,
            total_person_partners,
            total_partial_partners,
            total_person_rels,
            total_partial_rels,
            total_pj_rels,
        )

    def load(self) -> None:
        loader = Neo4jBatchLoader(self.driver)

        if self.companies:
            loader.load_nodes("Company", self.companies, key_field="cnpj")

        if self.partners:
            loader.load_nodes("Person", self.partners, key_field="cpf")

        if self.partial_partners:
            loader.load_nodes("Partner", self.partial_partners, key_field="partner_id")

        if self.relationships:
            loader.load_relationships(
                rel_type="SOCIO_DE",
                rows=self.relationships,
                source_label="Person",
                source_key="cpf",
                target_label="Company",
                target_key="cnpj",
                properties=["tipo_socio", "qualificacao", "data_entrada"],
            )

        if self.partner_relationships:
            loader.load_relationships(
                rel_type="SOCIO_DE",
                rows=self.partner_relationships,
                source_label="Partner",
                source_key="partner_id",
                target_label="Company",
                target_key="cnpj",
                properties=["tipo_socio", "qualificacao", "data_entrada"],
            )

        if self.pj_relationships:
            loader.load_relationships(
                rel_type="SOCIO_DE",
                rows=self.pj_relationships,
                source_label="Company",
                source_key="cnpj",
                target_label="Company",
                target_key="cnpj",
                properties=["tipo_socio", "qualificacao", "data_entrada"],
            )

        if self.snapshot_relationships:
            self._load_snapshot_relationship_rows(loader, self.snapshot_relationships)
