import logging
import os

import click
from neo4j import GraphDatabase

from bracc_etl.linking_hooks import run_post_load_hooks
from bracc_etl.pipelines.bcb import BcbPipeline
from bracc_etl.pipelines.bndes import BndesPipeline
from bracc_etl.pipelines.caged import CagedPipeline
from bracc_etl.pipelines.camara import CamaraPipeline
from bracc_etl.pipelines.camara_inquiries import CamaraInquiriesPipeline
from bracc_etl.pipelines.ceaf import CeafPipeline
from bracc_etl.pipelines.cepim import CepimPipeline
from bracc_etl.pipelines.cnpj import CNPJPipeline
from bracc_etl.pipelines.comprasnet import ComprasnetPipeline
from bracc_etl.pipelines.cpgf import CpgfPipeline
from bracc_etl.pipelines.cvm import CvmPipeline
from bracc_etl.pipelines.cvm_funds import CvmFundsPipeline
from bracc_etl.pipelines.datajud import DatajudPipeline
from bracc_etl.pipelines.datasus import DatasusPipeline
from bracc_etl.pipelines.dou import DouPipeline
from bracc_etl.pipelines.eu_sanctions import EuSanctionsPipeline
from bracc_etl.pipelines.holdings import HoldingsPipeline
from bracc_etl.pipelines.ibama import IbamaPipeline
from bracc_etl.pipelines.icij import ICIJPipeline
from bracc_etl.pipelines.inep import InepPipeline
from bracc_etl.pipelines.leniency import LeniencyPipeline
from bracc_etl.pipelines.mides import MidesPipeline
from bracc_etl.pipelines.ofac import OfacPipeline
from bracc_etl.pipelines.opensanctions import OpenSanctionsPipeline
from bracc_etl.pipelines.pep_cgu import PepCguPipeline
from bracc_etl.pipelines.pgfn import PgfnPipeline
from bracc_etl.pipelines.pncp import PncpPipeline
from bracc_etl.pipelines.querido_diario import QueridoDiarioPipeline
from bracc_etl.pipelines.rais import RaisPipeline
from bracc_etl.pipelines.renuncias import RenunciasPipeline
from bracc_etl.pipelines.sanctions import SanctionsPipeline
from bracc_etl.pipelines.senado import SenadoPipeline
from bracc_etl.pipelines.senado_cpis import SenadoCpisPipeline
from bracc_etl.pipelines.siconfi import SiconfiPipeline
from bracc_etl.pipelines.siop import SiopPipeline
from bracc_etl.pipelines.stf import StfPipeline
from bracc_etl.pipelines.stj_dados_abertos import StjPipeline
from bracc_etl.pipelines.tcu import TcuPipeline
from bracc_etl.pipelines.tesouro_emendas import TesouroEmendasPipeline
from bracc_etl.pipelines.transferegov import TransferegovPipeline
from bracc_etl.pipelines.transparencia import TransparenciaPipeline
from bracc_etl.pipelines.tse import TSEPipeline
from bracc_etl.pipelines.tse_bens import TseBensPipeline
from bracc_etl.pipelines.tse_filiados import TseFiliadosPipeline
from bracc_etl.pipelines.un_sanctions import UnSanctionsPipeline
from bracc_etl.pipelines.viagens import ViagensPipeline
from bracc_etl.pipelines.world_bank import WorldBankPipeline

PIPELINES: dict[str, type] = {
    "cnpj": CNPJPipeline,
    "tse": TSEPipeline,
    "transparencia": TransparenciaPipeline,
    "sanctions": SanctionsPipeline,
    "pep_cgu": PepCguPipeline,
    "bndes": BndesPipeline,
    "pgfn": PgfnPipeline,
    "ibama": IbamaPipeline,
    "comprasnet": ComprasnetPipeline,
    "tcu": TcuPipeline,
    "transferegov": TransferegovPipeline,
    "rais": RaisPipeline,
    "inep": InepPipeline,
    "dou": DouPipeline,
    "datasus": DatasusPipeline,
    "icij": ICIJPipeline,
    "opensanctions": OpenSanctionsPipeline,
    "cvm": CvmPipeline,
    "cvm_funds": CvmFundsPipeline,
    "camara": CamaraPipeline,
    "camara_inquiries": CamaraInquiriesPipeline,
    "senado": SenadoPipeline,
    "ceaf": CeafPipeline,
    "cepim": CepimPipeline,
    "cpgf": CpgfPipeline,
    "leniency": LeniencyPipeline,
    "ofac": OfacPipeline,
    "holdings": HoldingsPipeline,
    "viagens": ViagensPipeline,
    "siop": SiopPipeline,
    "pncp": PncpPipeline,
    "renuncias": RenunciasPipeline,
    "siconfi": SiconfiPipeline,
    "tse_bens": TseBensPipeline,
    "tse_filiados": TseFiliadosPipeline,
    "bcb": BcbPipeline,
    "stf": StfPipeline,
    "caged": CagedPipeline,
    "eu_sanctions": EuSanctionsPipeline,
    "un_sanctions": UnSanctionsPipeline,
    "world_bank": WorldBankPipeline,
    "senado_cpis": SenadoCpisPipeline,
    "mides": MidesPipeline,
    "querido_diario": QueridoDiarioPipeline,
    "datajud": DatajudPipeline,
    "tesouro_emendas": TesouroEmendasPipeline,
    "stj_dados_abertos": StjPipeline,
}


@click.group()
def cli() -> None:
    """BR-ACC ETL — Data ingestion pipelines for Brazilian public data."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")


@cli.command()
@click.option("--source", required=True, help="Pipeline name (see 'sources' command)")
@click.option("--neo4j-uri", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-user", default="neo4j", help="Neo4j user")
@click.option("--neo4j-password", required=True, help="Neo4j password")
@click.option("--neo4j-database", default="neo4j", help="Neo4j database")
@click.option("--data-dir", default="./data", help="Directory for downloaded data")
@click.option("--limit", type=int, default=None, help="Limit rows processed")
@click.option("--chunk-size", type=int, default=50_000, help="Chunk size for batch processing")
@click.option(
    "--linking-tier",
    type=click.Choice(["community", "full"]),
    default=os.getenv("LINKING_TIER", "full"),
    show_default=True,
    help="Post-load linking strategy tier",
)
@click.option("--streaming/--no-streaming", default=False, help="Streaming mode")
@click.option("--start-phase", type=int, default=1, help="Skip to phase N")
@click.option("--history/--no-history", default=False, help="Enable history mode when supported")
def run(
    source: str,
    neo4j_uri: str,
    neo4j_user: str,
    neo4j_password: str,
    neo4j_database: str,
    data_dir: str,
    limit: int | None,
    chunk_size: int,
    linking_tier: str,
    streaming: bool,
    start_phase: int,
    history: bool,
) -> None:
    """Run an ETL pipeline."""
    os.environ["NEO4J_DATABASE"] = neo4j_database

    if source not in PIPELINES:
        available = ", ".join(PIPELINES.keys())
        raise click.ClickException(f"Unknown source: {source}. Available: {available}")

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        pipeline_cls = PIPELINES[source]
        pipeline = pipeline_cls(
            driver=driver,
            data_dir=data_dir,
            limit=limit,
            chunk_size=chunk_size,
            history=history,
        )

        if streaming and hasattr(pipeline, "run_streaming"):
            pipeline.run_streaming(start_phase=start_phase)
        else:
            pipeline.run()

        run_post_load_hooks(
            driver=driver,
            source=source,
            neo4j_database=neo4j_database,
            linking_tier=linking_tier,
        )
    finally:
        driver.close()


def _resolve_rf_release_inline(year_month: str | None = None) -> str:
    """Resolve Receita Federal CNPJ release URL.

    Tries Nextcloud shares first (new primary), falls back to dadosabertos.rfb.gov.br.
    """
    from datetime import UTC, datetime

    import httpx

    # --- Nextcloud (primary) ---
    nextcloud_dl = "https://arquivos.receitafederal.gov.br/s/{token}/download?path=%2F&files="
    tokens: list[str] = []
    env_token = os.environ.get("CNPJ_SHARE_TOKEN")
    if env_token:
        tokens.append(env_token)
    tokens.extend(["gn672Ad4CF8N6TK", "YggdBLfdninEJX9"])

    for token in tokens:
        share_url = f"https://arquivos.receitafederal.gov.br/s/{token}"
        try:
            resp = httpx.head(share_url, follow_redirects=True, timeout=30)
            if resp.status_code < 400:
                return nextcloud_dl.format(token=token)
        except httpx.HTTPError:
            pass

    # --- Legacy dadosabertos (fallback) ---
    new_base = "https://dadosabertos.rfb.gov.br/CNPJ/dados_abertos_cnpj/{ym}/"
    legacy_url = "https://dadosabertos.rfb.gov.br/CNPJ/"

    now = datetime.now(UTC)
    if year_month is not None:
        candidates = [year_month]
    else:
        current = f"{now.year:04d}-{now.month:02d}"
        prev_m = now.month - 1 if now.month > 1 else 12
        prev_y = now.year if now.month > 1 else now.year - 1
        candidates = [current, f"{prev_y:04d}-{prev_m:02d}"]

    for ym in candidates:
        url = new_base.format(ym=ym)
        try:
            resp = httpx.head(url, follow_redirects=True, timeout=30)
            if resp.status_code < 400:
                return url
        except httpx.HTTPError:
            pass

    try:
        resp = httpx.head(legacy_url, follow_redirects=True, timeout=30)
        if resp.status_code < 400:
            return legacy_url
    except httpx.HTTPError:
        pass

    tried = ", ".join(candidates)
    msg = f"Could not resolve CNPJ release. Tried Nextcloud tokens, months [{tried}], and legacy."
    raise RuntimeError(msg)


@cli.command()
@click.option("--output-dir", default="./data/cnpj", help="Output directory")
@click.option("--files", type=int, default=10, help="Number of files per type (0-9)")
@click.option("--skip-existing/--no-skip-existing", default=True)
@click.option("--release", default=None, help="Pin to specific monthly release (YYYY-MM)")
def download(output_dir: str, files: int, skip_existing: bool, release: str | None) -> None:
    """Download CNPJ data from Receita Federal."""
    import zipfile
    from pathlib import Path

    import httpx

    logger = logging.getLogger(__name__)

    base_url = _resolve_rf_release_inline(release)
    logger.info("Using CNPJ release URL: %s", base_url)
    file_types = ["Empresas", "Socios", "Estabelecimentos"]

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    for file_type in file_types:
        for i in range(min(files, 10)):
            filename = f"{file_type}{i}.zip"
            url = f"{base_url}{filename}"
            dest = out / filename
            try:
                if skip_existing and dest.exists():
                    logger.info("Skipping (exists): %s", dest.name)
                    continue

                logger.info("Downloading %s...", url)
                with httpx.stream("GET", url, follow_redirects=True, timeout=300) as response:
                    response.raise_for_status()
                    with open(dest, "wb") as f:
                        for chunk in response.iter_bytes(chunk_size=8192):
                            f.write(chunk)
                logger.info("Downloaded: %s", dest.name)

                logger.info("Extracting %s...", dest.name)
                with zipfile.ZipFile(dest, "r") as zf:
                    # Path traversal guard
                    out_resolved = out.resolve()
                    safe = True
                    for info in zf.infolist():
                        target = (out / info.filename).resolve()
                        if not target.is_relative_to(out_resolved):
                            logger.warning(
                                "Path traversal in %s: %s — skipping archive",
                                dest.name,
                                info.filename,
                            )
                            safe = False
                            break
                    if not safe:
                        continue
                    # Zip bomb guard (50 GB limit for CNPJ data)
                    total = sum(i.file_size for i in zf.infolist())
                    if total > 50 * 1024**3:
                        logger.warning(
                            "Uncompressed size too large: %s (%.1f GB) — skipping",
                            dest.name,
                            total / 1e9,
                        )
                        continue
                    zf.extractall(out)
            except httpx.HTTPError:
                logger.warning("Failed to download %s (may not exist)", filename)


@cli.command()
@click.option("--status", "show_status", is_flag=True, help="Show ingestion status from Neo4j")
@click.option("--neo4j-uri", default="bolt://localhost:7687", help="Neo4j URI")
@click.option("--neo4j-user", default="neo4j")
@click.option("--neo4j-password", default=None)
def sources(show_status: bool, neo4j_uri: str, neo4j_user: str, neo4j_password: str | None) -> None:
    """List available data sources."""
    if not show_status:
        click.echo("Available pipelines:")
        for name in sorted(PIPELINES):
            click.echo(f"  {name}")
        return

    if not neo4j_password:
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "")
    if not neo4j_password:
        raise click.ClickException(
            "--neo4j-password or NEO4J_PASSWORD env var required for --status"
        )

    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))
    try:
        with driver.session() as session:
            result = session.run(
                "MATCH (r:IngestionRun) "
                "WITH r ORDER BY r.started_at DESC "
                "WITH r.source_id AS sid, collect(r)[0] AS latest "
                "RETURN latest ORDER BY sid"
            )
            runs = {r["latest"]["source_id"]: dict(r["latest"]) for r in result}

        click.echo(
            f"{'Source':<20} {'Status':<15} {'Rows In':>10} {'Loaded':>10} "
            f"{'Started':<20} {'Finished':<20}"
        )
        click.echo("-" * 100)

        for name in sorted(PIPELINES):
            run = runs.get(name, {})
            click.echo(
                f"{name:<20} "
                f"{run.get('status', '-'):<15} "
                f"{run.get('rows_in', 0):>10,} "
                f"{run.get('rows_loaded', 0):>10,} "
                f"{str(run.get('started_at', '-')):<20} "
                f"{str(run.get('finished_at', '-')):<20}"
            )
    finally:
        driver.close()


if __name__ == "__main__":
    cli()
