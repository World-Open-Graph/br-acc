from typing import Annotated

from fastapi import APIRouter, Depends, Query
from neo4j import AsyncSession

from bracc.dependencies import get_session

from . import controller
from .model import BaselineResponse

router = APIRouter(prefix="/api/v1/baseline", tags=["baseline"])


@router.get("/{entity_id}", response_model=BaselineResponse)
async def get_baseline_for_entity(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    dimension: Annotated[str | None, Query()] = None,
) -> BaselineResponse:
    return await controller.get_baseline_for_entity(entity_id, session, dimension)