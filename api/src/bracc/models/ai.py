from pydantic import BaseModel, Field
from typing import Any


class AIAnalysisRequest(BaseModel):
    entity_id: str = Field(description="The entity ID to analyze")
    include_relationships: bool = Field(default=True, description="Include relationship analysis")
    include_timeline: bool = Field(default=True, description="Include timeline generation")
    include_anomalies: bool = Field(default=True, description="Include anomaly detection")
    lang: str = Field(default="pt", description="Language for analysis")


class AIInsight(BaseModel):
    id: str
    type: str = Field(description="Insight type: relationship, timeline, anomaly, risk, summary")
    title: str
    description: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: list[str] = Field(default_factory=list)
    severity: str | None = Field(default=None, description="For risk insights: low, medium, high, critical")
    sources: list[str] = Field(default_factory=list)


class AIAnalysisResponse(BaseModel):
    entity_id: str
    summary: str
    insights: list[AIInsight] = Field(default_factory=list)
    risk_level: str = Field(description="low, medium, high, critical")
    risk_score: float = Field(ge=0.0, le=100.0)
    processed_at: str


class WebEnrichmentRequest(BaseModel):
    entity_id: str = Field(description="The entity ID to enrich")
    sources: list[str] = Field(
        default_factory=lambda: ["news", "social", "company_registry"],
        description="Sources to crawl: news, social, company_registry, all"
    )
    max_pages: int = Field(default=10, ge=1, le=50)


class WebEnrichmentResult(BaseModel):
    source: str
    url: str
    title: str
    snippet: str
    published_at: str | None
    relevance_score: float = Field(ge=0.0, le=1.0)


class WebEnrichmentResponse(BaseModel):
    entity_id: str
    results: list[WebEnrichmentResult]
    total_results: int
    processed_at: str


class InvestigativeScoreRequest(BaseModel):
    investigation_id: str = Field(description="The investigation ID to score")
    include_entity_scores: bool = Field(default=True)


class EntityScore(BaseModel):
    entity_id: str
    entity_name: str
    entity_type: str
    risk_score: float = Field(ge=0.0, le=100.0)
    risk_factors: list[str] = Field(default_factory=list)
    priority: int = Field(ge=1, description="Priority rank within investigation")


class InvestigativeScoreResponse(BaseModel):
    investigation_id: str
    investigation_title: str
    overall_risk_score: float = Field(ge=0.0, le=100.0)
    entity_count: int
    high_risk_entities: int
    entity_scores: list[EntityScore] = Field(default_factory=list)
    recommended_actions: list[str] = Field(default_factory=list)
    generated_at: str


class TimelineGenerationRequest(BaseModel):
    entity_id: str = Field(description="The entity ID to generate timeline for")
    start_date: str | None = Field(default=None, description="Start date (ISO format)")
    end_date: str | None = Field(default=None, description="End date (ISO format)")
    include_ai_insights: bool = Field(default=True)


class TimelineEventExt(BaseModel):
    id: str
    date: str
    label: str
    entity_type: str
    properties: dict[str, Any]
    sources: list[str]
    ai_annotation: str | None = Field(default=None, description="AI-generated annotation")


class TimelineGenerationResponse(BaseModel):
    entity_id: str
    events: list[TimelineEventExt]
    total: int
    next_cursor: str | None
    generated_at: str


class SourceVerificationRequest(BaseModel):
    entity_id: str = Field(description="The entity ID to verify sources for")
    source_urls: list[str] = Field(description="URLs to verify")


class VerifiedSource(BaseModel):
    url: str
    is_verified: bool
    source_name: str | None
    published_date: str | None
    author: str | None
    credibility_score: float = Field(ge=0.0, le=1.0)
    bias_indicator: str | None = Field(description="left, center, right, unknown")
    fact_check_result: str | None


class SourceVerificationResponse(BaseModel):
    entity_id: str
    verified_sources: list[VerifiedSource]
    total_verified: int
    processed_at: str


class TTSRequest(BaseModel):
    text: str = Field(max_length=5000)
    voice: str = Field(default="alloy")
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    format: str = Field(default="mp3")


class TTSResponse(BaseModel):
    audio_base64: str
    duration_seconds: float


class STTRequest(BaseModel):
    audio_base64: str
    language: str = Field(default="pt")


class STTResponse(BaseModel):
    text: str
    confidence: float
