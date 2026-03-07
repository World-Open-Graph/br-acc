"""AI and journalist tools API routes.

Provides endpoints for:
- AI-powered entity analysis
- Web enrichment and crawling
- Investigative scoring
- Timeline generation
- Source verification
- Text-to-speech and speech-to-text
- PDF dossier generation
- Alert subscriptions
"""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response
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
    STTRequest,
    STTResponse,
    TimelineGenerationRequest,
    TimelineGenerationResponse,
    TTSRequest,
    TTSResponse,
    WebEnrichmentRequest,
    WebEnrichmentResponse,
)
from bracc.services import ai_service, voice_service
from bracc.services.public_guard import enforce_entity_lookup_enabled
from bracc.services.scoring_service import (
    SuspicionScoreResult,
    compute_suspicion_score_safe,
    format_factor_explanation,
)

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
journalist_router = APIRouter(prefix="/api/v1/journalist", tags=["journalist"])
voice_router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# In-memory alert subscriptions store (production would use database)
_alert_subscriptions: dict[str, dict[str, str]] = {}


def _enforce_ai_enabled() -> None:
    """Check if AI services are enabled."""
    if not settings.ai_enabled:
        raise HTTPException(status_code=503, detail="AI services are not enabled")


def _enforce_journalist_tools() -> None:
    """Check if journalist tools are enabled."""
    if not settings.journalist_tools_enabled:
        raise HTTPException(status_code=503, detail="Journalist tools are not enabled")


def _enforce_voice_enabled() -> None:
    """Check if voice services are enabled."""
    if not settings.voice_enabled:
        raise HTTPException(status_code=503, detail="Voice services are not enabled")


@router.post("/analyze", response_model=AIAnalysisResponse)
async def analyze_entity(
    body: AIAnalysisRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> AIAnalysisResponse:
    """Perform AI-powered analysis of an entity.

    Analyzes an entity for risks, anomalies, and relationships.
    Results are cached for improved performance.
    """
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
    """Enrich entity data with web information.

    Crawls web sources for additional information about the entity.
    Supports news, company registry, and other sources.
    """
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
    """Get investigative scores for an investigation.

    Calculates risk scores for all entities in an investigation
    and provides aggregate statistics.
    """
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
    """Generate AI-enhanced timeline for an entity.

    Creates a chronological timeline of entity events with
    optional AI-generated insights and annotations.
    """
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
    """Get verified sources for an entity.

    Verifies and analyzes the credibility of provided URLs
    related to an entity.
    """
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
    """Convert text to speech.

    Converts text to spoken audio using AI voice synthesis.
    Supports multiple voices and adjustable speed.
    """
    _enforce_voice_enabled()

    try:
        audio_base64, duration = await voice_service.text_to_speech(
            text=body.text,
            voice=body.voice,
            speed=body.speed,
            format=body.format,
        )
    except voice_service.ConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except voice_service.VoiceServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return TTSResponse(
        audio_base64=audio_base64,
        duration_seconds=duration,
    )


@voice_router.post("/stt", response_model=STTResponse)
async def speech_to_text(
    body: STTRequest,
) -> STTResponse:
    """Convert speech to text.

    Transcribes audio to text using AI speech recognition.
    Returns confidence score with the transcription.
    """
    _enforce_voice_enabled()

    try:
        text, confidence = await voice_service.speech_to_text(
            audio_base64=body.audio_base64,
            language=body.language,
        )
    except voice_service.ConfigurationError as e:
        raise HTTPException(status_code=503, detail=str(e)) from e
    except voice_service.ConfidenceTooLowError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except voice_service.VoiceServiceError as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return STTResponse(
        text=text,
        confidence=confidence,
    )


@router.get("/status")
async def ai_status() -> dict[str, bool]:
    """Get AI services status.

    Returns the enabled/disabled status of all AI-related services.
    """
    return {
        "ai_enabled": settings.ai_enabled,
        "journalist_tools_enabled": settings.journalist_tools_enabled,
        "voice_enabled": settings.voice_enabled,
    }


# =============================================================================
# Scoring Endpoints
# =============================================================================


@router.get("/entity/{entity_id}/score")
async def get_entity_suspicion_score(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    include_history: Annotated[bool, Query()] = False,
    include_explanations: Annotated[bool, Query()] = True,
    lang: Annotated[str, Query()] = "pt",
) -> dict[str, Any]:
    """Get suspicion score for an entity.

    Computes a comprehensive suspicion score with explainable factors
    including sanctions, PEP connections, contract volume, offshore links,
    pattern flags, and temporal anomalies.

    Args:
        entity_id: Entity ID.
        include_history: Include historical scores if available.
        include_explanations: Include detailed factor explanations.
        lang: Language for explanations (pt/en).

    Returns:
        Suspicion score result with factors and explanations.
    """
    _enforce_ai_enabled()
    _enforce_journalist_tools()

    result = await compute_suspicion_score_safe(
        session,
        entity_id=entity_id,
        include_history=include_history,
    )

    response: dict[str, Any] = {
        "entity_id": result.entity_id,
        "entity_name": result.entity_name,
        "entity_type": result.entity_type,
        "suspicion_score": result.suspicion_score,
        "risk_level": result.risk_level,
        "confidence": result.confidence,
        "computed_at": result.computed_at,
    }

    if result.null_reason:
        response["null_reason"] = result.null_reason

    if include_explanations and result.factors:
        response["factors"] = [
            {
                "name": f.name,
                "score": f.score,
                "weight": f.weight,
                "weighted_score": round(f.weighted_score, 2),
                "explanation": f.explanation,
                "evidence": f.evidence,
                "sources": f.sources,
                "formatted_explanation": format_factor_explanation(f, lang),
            }
            for f in result.factors
        ]

    if include_history:
        response["score_history"] = result.score_history

    return response


# =============================================================================
# Journalist Tools - PDF Dossier
# =============================================================================


@journalist_router.get("/entity/{entity_id}/dossier")
async def generate_entity_dossier(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    lang: Annotated[Literal["pt", "en"], Query()] = "pt",
    include_charts: Annotated[bool, Query()] = True,
) -> Response:
    """Generate PDF dossier for an entity.

    Creates a comprehensive PDF report containing:
    - Entity basic information
    - Suspicion score with explanations
    - Connection network summary
    - Timeline of events
    - Risk factors and anomalies
    - Optional charts and visualizations

    Args:
        entity_id: Entity ID.
        lang: Language for the dossier.
        include_charts: Whether to include data visualizations.

    Returns:
        PDF file as response.
    """
    _enforce_journalist_tools()

    from bracc.services.pdf_service import render_investigation_pdf
    from bracc.services.neo4j_service import execute_query_single
    from bracc.services.public_guard import sanitize_public_properties, sanitize_props

    # Fetch entity data
    entity_record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if entity_record is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    node = entity_record["e"]
    labels = entity_record["entity_labels"]
    entity_name = str(node.get("name", "Unknown"))
    entity_type = labels[0] if labels else "Unknown"

    # Get suspicion score
    score_result = await compute_suspicion_score_safe(session, entity_id)

    # Build dossier content
    from bracc.models.investigation import InvestigationResponse

    # Create a mock investigation for PDF rendering
    dossier = InvestigationResponse(
        id=f"dossier-{entity_id}",
        title=f"Dossiê: {entity_name}",
        description=f"Análise completa de {entity_type}: {entity_name}",
        created_at=datetime.now(UTC).isoformat(),
        updated_at=datetime.now(UTC).isoformat(),
        entity_ids=[entity_id],
    )

    # Build entity list for PDF
    document = str(node.get("cpf", node.get("cnpj", "")))
    entities = [{
        "name": entity_name,
        "type": entity_type,
        "document": document,
    }]

    # Create annotations with score info
    annotations = []
    if score_result.suspicion_score is not None:
        score_text = f"Score de suspeita: {score_result.suspicion_score}/100"
        score_text += f"\nNível de risco: {score_result.risk_level}"
        score_text += f"\nConfiança: {score_result.confidence:.0%}"

        if score_result.factors:
            score_text += "\n\nFatores:"
            for factor in score_result.factors[:5]:
                score_text += f"\n- {factor.name}: {factor.score:.1f}"

        annotations.append({
            "created_at": score_result.computed_at,
            "text": score_text,
        })

    # Add risk factors as annotations
    for factor in score_result.factors:
        if factor.evidence:
            annotation_text = f"{factor.name}: {factor.explanation}"
            if factor.evidence:
                annotation_text += f"\nEvidências: {', '.join(factor.evidence[:3])}"
            annotations.append({
                "created_at": score_result.computed_at,
                "text": annotation_text,
            })

    # Tags for categorization
    tags = [{"name": entity_type, "color": "#2c3e50"}]
    if score_result.risk_level in ["high", "critical"]:
        tags.append({"name": "Alto Risco", "color": "#e74c3c"})

    pdf_bytes = await render_investigation_pdf(
        dossier,  # type: ignore[arg-type]
        annotations,  # type: ignore[arg-type]
        tags,  # type: ignore[arg-type]
        entities,
        lang=lang,
    )

    safe_name = "".join(c for c in entity_name if c.isalnum() or c in " _-")[:50]
    filename = f"dossier_{safe_name}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# =============================================================================
# Alert Subscription System
# =============================================================================


@journalist_router.post("/alerts/subscribe")
async def subscribe_to_alerts(
    entity_id: Annotated[str, Query(description="Entity ID to monitor")],
    email: Annotated[str, Query(description="Email for notifications")],
    alert_types: Annotated[
        str,
        Query(description="Comma-separated alert types: score_change, new_data, pattern_match"),
    ] = "score_change,new_data",
) -> dict[str, Any]:
    """Subscribe to entity alerts.

    Creates an idempotent subscription for entity monitoring.
    Multiple subscriptions with the same parameters are deduplicated.

    Args:
        entity_id: Entity to monitor.
        email: Email for notifications.
        alert_types: Types of alerts to receive.

    Returns:
        Subscription details.
    """
    _enforce_journalist_tools()

    # Create subscription key for idempotency
    subscription_key = hashlib.sha256(
        f"{entity_id}:{email}:{alert_types}".encode()
    ).hexdigest()[:16]

    # Check if subscription already exists (idempotent)
    if subscription_key in _alert_subscriptions:
        return {
            "subscription_id": subscription_key,
            "status": "already_exists",
            "entity_id": entity_id,
            "email": email,
            "alert_types": alert_types.split(","),
            "created_at": _alert_subscriptions[subscription_key]["created_at"],
        }

    # Create new subscription
    from datetime import datetime, timezone

    subscription = {
        "subscription_id": subscription_key,
        "entity_id": entity_id,
        "email": email,
        "alert_types": alert_types.split(","),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }

    _alert_subscriptions[subscription_key] = subscription

    return {
        "subscription_id": subscription_key,
        "status": "created",
        **subscription,
    }


@journalist_router.delete("/alerts/unsubscribe/{subscription_id}")
async def unsubscribe_from_alerts(
    subscription_id: str,
) -> dict[str, Any]:
    """Unsubscribe from entity alerts.

    Args:
        subscription_id: Subscription ID to cancel.

    Returns:
        Unsubscription confirmation.
    """
    _enforce_journalist_tools()

    if subscription_id not in _alert_subscriptions:
        raise HTTPException(status_code=404, detail="Subscription not found")

    subscription = _alert_subscriptions.pop(subscription_id)

    return {
        "subscription_id": subscription_id,
        "status": "cancelled",
        "entity_id": subscription["entity_id"],
        "email": subscription["email"],
        "cancelled_at": datetime.now(UTC).isoformat(),
    }


@journalist_router.get("/alerts/subscriptions")
async def list_subscriptions(
    email: Annotated[str | None, Query()] = None,
    entity_id: Annotated[str | None, Query()] = None,
) -> dict[str, Any]:
    """List alert subscriptions.

    Args:
        email: Filter by email.
        entity_id: Filter by entity.

    Returns:
        List of matching subscriptions.
    """
    _enforce_journalist_tools()

    subscriptions = list(_alert_subscriptions.values())

    if email:
        subscriptions = [s for s in subscriptions if s["email"] == email]

    if entity_id:
        subscriptions = [s for s in subscriptions if s["entity_id"] == entity_id]

    return {
        "subscriptions": subscriptions,
        "total": len(subscriptions),
    }


# Need to import datetime at module level for the new endpoints
from datetime import datetime, timezone as tz
