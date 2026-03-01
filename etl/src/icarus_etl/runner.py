import logging
import os

import click
from neo4j import GraphDatabase

from icarus_etl.linking_hooks import run_post_load_hooks
from icarus_etl.pipelines.bcb import BcbPipeline
from icarus_etl.pipelines.bndes import BndesPipeline
from icarus_etl.pipelines.caged import CagedPipeline
from icarus_etl.pipelines.camara import CamaraPipeline
from icarus_etl.pipelines.camara_inquiries import CamaraInquiriesPipeline
from icarus_etl.pipelines.ceaf import CeafPipeline
from icarus_etl.pipelines.cepim import CepimPipeline
from icarus_etl.pipelines.cnpj import CNPJPipeline
from icarus_etl.pipelines.comprasnet import ComprasnetPipeline
from icarus_etl.pipelines.cpgf import CpgfPipeline
from icarus_etl.pipelines.cvm import CvmPipeline
from icarus_etl.pipelines.cvm_funds import CvmFundsPipeline
from icarus_etl.pipelines.datajud import DatajudPipeline
from icarus_etl.pipelines.datasus import DatasusPipeline
from icarus_etl.pipelines.dou import DouPipeline
from icarus_etl.pipelines.eu_sanctions import EuSanctionsPipeline
from icarus_etl.pipelines.holdings import HoldingsPipeline
from icarus_etl.pipelines.ibama import IbamaPipeline
from icarus_etl.pipelines.icij import ICIJPipeline
from icarus_etl.pipelines.inep import InepPipeline
from icarus_etl.pipelines.leniency import LeniencyPipeline
from icarus_etl.pipelines.mides import MidesPipeline
from icarus_etl.pipelines.ofac import OfacPipeline
from icarus_etl.pipelines.opensanctions import OpenSanctionsPipeline
from icarus_etl.pipelines.pep_cgu import PepCguPipeline
from icarus_etl.pipelines.pgfn import PgfnPipeline
from icarus_etl.pipelines.pncp import PncpPipeline
from icarus_etl.pipelines.querido_diario import QueridoDiarioPipeline
from icarus_etl.pipelines.rais import RaisPipeline
from icarus_etl.pipelines.renuncias import RenunciasPipeline
from icarus_etl.pipelines.sanctions import SanctionsPipeline
from icarus_etl.pipelines.senado import SenadoPipeline
from icarus_etl.pipelines.senado_cpis import SenadoCpisPipeline
from icarus_etl.pipelines.siconfi import SiconfiPipeline
from icarus_etl.pipelines.siop import SiopPipeline
from icarus_etl.pipelines.stf import StfPipeline
from icarus_etl.pipelines.tcu import TcuPipeline
from icarus_etl.pipelines.transferegov import TransferegovPipeline
from icarus_etl.pipelines.transparencia import TransparenciaPipeline
from icarus_etl.pipelines.tse import TSEPipeline
from icarus_etl.pipelines.tse_bens import TseBensPipeline
from icarus_etl.pipelines.tse_filiados import TseFiliadosPipeline
from icarus_etl.pipelines.un_sanctions import UnSanctionsPipeline
from icarus_etl.pipelines.viagens import ViagensPipeline
from icarus_etl.pipelines.world_bank import WorldBankPipeline

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
}


@click.group()
def cli() -> None:
    """ICARUS ETL — Data ingestion pipelines for Brazilian public data."""
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
    driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    if source not in PIPELINES:
        available = ", ".join(PIPELINES.keys())
        raise click.ClickException(f"Unknown source: {source}. Available: {available}")

    pipeline_cls = PIPELINES[source]
    try:
        pipeline = pipeline_cls(
            driver=driver,
            data_dir=data_dir,
            limit=limit,
            chunk_size=chunk_size,
            history=history,
        )
    except TypeError:
        pipeline = pipeline_cls(
            driver=driver,
            data_dir=data_dir,
            limit=limit,
            chunk_size=chunk_size,
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

    driver.close()


@cli.command()
@click.option("--output-dir", default="./data/cnpj", help="Output directory")
@click.option("--files", type=int, default=10, help="Number of files per type (0-9)")
@click.option("--skip-existing/--no-skip-existing", default=True)
def download(output_dir: str, files: int, skip_existing: bool) -> None:
    """Download CNPJ data from Receita Federal."""
    import zipfile
    from pathlib import Path

    import httpx

    logger = logging.getLogger(__name__)

    base_url = "https://dadosabertos.rfb.gov.br/CNPJ/"
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
                    zf.extractall(out)
            except httpx.HTTPError:
                logger.warning("Failed to download %s (may not exist)", filename)


@cli.command()
def sources() -> None:
    """List available data sources."""
    click.echo("Available pipelines:")
    for name in sorted(PIPELINES):
        click.echo(f"  {name}")


if __name__ == "__main__":
    cli()
