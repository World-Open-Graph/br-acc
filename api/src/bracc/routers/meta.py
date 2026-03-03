import time
from typing import Annotated, Any

from fastapi import APIRouter, Depends
from neo4j import AsyncSession

from bracc.dependencies import get_session
from bracc.services.cache import cache
from bracc.services.neo4j_service import execute_query_single
from bracc.services.source_registry import load_source_registry, source_registry_summary

router = APIRouter(prefix="/api/v1/meta", tags=["meta"])

_stats_cache: dict[str, Any] | None = None
_stats_cache_time: float = 0.0


@router.get("/health")
async def neo4j_health(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    record = await execute_query_single(session, "health_check", {})
    if record and record["ok"] == 1:
        return {"neo4j": "connected"}
    return {"neo4j": "error"}


@router.get("/stats")
async def database_stats(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    global _stats_cache, _stats_cache_time  # noqa: PLW0603

    if _stats_cache is not None and (time.monotonic() - _stats_cache_time) < 300:
        return _stats_cache

    record = await execute_query_single(session, "meta_stats", {})
    source_entries = load_source_registry()
    source_summary = source_registry_summary(source_entries)

    result = {
        "total_nodes": record["total_nodes"] if record else 0,
        "total_relationships": record["total_relationships"] if record else 0,
        "person_count": record["person_count"] if record else 0,
        "company_count": record["company_count"] if record else 0,
        "health_count": record["health_count"] if record else 0,
        "finance_count": record["finance_count"] if record else 0,
        "contract_count": record["contract_count"] if record else 0,
        "sanction_count": record["sanction_count"] if record else 0,
        "election_count": record["election_count"] if record else 0,
        "amendment_count": record["amendment_count"] if record else 0,
        "embargo_count": record["embargo_count"] if record else 0,
        "education_count": record["education_count"] if record else 0,
        "convenio_count": record["convenio_count"] if record else 0,
        "laborstats_count": record["laborstats_count"] if record else 0,
        "offshore_entity_count": record["offshore_entity_count"] if record else 0,
        "offshore_officer_count": record["offshore_officer_count"] if record else 0,
        "global_pep_count": record["global_pep_count"] if record else 0,
        "cvm_proceeding_count": record["cvm_proceeding_count"] if record else 0,
        "expense_count": record["expense_count"] if record else 0,
        "pep_record_count": record["pep_record_count"] if record else 0,
        "expulsion_count": record["expulsion_count"] if record else 0,
        "leniency_count": record["leniency_count"] if record else 0,
        "international_sanction_count": record["international_sanction_count"] if record else 0,
        "gov_card_expense_count": record["gov_card_expense_count"] if record else 0,
        "gov_travel_count": record["gov_travel_count"] if record else 0,
        "bid_count": record["bid_count"] if record else 0,
        "fund_count": record["fund_count"] if record else 0,
        "dou_act_count": record["dou_act_count"] if record else 0,
        "tax_waiver_count": record["tax_waiver_count"] if record else 0,
        "municipal_finance_count": record["municipal_finance_count"] if record else 0,
        "declared_asset_count": record["declared_asset_count"] if record else 0,
        "party_membership_count": record["party_membership_count"] if record else 0,
        "barred_ngo_count": record["barred_ngo_count"] if record else 0,
        "bcb_penalty_count": record["bcb_penalty_count"] if record else 0,
        "labor_movement_count": record["labor_movement_count"] if record else 0,
        "legal_case_count": record["legal_case_count"] if record else 0,
        "judicial_case_count": record["judicial_case_count"] if record else 0,
        "source_document_count": record.get("source_document_count", 0) if record else 0,
        "ingestion_run_count": record.get("ingestion_run_count", 0) if record else 0,
        "temporal_violation_count": record.get("temporal_violation_count", 0) if record else 0,
        "cpi_count": record["cpi_count"] if record else 0,
        "inquiry_requirement_count": record["inquiry_requirement_count"] if record else 0,
        "inquiry_session_count": record["inquiry_session_count"] if record else 0,
        "municipal_bid_count": record["municipal_bid_count"] if record else 0,
        "municipal_contract_count": record["municipal_contract_count"] if record else 0,
        "municipal_gazette_act_count": record["municipal_gazette_act_count"] if record else 0,
        "data_sources": source_summary["universe_v1_sources"],
        "implemented_sources": source_summary["implemented_sources"],
        "loaded_sources": source_summary["loaded_sources"],
        "healthy_sources": source_summary["healthy_sources"],
        "stale_sources": source_summary["stale_sources"],
        "blocked_external_sources": source_summary["blocked_external_sources"],
        "quality_fail_sources": source_summary["quality_fail_sources"],
        "discovered_uningested_sources": source_summary["discovered_uningested_sources"],
    }

    _stats_cache = result
    _stats_cache_time = time.monotonic()
    return result


@router.get("/sources")
async def list_sources() -> dict[str, list[dict[str, Any]]]:
    sources = [entry.to_public_dict() for entry in load_source_registry() if entry.in_universe_v1]
    return {"sources": sources}


@router.get("/cache-stats")
async def cache_stats() -> dict[str, Any]:
    return cache.get_stats()


@router.delete("/cache")
async def flush_cache() -> dict[str, Any]:
    count = await cache.flush()
    return {"flushed_keys": count}


@router.get("/etl-progress")
async def etl_progress() -> dict[str, Any]:
    """Parse ETL log to show current progress."""
    import os
    import re
    from datetime import datetime

    log_path = os.environ.get("ETL_LOG_PATH", "/opt/bracc/cnpj-etl.log")
    result: dict[str, Any] = {
        "running": False,
        "phase": None,
        "current_file": None,
        "files_processed": 0,
        "total_files": 10,
        "percent": 0.0,
        "last_update": None,
        "phases": {
            1: "Building establishment lookup",
            2: "Loading companies + socios",
            3: "Creating SOCIO_DE relationships",
            4: "Post-optimization (indexes, constraints)",
        },
    }

    if not os.path.exists(log_path) or not os.path.isfile(log_path):
        return result

    try:
        stat = os.stat(log_path)
        if stat.st_size == 0:
            return result  # Empty file (e.g. Docker bind mount placeholder)

        import time as _time
        age_seconds = _time.time() - stat.st_mtime
        result["running"] = age_seconds < 10800  # updated in last 3h (each CSV file takes ~2h)
        result["log_age_seconds"] = int(age_seconds)

        with open(log_path, "r") as f:
            lines = f.readlines()

        # Parse phases and files
        current_phase = 0
        files_done = 0
        current_file = None
        last_ts = None

        for line in lines:
            if "Phase 1:" in line:
                current_phase = 1
            elif "Phase 2:" in line:
                current_phase = 2
            elif "Phase 3:" in line:
                current_phase = 3
            elif "Phase 4:" in line:
                current_phase = 4

            file_match = re.search(r"Reading (K3241\.\w+\.\w+\.\w+)", line)
            if file_match:
                current_file = file_match.group(1)
                files_done += 1

            ts_match = re.match(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", line)
            if ts_match:
                last_ts = ts_match.group(1)

        # In phase 1, each file is ~10% of the phase
        if current_phase == 1:
            result["percent"] = round((files_done / 10) * 25, 1)  # Phase 1 = 25% of total
        elif current_phase == 2:
            result["percent"] = 25 + 50  # rough estimate
        elif current_phase == 3:
            result["percent"] = 75 + 15
        elif current_phase == 4:
            result["percent"] = 95

        result["phase"] = current_phase
        result["current_file"] = current_file
        result["files_processed"] = files_done
        result["last_update"] = last_ts

    except Exception as e:
        result["error"] = str(e)

    return result
