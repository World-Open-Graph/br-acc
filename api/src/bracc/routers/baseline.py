from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from bracc.config import settings
from bracc.dependencies import get_session
from bracc.models.baseline import BaselineResponse
from bracc.services.baseline_service import BASELINE_QUERIES, run_all_baselines, run_baseline
from bracc.services.public_guard import enforce_entity_lookup_enabled

router = APIRouter(prefix="/api/v1/baseline", tags=["baseline"])


@router.get("/{entity_id}", response_model=BaselineResponse)
async def get_baseline_for_entity(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    dimension: Annotated[str | None, Query()] = None,
) -> BaselineResponse:
    enforce_entity_lookup_enabled()
    if dimension:
        if dimension not in BASELINE_QUERIES:
            available = list(BASELINE_QUERIES.keys())
            app_env = settings.app_env.strip().lower()
            detail = (
                "Invalid dimension"
                if app_env in ("prod", "production")
                else f"Invalid dimension: {dimension}. Available: {available}"
            )
            raise HTTPException(status_code=400, detail=detail)
        results = await run_baseline(session, dimension, entity_id)
    else:
        results = await run_all_baselines(session, entity_id)

    return BaselineResponse(
        entity_id=entity_id,
        comparisons=results,
        total=len(results),
    )
