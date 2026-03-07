#!/usr/bin/env python3
"""Download senator identity data from Senado Dados Abertos API.

Builds a lookup table mapping parliamentary names to CPFs and IDs.
Used by the Senado pipeline to match CEAPS expenses to Person nodes.

Usage:
    python etl/scripts/download_senado_parlamentares.py
    python etl/scripts/download_senado_parlamentares.py --output-dir ./data/senado
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import click
import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

API_BASE = "https://legis.senado.leg.br/dadosabertos"
HEADERS = {"Accept": "application/json"}

# Legislatures to fetch (48th = 1987, current 57th = 2023-2027)
LEGISLATURES = list(range(48, 58))


def _fetch_json(url: str, timeout: int = 30) -> dict | None:
    """Fetch JSON from Senado API with retry."""
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=timeout)
            if resp.status_code == 200:
                return resp.json()
            logger.warning("HTTP %d for %s", resp.status_code, url)
        except requests.RequestException as e:
            logger.warning("Request error (attempt %d): %s", attempt + 1, e)
            time.sleep(2 ** attempt)
    return None


def _fetch_senator_detail(codigo: str, timeout: int = 30) -> dict | None:
    """Fetch detailed senator info including identification data."""
    url = f"{API_BASE}/senador/{codigo}"
    data = _fetch_json(url, timeout)
    if not data:
        return None
    try:
        parlamentar = data["DetalheParlamentar"]["Parlamentar"]
        ident = parlamentar.get("IdentificacaoParlamentar", {})
        dados = parlamentar.get("DadosBasicosParlamentar", {})
        return {
            "codigo": ident.get("CodigoParlamentar", ""),
            "nome_parlamentar": ident.get("NomeParlamentar", ""),
            "nome_completo": ident.get("NomeCompletoParlamentar", ""),
            "sexo": ident.get("SexoParlamentar", ""),
            "uf": ident.get("UfParlamentar", ""),
            "partido": ident.get("SiglaPartidoParlamentar", ""),
            "cpf": dados.get("CpfParlamentar", ""),
            "data_nascimento": dados.get("DataNascimento", ""),
        }
    except (KeyError, TypeError) as e:
        logger.warning("Failed to parse detail for %s: %s", codigo, e)
        return None


def _fetch_legislature_senators(legislatura: int, timeout: int = 30) -> list[dict]:
    """Fetch senator list for a given legislature."""
    url = f"{API_BASE}/senador/lista/legislatura/{legislatura}"
    data = _fetch_json(url, timeout)
    if not data:
        return []

    try:
        lista = data["ListaParlamentarLegislatura"]["Parlamentares"]["Parlamentar"]
        if isinstance(lista, dict):
            lista = [lista]
        senators = []
        for p in lista:
            ident = p.get("IdentificacaoParlamentar", {})
            senators.append({
                "codigo": ident.get("CodigoParlamentar", ""),
                "nome_parlamentar": ident.get("NomeParlamentar", ""),
                "nome_completo": ident.get("NomeCompletoParlamentar", ""),
                "uf": ident.get("UfParlamentar", ""),
                "partido": ident.get("SiglaPartidoParlamentar", ""),
                "legislatura": legislatura,
            })
        return senators
    except (KeyError, TypeError) as e:
        logger.warning("Failed to parse legislature %d: %s", legislatura, e)
        return []


@click.command()
@click.option("--output-dir", default="./data/senado", help="Output directory")
@click.option("--timeout", type=int, default=30, help="Request timeout in seconds")
@click.option("--fetch-details/--no-fetch-details", default=True,
              help="Fetch individual senator details for CPFs")
def main(output_dir: str, timeout: int, fetch_details: bool) -> None:
    """Download senator identity data from Senado Dados Abertos API."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Collect all unique senators across legislatures
    all_senators: dict[str, dict] = {}  # keyed by codigo

    for leg in LEGISLATURES:
        logger.info("Fetching legislature %d...", leg)
        senators = _fetch_legislature_senators(leg, timeout)
        for s in senators:
            codigo = s["codigo"]
            if codigo not in all_senators:
                all_senators[codigo] = {
                    "codigo": codigo,
                    "nome_parlamentar": s["nome_parlamentar"],
                    "nome_completo": s["nome_completo"],
                    "uf": s["uf"],
                    "partido": s["partido"],
                    "legislaturas": [],
                    "cpf": "",
                }
            all_senators[codigo]["legislaturas"].append(leg)
        logger.info("  Found %d senators in legislature %d", len(senators), leg)
        time.sleep(0.5)  # Be polite to the API

    logger.info("Total unique senators: %d", len(all_senators))

    # Fetch detailed info for CPFs
    if fetch_details:
        cpf_count = 0
        for i, (codigo, senator) in enumerate(all_senators.items()):
            if (i + 1) % 50 == 0:
                logger.info("  Fetching details: %d/%d...", i + 1, len(all_senators))

            detail = _fetch_senator_detail(codigo, timeout)
            if detail and detail.get("cpf"):
                senator["cpf"] = detail["cpf"]
                cpf_count += 1
            if detail:
                senator["nome_completo"] = (
                    detail.get("nome_completo") or senator["nome_completo"]
                )
                senator["sexo"] = detail.get("sexo", "")
                senator["data_nascimento"] = detail.get("data_nascimento", "")

            time.sleep(0.3)  # Rate limit

        logger.info("Fetched CPFs for %d/%d senators", cpf_count, len(all_senators))

    # Save lookup
    output_path = out / "parlamentares.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(list(all_senators.values()), f, ensure_ascii=False, indent=2)

    logger.info("Saved %d senators to %s", len(all_senators), output_path)


if __name__ == "__main__":
    main()
