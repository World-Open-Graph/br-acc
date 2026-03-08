from typing import Annotated

from fastapi import Depends, HTTPException, Query
from neo4j import AsyncSession

from bracc.config import settings
from bracc.dependencies import get_session
from bracc.services.baseline_service import BASELINE_QUERIES, run_all_baselines, run_baseline
from bracc.services.public_guard import enforce_entity_lookup_enabled

from .model import BaselineResponse

async def get_baseline_for_entity(
    entity_id: str,
    session: AsyncSession,
    dimension: str | None = None,
) -> BaselineResponse:
    enforce_entity_lookup_enabled()

    if dimension:
        _validate_dimension(dimension)
        results = await run_baseline(session, dimension, entity_id)
    else:
        results = await run_all_baselines(session, entity_id)

    return BaselineResponse(
        entity_id=entity_id,
        comparisons=results,
        total=len(results),
    )
def _validate_dimension(dim: str) -> None:
    if dim not in BASELINE_QUERIES:
        available = list(BASELINE_QUERIES.keys())
        env = settings.app_env.strip().lower()
        if env in ("prod", "production"):
            message = "Invalid dimension"
        else:
            message = f"Invalid dimension: {dim}. Available: {available}"
        raise HTTPException(status_code=400, detail=message)
