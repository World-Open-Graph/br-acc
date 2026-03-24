"""Public HTTP routes for emendas."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from neo4j import AsyncSession

from bracc.dependencies import get_session

from . import controller
from .model import EmendasListResponse

router = APIRouter(prefix="/api/v1/emendas", tags=["emendas"])


@router.get("/", response_model=EmendasListResponse)
async def list_emendas_tesouro(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EmendasListResponse:
    """Expose Tesouro emendas listing with pagination."""
    return await controller.list_emendas_tesouro(session, skip, limit)
