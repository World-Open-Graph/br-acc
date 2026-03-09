"""Download Tesouro Transparente Emendas data."""

import logging
from pathlib import Path

import httpx

logger = logging.getLogger(__name__)

# URL from CKAN API for "emendas-parlamentares"
DATASET_URL = "https://www.tesourotransparente.gov.br/ckan/dataset/83e419da-1552-46bf-bfc3-05160b2c46c9/resource/66d69917-a5d8-4500-b4b2-ef1f5d062430/download/emendas-parlamentares.csv"

def download_tesouro_emendas(dest_dir: Path) -> None:
    dest_dir.mkdir(parents=True, exist_ok=True)
    out_file = dest_dir / "emendas_tesouro.csv"

    logger.info("Downloading Tesouro Emendas CSV...")
    with httpx.Client(verify=False, timeout=60.0) as client:
        response = client.get(DATASET_URL, follow_redirects=True)
        response.raise_for_status()
        out_file.write_bytes(response.content)

    logger.info("Downloaded %s (%.2f MB)", out_file.name, out_file.stat().st_size / 1024 / 1024)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    data_dir = Path("data/tesouro_emendas")
    download_tesouro_emendas(data_dir)
