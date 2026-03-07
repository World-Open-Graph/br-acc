from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncDriver, AsyncSession

from bracc.config import settings
from bracc.dependencies import get_driver, get_session
from bracc.models.ai import (
    AIAnalysisRequest,
    AIAnalysisResponse,
    InvestigativeScoreRequest,
    InvestigativeScoreResponse,
    SourceVerificationRequest,
    SourceVerificationResponse,
    TimelineGenerationRequest,
    TimelineGenerationResponse,
    TTSRequest,
    TTSResponse,
    STTRequest,
    STTResponse,
    WebEnrichmentRequest,
    WebEnrichmentResponse,
)
from bracc.services import ai_service, voice_service
from bracc.services.public_guard import enforce_entity_lookup_enabled

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
journalist_router = APIRouter(prefix="/api/v1/journalist", tags=["journalist"])
voice_router = APIRouter(prefix="/api/v1/voice", tags=["voice"])


def _enforce_ai_enabled() -> None:
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI services are not enabled")


def _enforce_journalist_tools() -> None:
    if not settings.journalist_tools_enabled:
        raise HTTPException(status_code=503, detail="Journalist tools are not enabled")


def _enforce_voice_enabled() -> None:
    if not settings.voice_enabled:
        raise HTTPException(status_code=503, detail="Voice services are not enabled")


@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_entity(
    body: AIAnalysisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AIAnalysisResponse:
    """Perform AI-powered analysis of an entity."""
    _enforce_ai_enabled()
    if settings.public_mode:
        enforce_entity_lookup_enabled()

    return await ai_service.analyze_entity(
        session,
        entity_id=body.entity_id,
        include_relationships=body.include_relationships,
        include_timeline=body.include_timeline,
        include_anomalies=body.include_anomalies,
        lang=body.lang,
    )


@router.post("/enrich", response_model=WebEnrichmentResponse)
async def enrich_entity(
    body: WebEnrichmentRequest,
    driver: Annotated[AsyncDriver, Depends(get_driver)],
) -> WebEnrichmentResponse:
    """Enrich entity data with web information."""
    _enforce_ai_enabled()
    if settings.public_mode:
        enforce_entity_lookup_enabled()

    async with driver.session(database=settings.neo4j_database) as session:
        return await ai_service.get_web_enrichment(
            entity_id=body.entity_id,
            sources=body.sources,
            max_pages=body.max_pages,
        )


@router.get("/score/{investigation_id}", response_model=InvestigativeScoreResponse)
async def get_investigative_scores(
    investigation_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_entity_scores: Annotated[bool, Query()] = True,
) -> InvestigativeScoreResponse:
    """Get investigative scores for an investigation."""
    _enforce_ai_enabled()
    _enforce_journalist_tools()

    return await ai_service.get_investigative_scores(
        session,
        investigation_id=investigation_id,
        include_entity_scores=include_entity_scores,
    )


@router.post("/timeline", response_model=TimelineGenerationResponse)
async def generate_timeline(
    body: TimelineGenerationRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TimelineGenerationResponse:
    """Generate AI-enhanced timeline for an entity."""
    _enforce_ai_enabled()

    return await ai_service.generate_timeline(
        session,
        entity_id=body.entity_id,
        start_date=body.start_date,
        end_date=body.end_date,
        include_ai_insights=body.include_ai_insights,
    )


@journalist_router.get("/sources/{entity_id}", response_model=SourceVerificationResponse)
async def get_verified_sources(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    urls: Annotated[str, Query(description="Comma-separated URLs to verify")],
) -> SourceVerificationResponse:
    """Get verified sources for an entity."""
    _enforce_journalist_tools()

    source_urls = [u.strip() for u in urls.split(",") if u.strip()]
    if not source_urls:
        raise HTTPException(status_code=400, detail="No URLs provided")

    return await ai_service.verify_sources(
        session,
        entity_id=entity_id,
        source_urls=source_urls,
    )


@voice_router.post("/tts", response_model=TTSResponse)
async def text_to_speech(
    body: TTSRequest,
) -> TTSResponse:
    """Convert text to speech."""
    _enforce_voice_enabled()

    audio_base64, duration = await voice_service.text_to_speech(
        text=body.text,
        voice=body.voice,
        speed=body.speed,
        format=body.format,
    )

    return TTSResponse(
        audio_base64=audio_base64,
        duration_seconds=duration,
    )


@voice_router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    body: STTRequest,
) -> STTResponse:
    """Convert speech to text."""
    _enforce_voice_enabled()

    text, confidence = await voice_service.speech_to_text(
        audio_base64=body.audio_base64,
        language=body.language,
    )

    return STTResponse(
        text=text,
        confidence=confidence,
    )


@router.get("/status")
async def ai_status() -> dict[str, bool]:
    """Get AI services status."""
    return {
        "ai_enabled": settings.ai_enabled,
        "journalist_tools_enabled": settings.journalist_tools_enabled,
        "voice_enabled": settings.voice_enabled,
    }
