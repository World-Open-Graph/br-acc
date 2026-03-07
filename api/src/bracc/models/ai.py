"""Pydantic models for AI-related API endpoints.

Models for:
- AI entity analysis
- Web enrichment
- Investigative scoring
- Timeline generation
- Source verification
- Voice (TTS/STT)
- PDF dossier generation
- Alert subscriptions
"""

from pydantic import BaseModel, Field
from typing import Any


class AIAnalysisRequest(BaseModel):
    """Request model for AI entity analysis.

    Attributes:
        entity_id: The entity ID to analyze.
        include_relationships: Include relationship analysis.
        include_timeline: Include timeline generation.
        include_anomalies: Include anomaly detection.
        lang: Language for analysis output.
    """

    entity_id: str = Field(description="The entity ID to analyze")
    include_relationships: bool = Field(
        default=True,
        description="Include relationship analysis",
    )
    include_timeline: bool = Field(
        default=True,
        description="Include timeline generation",
    )
    include_anomalies: bool = Field(
        default=True,
        description="Include anomaly detection",
    )
    lang: str = Field(default="pt", description="Language for analysis")


class AIInsight(BaseModel):
    """Individual AI insight/observation.

    Attributes:
        id: Unique insight ID.
        type: Insight type (relationship, timeline, anomaly, risk, summary).
        title: Insight title.
        description: Detailed description.
        confidence: Confidence score (0-1).
        evidence: Supporting evidence strings.
        severity: Risk severity level (low, medium, high, critical).
        sources: Data sources contributing to this insight.
    """

    id: str
    type: str = Field(
        description="Insight type: relationship, timeline, anomaly, risk, summary",
    )
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    severity: str | None = Field(
        default=None,
        description="For risk insights: low, medium, high, critical",
    )
    sources: list[str] = Field(default_factory=list)


class AIAnalysisResponse(BaseModel):
    """Response model for AI entity analysis.

    Attributes:
        entity_id: Analyzed entity ID.
        summary: Text summary with source citations.
        insights: List of AI-generated insights.
        risk_level: Overall risk level classification.
        risk_score: Numerical risk score (0-100).
        processed_at: ISO timestamp.
    """

    entity_id: str
    summary: str
    insights: list[AIInsight] = Field(default_factory=list)
    risk_level: str = Field(description="low, medium, high, critical")
    risk_score: float = Field(ge=0.0, le=100.0)
    processed_at: str


class WebEnrichmentRequest(BaseModel):
    """Request model for web enrichment.

    Attributes:
        entity_id: Entity to enrich.
        sources: Sources to crawl (news, social, company_registry, all).
        max_pages: Maximum pages to crawl per source.
    """

    entity_id: str = Field(description="The entity ID to enrich")
    sources: list[str] = Field(
        default_factory=lambda: ["news", "social", "company_registry"],
        description="Sources to crawl: news, social, company_registry, all",
    )
    max_pages: int = Field(default=10, ge=1, le=50)


class WebEnrichmentResult(BaseModel):
    """Single web enrichment result.

    Attributes:
        source: Source type.
        url: Result URL.
        title: Result title.
        snippet: Content snippet.
        published_at: Publication date if available.
        relevance_score: Calculated relevance (0-1).
        last_crawled_at: When this result was crawled.
        content_hash: Hash for deduplication.
    """

    source: str
    url: str
    title: str
    snippet: str
    published_at: str | None = None
    relevance_score: float = Field(ge=0.0, le=1.0)
    last_crawled_at: str | None = None
    content_hash: str | None = None


class WebEnrichmentResponse(BaseModel):
    """Response model for web enrichment.

    Attributes:
        entity_id: Enriched entity ID.
        results: List of enrichment results.
        total_results: Total number of results.
        deduplicated_count: Number of duplicates removed.
        processed_at: ISO timestamp.
        source_citations: List of source URLs.
    """

    entity_id: str
    results: list[WebEnrichmentResult]
    total_results: int
    deduplicated_count: int = 0
    processed_at: str
    source_citations: list[str] = Field(default_factory=list)


class InvestigativeScoreRequest(BaseModel):
    """Request model for investigative scoring.

    Attributes:
        investigation_id: Investigation to score.
        include_entity_scores: Include individual entity scores.
    """

    investigation_id: str = Field(description="The investigation ID to score")
    include_entity_scores: bool = Field(default=True)


class EntityScore(BaseModel):
    """Score for a single entity in investigation.

    Attributes:
        entity_id: Entity ID.
        entity_name: Entity name.
        entity_type: Entity type label.
        risk_score: Risk score (0-100).
        risk_factors: List of risk factor identifiers.
        priority: Priority rank within investigation.
        score_explanation: Human-readable score explanation.
        score_history: Historical scores if available.
    """

    entity_id: str
    entity_name: str
    entity_type: str
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_factors: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, description="Priority rank within investigation")
    score_explanation: str | None = None
    score_history: list[dict[str, Any]] = Field(default_factory=list)


class InvestigativeScoreResponse(BaseModel):
    """Response model for investigative scores.

    Attributes:
        investigation_id: Investigation ID.
        investigation_title: Investigation title.
        overall_risk_score: Aggregate risk score (0-100).
        entity_count: Number of entities in investigation.
        high_risk_entities: Count of high-risk entities.
        entity_scores: Individual entity scores.
        recommended_actions: Suggested follow-up actions.
        generated_at: ISO timestamp.
    """

    investigation_id: str
    investigation_title: str
    overall_risk_score: float = Field(ge=0.0, le=100.0)
    entity_count: int
    high_risk_entities: int
    entity_scores: list[EntityScore] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    generated_at: str


class TimelineGenerationRequest(BaseModel):
    """Request model for timeline generation.

    Attributes:
        entity_id: Entity to generate timeline for.
        start_date: Optional start date filter (ISO format).
        end_date: Optional end date filter (ISO format).
        include_ai_insights: Include AI-generated annotations.
    """

    entity_id: str = Field(description="The entity ID to generate timeline for")
    start_date: str | None = Field(
        default=None,
        description="Start date (ISO format)",
    )
    end_date: str | None = Field(
        default=None,
        description="End date (ISO format)",
    )
    include_ai_insights: bool = Field(default=True)


class TimelineEventExt(BaseModel):
    """Extended timeline event with AI annotations.

    Attributes:
        id: Event ID.
        date: Event date.
        label: Event label/description.
        entity_type: Type of entity involved.
        properties: Additional event properties.
        sources: Data sources.
        ai_annotation: AI-generated annotation/explanation.
        why_explanation: Detailed "WHY" explanation for the event.
    """

    id: str
    date: str
    label: str
    entity_type: str
    properties: dict[str, Any]
    sources: list[str]
    ai_annotation: str | None = Field(
        default=None,
        description="AI-generated annotation",
    )
    why_explanation: str | None = None


class TimelineGenerationResponse(BaseModel):
    """Response model for timeline generation.

    Attributes:
        entity_id: Entity ID.
        events: Timeline events.
        total: Total event count.
        next_cursor: Pagination cursor if more events available.
        generated_at: ISO timestamp.
    """

    entity_id: str
    events: list[TimelineEventExt]
    total: int
    next_cursor: str | None
    generated_at: str


class SourceVerificationRequest(BaseModel):
    """Request model for source verification.

    Attributes:
        entity_id: Entity to verify sources for.
        source_urls: URLs to verify.
    """

    entity_id: str = Field(description="The entity ID to verify sources for")
    source_urls: list[str] = Field(description="URLs to verify")


class VerifiedSource(BaseModel):
    """Single verified source result.

    Attributes:
        url: Source URL.
        is_verified: Whether URL is accessible.
        source_name: Extracted domain/source name.
        published_date: Publication date if extractable.
        author: Author if extractable.
        credibility_score: Calculated credibility (0-1).
        bias_indicator: Political bias indicator.
        fact_check_result: Fact-check verification result.
        verification_timestamp: When verification occurred.
    """

    url: str
    is_verified: bool
    source_name: str | None = None
    published_date: str | None = None
    author: str | None = None
    credibility_score: float = Field(ge=0.0, le=1.0)
    bias_indicator: str | None = Field(
        default=None,
        description="left, center, right, unknown",
    )
    fact_check_result: str | None = None
    verification_timestamp: str | None = None


class SourceVerificationResponse(BaseModel):
    """Response model for source verification.

    Attributes:
        entity_id: Entity ID.
        verified_sources: List of verification results.
        total_verified: Count of successfully verified sources.
        total_failed: Count of failed verifications.
        processed_at: ISO timestamp.
    """

    entity_id: str
    verified_sources: list[VerifiedSource]
    total_verified: int
    total_failed: int = 0
    processed_at: str


class TTSRequest(BaseModel):
    """Request model for text-to-speech.

    Attributes:
        text: Text to convert (max 5000 chars).
        voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer).
        speed: Speech speed (0.25 to 4.0).
        format: Output format (mp3, opus, aac, flac).
        language: Optional language hint.
    """

    text: str = Field(max_length=5000)
    voice: str = Field(default="alloy")
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    format: str = Field(default="mp3")
    language: str | None = None


class TTSResponse(BaseModel):
    """Response model for text-to-speech.

    Attributes:
        audio_base64: Base64-encoded audio data.
        duration_seconds: Audio duration.
        detected_language: Auto-detected language.
    """

    audio_base64: str
    duration_seconds: float
    detected_language: str | None = None


class STTRequest(BaseModel):
    """Request model for speech-to-text.

    Attributes:
        audio_base64: Base64-encoded audio data.
        language: Expected language code.
    """

    audio_base64: str
    language: str = Field(default="pt")


class STTResponse(BaseModel):
    """Response model for speech-to-text.

    Attributes:
        text: Transcribed text.
        confidence: Confidence score (0-1).
        language: Detected/used language.
    """

    text: str
    confidence: float
    language: str = "pt"


class SuspicionScoreRequest(BaseModel):
    """Request model for suspicion score.

    Attributes:
        entity_id: Entity to score.
        include_history: Include score history.
        include_explanations: Include detailed factor explanations.
        lang: Language for explanations.
    """

    entity_id: str
    include_history: bool = False
    include_explanations: bool = True
    lang: str = "pt"


class ScoreFactorDetail(BaseModel):
    """Detailed scoring factor information.

    Attributes:
        name: Factor name.
        score: Raw score (0-100).
        weight: Factor weight.
        weighted_score: Weighted contribution.
        explanation: Human-readable explanation.
        evidence: Supporting evidence.
        sources: Data sources.
        formatted_explanation: Pre-formatted explanation.
    """

    name: str
    score: float
    weight: float
    weighted_score: float
    explanation: str
    evidence: list[str]
    sources: list[str]
    formatted_explanation: str


class SuspicionScoreResponse(BaseModel):
    """Response model for suspicion score.

    Attributes:
        entity_id: Entity ID.
        entity_name: Entity name.
        entity_type: Entity type.
        suspicion_score: Overall score (0-100) or null.
        risk_level: Risk classification.
        confidence: Score confidence (0-1).
        factors: Detailed factor breakdown.
        score_history: Historical scores.
        computed_at: ISO timestamp.
        null_reason: Reason if score is null.
    """

    entity_id: str
    entity_name: str
    entity_type: str
    suspicion_score: float | None
    risk_level: str
    confidence: float
    factors: list[ScoreFactorDetail] = Field(default_factory=list)
    score_history: list[dict[str, Any]] = Field(default_factory=list)
    computed_at: str
    null_reason: str | None = None


class DossierRequest(BaseModel):
    """Request model for PDF dossier generation.

    Attributes:
        entity_id: Entity to generate dossier for.
        lang: Language for dossier.
        include_charts: Include data visualizations.
        include_connections: Include connection graph.
        include_timeline: Include timeline section.
    """

    entity_id: str
    lang: str = "pt"
    include_charts: bool = True
    include_connections: bool = True
    include_timeline: bool = True


class AlertSubscriptionRequest(BaseModel):
    """Request model for alert subscription.

    Attributes:
        entity_id: Entity to monitor.
        email: Email for notifications.
        alert_types: Types of alerts to receive.
    """

    entity_id: str
    email: str
    alert_types: list[str] = Field(default_factory=lambda: ["score_change", "new_data"])


class AlertSubscriptionResponse(BaseModel):
    """Response model for alert subscription.

    Attributes:
        subscription_id: Unique subscription ID.
        status: Subscription status (created, already_exists).
        entity_id: Monitored entity.
        email: Notification email.
        alert_types: Enabled alert types.
        created_at: ISO timestamp.
    """

    subscription_id: str
    status: str
    entity_id: str
    email: str
    alert_types: list[str]
    created_at: str


class AlertUnsubscribeResponse(BaseModel):
    """Response model for alert unsubscription.

    Attributes:
        subscription_id: Cancelled subscription ID.
        status: Cancellation status.
        entity_id: Entity that was monitored.
        email: Email address.
        cancelled_at: ISO timestamp.
    """

    subscription_id: str
    status: str
    entity_id: str
    email: str
    cancelled_at: str


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics.

    Attributes:
        enabled: Whether caching is enabled.
        size: Current cache size.
        max_size: Maximum cache capacity.
        expired_entries: Count of expired entries.
        hit_rate: Cache hit rate if available.
    """

    enabled: bool
    size: int
    max_size: int
    expired_entries: int
    hit_rate: float | None = None
