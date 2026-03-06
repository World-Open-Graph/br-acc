#!/usr/bin/env python3
"""Download UN Security Council consolidated sanctions list.

Downloads the XML from the UN sanctions website, parses INDIVIDUAL
and ENTITY entries, and saves as JSON for pipeline consumption.

Usage:
    python etl/scripts/download_un_sanctions.py
    python etl/scripts/download_un_sanctions.py --output-dir ./data/un_sanctions
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click
import defusedxml.ElementTree as ET

# Allow imports from scripts/ directory
sys.path.insert(0, str(Path(__file__).parent))
from _download_utils import download_file

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

UN_XML_URL = "https://scsanctions.un.org/resources/xml/en/consolidated.xml"


def _parse_individual(elem: ET.Element) -> dict[str, str | list[str]]:
    """Parse an INDIVIDUAL element from the UN consolidated XML."""
    ref = elem.findtext("REFERENCE_NUMBER", "").strip()

    # Name: combine FIRST_NAME + SECOND_NAME + THIRD_NAME
    first = elem.findtext("FIRST_NAME", "").strip()
    second = elem.findtext("SECOND_NAME", "").strip()
    third = elem.findtext("THIRD_NAME", "").strip()
    parts = [p for p in [first, second, third] if p]
    name = " ".join(parts)

    listed_date = elem.findtext("LISTED_ON", "").strip()

    # UN list type from parent context (SORT_KEY prefix)
    un_list_type = elem.findtext("UN_LIST_TYPE", "").strip()

    # Nationality from NATIONALITY/VALUE
    nationality_elem = elem.find(".//NATIONALITY/VALUE")
    nationality = ""
    if nationality_elem is not None and nationality_elem.text:
        nationality = nationality_elem.text.strip()

    # Aliases
    aliases: list[str] = []
    for alias_elem in elem.findall(".//INDIVIDUAL_ALIAS"):
        alias_name = alias_elem.findtext("ALIAS_NAME", "").strip()
        if alias_name:
            aliases.append(alias_name)

    return {
        "reference_number": ref,
        "name": name,
        "entity_type": "individual",
        "listed_date": listed_date,
        "un_list_type": un_list_type,
        "nationality": nationality,
        "aliases": aliases,
    }


def _parse_entity(elem: ET.Element) -> dict[str, str | list[str]]:
    """Parse an ENTITY element from the UN consolidated XML."""
    ref = elem.findtext("REFERENCE_NUMBER", "").strip()

    # Entity name from FIRST_NAME (entities typically only have this)
    first = elem.findtext("FIRST_NAME", "").strip()
    name = first

    listed_date = elem.findtext("LISTED_ON", "").strip()
    un_list_type = elem.findtext("UN_LIST_TYPE", "").strip()

    # Aliases
    aliases: list[str] = []
    for alias_elem in elem.findall(".//ENTITY_ALIAS"):
        alias_name = alias_elem.findtext("ALIAS_NAME", "").strip()
        if alias_name:
            aliases.append(alias_name)

    return {
        "reference_number": ref,
        "name": name,
        "entity_type": "entity",
        "listed_date": listed_date,
        "un_list_type": un_list_type,
        "nationality": "",
        "aliases": aliases,
    }


def parse_un_xml(xml_path: Path) -> list[dict[str, str | list[str]]]:
    """Parse the UN consolidated XML and extract individuals and entities."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    entries: list[dict[str, str | list[str]]] = []

    # Parse individuals
    for elem in root.iter("INDIVIDUAL"):
        entry = _parse_individual(elem)
        if entry["reference_number"] and entry["name"]:
            entries.append(entry)

    # Parse entities
    for elem in root.iter("ENTITY"):
        entry = _parse_entity(elem)
        if entry["reference_number"] and entry["name"]:
            entries.append(entry)

    return entries


@click.command()
@click.option("--output-dir", default="./data/un_sanctions", help="Output directory")
@click.option(
    "--skip-existing/--no-skip-existing", default=True, help="Skip existing files"
)
@click.option("--timeout", type=int, default=300, help="Download timeout in seconds")
def main(output_dir: str, skip_existing: bool, timeout: int) -> None:
    """Download and parse UN Security Council consolidated sanctions list."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    json_path = out / "un_sanctions.json"
    xml_path = out / "consolidated.xml"

    if skip_existing and json_path.exists():
        logger.info("Skipping (exists): %s", json_path)
        return

    # Download XML
    logger.info("=== Downloading UN consolidated sanctions XML ===")
    if not download_file(UN_XML_URL, xml_path, timeout=timeout):
        logger.warning("Failed to download UN sanctions XML")
        sys.exit(1)

    # Parse XML to JSON
    logger.info("=== Parsing XML ===")
    entries = parse_un_xml(xml_path)

    # Save as JSON
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    logger.info(
        "=== Done: %d entries saved to %s ===",
        len(entries),
        json_path,
    )


if __name__ == "__main__":
    main()
