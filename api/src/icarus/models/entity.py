from typing import Any

from pydantic import BaseModel


class SourceAttribution(BaseModel):
    database: str
    record_id: str | None = None
    extracted_at: str | None = None


class EntityResponse(BaseModel):
    id: str
    type: str
    entity_label: str | None = None
    identity_quality: str | None = None
    properties: dict[str, str | float | int | bool | None]
    sources: list[SourceAttribution]
    is_pep: bool = False
    exposure_tier: str = "public_safe"


class ConnectionResponse(BaseModel):
    source_id: str
    target_id: str
    relationship_type: str
    properties: dict[str, str | float | int | bool | None]
    confidence: float = 1.0
    sources: list[SourceAttribution]
    exposure_tier: str = "public_safe"


class EntityWithConnections(BaseModel):
    entity: EntityResponse
    connections: list[ConnectionResponse]
    connected_entities: list[EntityResponse]


class ExposureFactor(BaseModel):
    name: str
    value: float
    percentile: float
    weight: float
    sources: list[str]


class ExposureResponse(BaseModel):
    entity_id: str
    exposure_index: float
    factors: list[ExposureFactor]
    peer_group: str
    peer_count: int
    sources: list[SourceAttribution]
    intelligence_tier: str = "community"


class TimelineEvent(BaseModel):
    id: str
    date: str
    label: str
    entity_type: str
    properties: dict[str, Any]
    sources: list[SourceAttribution]


class TimelineResponse(BaseModel):
    entity_id: str
    events: list[TimelineEvent]
    total: int
    next_cursor: str | None
