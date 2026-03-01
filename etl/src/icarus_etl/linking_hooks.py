from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from neo4j import Driver

logger = logging.getLogger(__name__)


def _split_statements(raw: str) -> list[str]:
    statements = [s.strip() for s in raw.split(";") if s.strip()]
    cleaned: list[str] = []
    for stmt in statements:
        lines = [ln for ln in stmt.splitlines() if not ln.strip().startswith("//")]
        cypher = "\n".join(lines).strip()
        if cypher:
            cleaned.append(cypher)
    return cleaned


def _run_script(driver: Driver, neo4j_database: str, script_path: Path) -> None:
    raw = script_path.read_text(encoding="utf-8")
    statements = _split_statements(raw)
    if not statements:
        return
    with driver.session(database=neo4j_database) as session:
        for stmt in statements:
            session.run(stmt)
    logger.info(
        "Post-load linking script applied: %s (%d statements)",
        script_path.name,
        len(statements),
    )


def run_post_load_hooks(
    *,
    driver: Driver,
    source: str,
    neo4j_database: str,
    linking_tier: str,
) -> None:
    tier = linking_tier.strip().lower()
    if tier not in {"community", "full"}:
        tier = "full"

    if tier == "community":
        logger.info("Post-load hooks skipped (LINKING_TIER=community)")
        return

    repo_root = Path(__file__).resolve().parents[3]
    scripts_dir = repo_root / "scripts"

    script_names: list[str] = []
    if source == "cnpj":
        script_names.extend(["link_partners_probable.cypher", "link_persons.cypher"])
    elif source in {"tse", "transparencia", "camara", "senado", "senado_cpis", "tse_filiados"}:
        script_names.append("link_persons.cypher")

    if not script_names:
        logger.info("No post-load linking hook configured for source=%s", source)
        return

    for name in script_names:
        script_path = scripts_dir / name
        if not script_path.exists():
            logger.warning("Post-load linking script missing (skipped): %s", script_path)
            continue
        _run_script(driver, neo4j_database, script_path)
