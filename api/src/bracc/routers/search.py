import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from neo4j import AsyncSession
from starlette.requests import Request

from bracc.dependencies import get_session
from bracc.middleware.rate_limit import limiter
from bracc.models.entity import SourceAttribution
from bracc.models.search import SearchResponse, SearchResult
from bracc.services.neo4j_service import execute_query, execute_query_single, sanitize_props
from bracc.services.public_guard import (
    has_person_labels,
    infer_exposure_tier,
    sanitize_public_properties,
    should_hide_person_entities,
)

router = APIRouter(prefix="/api/v1", tags=["search"])

_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}[\]^"~*?:\\/])')


def _escape_lucene(query: str) -> str:
    """Escape Lucene special characters so user input is treated as literals."""
    return _LUCENE_SPECIAL.sub(r"\\\1", query)


def _extract_name(node: Any, labels: list[str]) -> str:
    props = dict(node)
    entity_type = labels[0].lower() if labels else ""
    if entity_type == "company":
        return str(props.get("razao_social", props.get("name", props.get("nome_fantasia", ""))))
    if entity_type in ("contract", "amendment", "convenio"):
        return str(props.get("object", props.get("function", props.get("name", ""))))
    if entity_type == "embargo":
        return str(props.get("infraction", props.get("name", "")))
    if entity_type == "publicoffice":
        return str(props.get("org", props.get("name", "")))
    return str(props.get("name", ""))


@router.get("/search", response_model=SearchResponse)
@limiter.limit("30/minute")
async def search_entities(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_session)],
    q: Annotated[str, Query(min_length=2, max_length=200)],
    entity_type: Annotated[str | None, Query(alias="type")] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SearchResponse:
    skip = (page - 1) * size
    type_filter = entity_type.lower() if entity_type else None
    hide_person_entities = should_hide_person_entities()

    records = await execute_query(
        session,
        "search",
        {
            "query": _escape_lucene(q),
            "entity_type": type_filter,
            "skip": skip,
            "limit": size,
            "hide_person_entities": hide_person_entities,
        },
    )
    total_record = await execute_query_single(
        session,
        "search_count",
        {
            "query": _escape_lucene(q),
            "entity_type": type_filter,
            "hide_person_entities": hide_person_entities,
        },
    )
    total = int(total_record["total"]) if total_record and total_record["total"] is not None else 0

    results: list[SearchResult] = []
    for record in records:
        node = record["node"]
        props = dict(node)
        labels = record["node_labels"]
        if hide_person_entities and has_person_labels(labels):
            continue
        source_val = props.pop("source", None)
        sources: list[SourceAttribution] = []
        if isinstance(source_val, str):
            sources = [SourceAttribution(database=source_val)]
        elif isinstance(source_val, list):
            sources = [SourceAttribution(database=s) for s in source_val]

        doc_id = record["document_id"]
        # Only expose cpf/cnpj as document, not internal element IDs
        document = str(doc_id) if doc_id and not str(doc_id).startswith("4:") else None

        results.append(SearchResult(
            id=record["node_id"],
            type=labels[0].lower() if labels else "unknown",
            name=_extract_name(node, labels),
            score=record["score"],
            document=document,
            properties=sanitize_public_properties(sanitize_props(props)),
            sources=sources,
            exposure_tier=infer_exposure_tier(labels),
        ))

    return SearchResponse(
        results=results,
        total=total,
        page=page,
        size=size,
    )
