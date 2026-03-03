from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncDriver, AsyncSession
from starlette.requests import Request

from bracc.config import settings
from bracc.dependencies import get_driver, get_intelligence_provider, get_session
from bracc.middleware.rate_limit import limiter
from bracc.models.pattern import PatternResponse, PatternResult
from bracc.services.intelligence_provider import IntelligenceProvider
from bracc.services.public_guard import enforce_entity_lookup_enabled

router = APIRouter(prefix="/api/v1/patterns", tags=["patterns"])

_PATTERN_ENGINE_DISABLED_DETAIL = (
    "Pattern engine temporarily unavailable pending validation."
)


def _enforce_patterns_enabled() -> None:
    if not settings.patterns_enabled:
        raise HTTPException(status_code=503, detail=_PATTERN_ENGINE_DISABLED_DETAIL)


async def run_all_patterns(
    driver: AsyncDriver,
    entity_id: str | None = None,
    lang: str = "pt",
    include_probable: bool = False,
    provider: IntelligenceProvider | None = None,
) -> list[PatternResult]:
    intelligence = provider or get_intelligence_provider()
    return await intelligence.run_all_patterns(
        driver,
        entity_id=entity_id,
        lang=lang,
        include_probable=include_probable,
    )


async def run_pattern(
    session: AsyncSession,
    pattern_id: str,
    entity_id: str | None = None,
    lang: str = "pt",
    include_probable: bool = False,
    provider: IntelligenceProvider | None = None,
) -> list[PatternResult]:
    intelligence = provider or get_intelligence_provider()
    return await intelligence.run_pattern(
        session,
        pattern_id=pattern_id,
        entity_id=entity_id,
        lang=lang,
        include_probable=include_probable,
    )


@router.get("/{entity_id}", response_model=PatternResponse)
@limiter.limit("30/minute")
async def get_patterns_for_entity(
    request: Request,
    entity_id: str,
    driver: Annotated[AsyncDriver, Depends(get_driver)],
    provider: Annotated[IntelligenceProvider, Depends(get_intelligence_provider)],
    lang: Annotated[str, Query()] = "pt",
    include_probable: Annotated[bool, Query()] = False,
) -> PatternResponse:
    _enforce_patterns_enabled()
    if settings.public_mode:
        enforce_entity_lookup_enabled()
    results = await run_all_patterns(
        driver,
        entity_id,
        lang,
        include_probable=include_probable,
        provider=provider,
    )
    return PatternResponse(
        entity_id=entity_id,
        patterns=results,
        total=len(results),
    )


@router.get("/{entity_id}/{pattern_name}", response_model=PatternResponse)
@limiter.limit("30/minute")
async def get_specific_pattern(
    request: Request,
    entity_id: str,
    pattern_name: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[IntelligenceProvider, Depends(get_intelligence_provider)],
    lang: Annotated[str, Query()] = "pt",
    include_probable: Annotated[bool, Query()] = False,
) -> PatternResponse:
    _enforce_patterns_enabled()
    if settings.public_mode:
        enforce_entity_lookup_enabled()
    available = [row["id"] for row in provider.list_patterns()]
    if pattern_name not in set(available):
        app_env = settings.app_env.strip().lower()
        detail = (
            "Pattern not found"
            if app_env in ("prod", "production")
            else f"Pattern not found: {pattern_name}. Available: {available}"
        )
        raise HTTPException(status_code=404, detail=detail)
    results = await run_pattern(
        session,
        pattern_name,
        entity_id,
        lang,
        include_probable=include_probable,
        provider=provider,
    )
    return PatternResponse(
        entity_id=entity_id,
        patterns=results,
        total=len(results),
    )


@router.get("/", response_model=dict[str, list[dict[str, str]]])
async def list_patterns(
    provider: Annotated[IntelligenceProvider, Depends(get_intelligence_provider)],
) -> dict[str, list[dict[str, str]]]:
    _enforce_patterns_enabled()
    return {"patterns": provider.list_patterns()}
