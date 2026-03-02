import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession

from bracc.constants import PEP_ROLES
from bracc.dependencies import get_intelligence_provider, get_session
from bracc.models.entity import (
    ConnectionResponse,
    EntityResponse,
    EntityWithConnections,
    ExposureResponse,
    SourceAttribution,
    TimelineEvent,
    TimelineResponse,
)
from bracc.services.intelligence_provider import IntelligenceProvider
from bracc.services.neo4j_service import execute_query, execute_query_single, sanitize_props
from bracc.services.public_guard import (
    enforce_entity_lookup_enabled,
    enforce_entity_lookup_policy,
    enforce_person_access_policy,
    has_person_labels,
    infer_exposure_tier,
    sanitize_public_properties,
    should_hide_person_entities,
)

router = APIRouter(prefix="/api/v1/entity", tags=["entity"])

CPF_PATTERN = re.compile(r"^\d{11}$")
CNPJ_PATTERN = re.compile(r"^\d{14}$")


def _clean_identifier(raw: str) -> str:
    return re.sub(r"[.\-/]", "", raw)


def _is_pep(properties: dict[str, Any]) -> bool:
    role = str(properties.get("role", "")).lower()
    return any(keyword in role for keyword in PEP_ROLES)


def _infer_identity_quality(
    props: dict[str, Any],
    labels: list[str],
) -> str | None:
    if "identity_quality" in props and props["identity_quality"]:
        return str(props["identity_quality"])

    label_set = set(labels)
    if "Partner" in label_set:
        return "partial"
    if "Person" in label_set:
        cpf = props.get("cpf")
        if isinstance(cpf, str) and re.match(r"^\d{3}\.\d{3}\.\d{3}-\d{2}$", cpf):
            return "strong"
        return "unknown"
    return None


def _node_to_entity(
    node: Any, labels: list[str], entity_id: str
) -> EntityResponse:
    props = dict(node)
    entity_type = labels[0].lower() if labels else "unknown"
    entity_label = labels[0] if labels else None
    sources = []
    if "source" in props:
        source_val = props.pop("source")
        if isinstance(source_val, list):
            sources = [SourceAttribution(database=s) for s in source_val]
        elif isinstance(source_val, str):
            sources = [SourceAttribution(database=source_val)]
    identity_quality = _infer_identity_quality(props, labels)
    return EntityResponse(
        id=entity_id,
        type=entity_type,
        entity_label=entity_label,
        identity_quality=identity_quality,
        properties=sanitize_public_properties(sanitize_props(props)),
        sources=sources,
        is_pep=_is_pep(props),
        exposure_tier=infer_exposure_tier(labels),
    )


def _format_cpf(digits: str) -> str:
    """Format an 11-digit string as CPF: 123.456.789-00."""
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


def _format_cnpj(digits: str) -> str:
    """Format a 14-digit string as CNPJ: 12.345.678/0001-00."""
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


@router.get("/{cpf_or_cnpj}", response_model=EntityResponse)
async def get_entity(
    cpf_or_cnpj: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EntityResponse:
    enforce_entity_lookup_policy(cpf_or_cnpj)
    identifier = _clean_identifier(cpf_or_cnpj)

    if not CPF_PATTERN.match(identifier) and not CNPJ_PATTERN.match(identifier):
        raise HTTPException(status_code=400, detail="Invalid CPF or CNPJ format")

    if CPF_PATTERN.match(identifier):
        identifier_formatted = _format_cpf(identifier)
    else:
        identifier_formatted = _format_cnpj(identifier)

    record = await execute_query_single(
        session,
        "entity_lookup",
        {"identifier": identifier, "identifier_formatted": identifier_formatted},
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    enforce_person_access_policy(record["entity_labels"])

    return _node_to_entity(
        record["e"], record["entity_labels"], record["entity_id"]
    )


@router.get("/by-element-id/{element_id}", response_model=EntityResponse)
async def get_entity_by_element_id(
    element_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> EntityResponse:
    enforce_entity_lookup_enabled()
    record = await execute_query_single(
        session, "entity_by_element_id", {"element_id": element_id}
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    enforce_person_access_policy(record["entity_labels"])

    return _node_to_entity(
        record["e"], record["entity_labels"], element_id
    )


@router.get("/{entity_id}/exposure", response_model=ExposureResponse)
async def get_entity_exposure(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    provider: Annotated[IntelligenceProvider, Depends(get_intelligence_provider)],
) -> ExposureResponse:
    enforce_entity_lookup_enabled()
    return await provider.get_entity_exposure(session, entity_id)


@router.get("/{entity_id}/timeline", response_model=TimelineResponse)
async def get_entity_timeline(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> TimelineResponse:
    enforce_entity_lookup_enabled()
    records = await execute_query(
        session,
        "entity_timeline",
        {"entity_id": entity_id, "cursor": cursor, "limit": limit},
    )

    events: list[TimelineEvent] = []
    for record in records:
        lbls: list[str] = record["lbls"]
        entity_type = lbls[0] if lbls else "unknown"
        props: dict[str, Any] = dict(record["props"])
        event_date: str = record["event_date"]

        label = props.get("object", props.get("type", entity_type))

        events.append(TimelineEvent(
            id=record["id"],
            date=event_date,
            label=str(label),
            entity_type=entity_type,
            properties=sanitize_public_properties(sanitize_props(props)),
            sources=[SourceAttribution(database="neo4j_graph")],
        ))

    next_cursor = events[-1].date if len(events) == limit else None

    return TimelineResponse(
        entity_id=entity_id,
        events=events,
        total=len(events),
        next_cursor=next_cursor,
    )


@router.get("/{entity_id}/connections", response_model=EntityWithConnections)
async def get_connections(
    entity_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    depth: Annotated[int, Query(ge=1, le=4)] = 2,
    types: Annotated[str | None, Query()] = None,
    include_probable: Annotated[bool, Query()] = False,
) -> EntityWithConnections:
    enforce_entity_lookup_enabled()
    records = await execute_query(
        session,
        "entity_connections",
        {
            "entity_id": entity_id,
            "depth": depth,
            "include_probable": include_probable,
        },
    )

    if not records:
        raise HTTPException(status_code=404, detail="Entity not found or has no connections")

    first = records[0]
    enforce_person_access_policy(first["source_labels"])
    entity = _node_to_entity(
        first["e"], first["source_labels"], first["source_id"]
    )

    type_filter = {t.strip().lower() for t in types.split(",")} if types else None

    connections: list[ConnectionResponse] = []
    connected_entities: list[EntityResponse] = []
    seen_ids: set[str] = set()

    for record in records:
        target_labels = record["target_labels"]
        target_type = target_labels[0].lower() if target_labels else "unknown"
        if should_hide_person_entities() and has_person_labels(target_labels):
            continue

        if type_filter and target_type not in type_filter:
            continue

        rel_props = dict(record["r"])
        confidence = float(rel_props.pop("confidence", 1.0))
        source_val = rel_props.pop("source", None)
        rel_sources: list[SourceAttribution] = []
        if isinstance(source_val, str):
            rel_sources = [SourceAttribution(database=source_val)]
        elif isinstance(source_val, list):
            rel_sources = [SourceAttribution(database=s) for s in source_val]

        connections.append(ConnectionResponse(
            source_id=record["source_id"],
            target_id=record["target_id"],
            relationship_type=record["rel_type"],
            properties=sanitize_public_properties(sanitize_props(rel_props)),
            confidence=confidence,
            sources=rel_sources,
            exposure_tier=infer_exposure_tier(target_labels),
        ))

        target_id = record["target_id"]
        if target_id not in seen_ids:
            seen_ids.add(target_id)
            connected_entities.append(
                _node_to_entity(record["connected"], target_labels, target_id)
            )

    return EntityWithConnections(
        entity=entity,
        connections=connections,
        connected_entities=connected_entities,
    )
