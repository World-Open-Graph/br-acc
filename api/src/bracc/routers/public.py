from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j import AsyncSession  # noqa: TC002

from bracc.config import settings
from bracc.dependencies import get_session
from bracc.models.entity import SourceAttribution
from bracc.models.graph import GraphEdge, GraphNode, GraphResponse
from bracc.models.pattern import PatternResponse
from bracc.services.intelligence_provider import CommunityIntelligenceProvider
from bracc.services.neo4j_service import execute_query, execute_query_single, sanitize_props
from bracc.services.public_guard import (
    enforce_person_access_policy,
    has_person_labels,
    infer_exposure_tier,
    sanitize_public_properties,
)
from bracc.services.source_registry import load_source_registry, source_registry_summary

router = APIRouter(prefix="/api/v1/public", tags=["public"])
_PUBLIC_PROVIDER = CommunityIntelligenceProvider()

_CPF_KEYS = {"cpf", "doc_partial", "doc_raw"}
_CNPJ_PATTERN = re.compile(r"^\d{14}$")


def _clean_identifier(raw: str) -> str:
    return re.sub(r"[.\-/]", "", raw)


def _format_cnpj(digits: str) -> str:
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _slim_props(node_props: dict[str, Any]) -> dict[str, str | float | int | bool | None]:
    return sanitize_public_properties(sanitize_props(node_props))


def _build_sources(value: Any) -> list[SourceAttribution]:
    if isinstance(value, str):
        return [SourceAttribution(database=value)]
    if isinstance(value, list):
        return [SourceAttribution(database=str(item)) for item in value]
    return []


@router.get("/meta")
async def public_meta(
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, Any]:
    record = await execute_query_single(session, "meta_stats", {})
    summary = source_registry_summary(load_source_registry())
    return {
        "product": "World Transparency Graph",
        "mode": "public_safe",
        "total_nodes": record["total_nodes"] if record else 0,
        "total_relationships": record["total_relationships"] if record else 0,
        "company_count": record["company_count"] if record else 0,
        "contract_count": record["contract_count"] if record else 0,
        "sanction_count": record["sanction_count"] if record else 0,
        "finance_count": record["finance_count"] if record else 0,
        "bid_count": record["bid_count"] if record else 0,
        "inquiry_count": record["cpi_count"] if record else 0,
        "source_health": {
            "data_sources": summary["universe_v1_sources"],
            "implemented_sources": summary["implemented_sources"],
            "loaded_sources": summary["loaded_sources"],
            "healthy_sources": summary["healthy_sources"],
            "stale_sources": summary["stale_sources"],
            "blocked_external_sources": summary["blocked_external_sources"],
            "quality_fail_sources": summary["quality_fail_sources"],
            "discovered_uningested_sources": summary["discovered_uningested_sources"],
        },
    }


async def _resolve_company(
    session: AsyncSession,
    company_ref: str,
) -> tuple[str, str]:
    company_identifier = _clean_identifier(company_ref)
    company_identifier_formatted = (
        _format_cnpj(company_identifier) if _CNPJ_PATTERN.match(company_identifier) else company_ref
    )
    record = await execute_query_single(
        session,
        "public_company_lookup",
        {
            "company_id": company_ref,
            "company_identifier": company_identifier,
            "company_identifier_formatted": company_identifier_formatted,
        },
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Company not found")
    labels = record["entity_labels"]
    enforce_person_access_policy(labels)
    company = record["c"]
    cnpj = str(company.get("cnpj", ""))
    return record["entity_id"], cnpj


@router.get("/patterns/company/{cnpj_or_id}", response_model=PatternResponse)
async def public_patterns_for_company(
    cnpj_or_id: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    lang: Annotated[str, Query()] = "pt",
) -> PatternResponse:
    if not settings.patterns_enabled:
        raise HTTPException(
            status_code=503,
            detail="Pattern engine temporarily unavailable pending validation.",
        )
    company_id, _company_cnpj = await _resolve_company(session, cnpj_or_id)
    patterns = await _PUBLIC_PROVIDER.run_pattern(
        session,
        pattern_id="__all__",
        entity_id=company_id,
        lang=lang,
        include_probable=False,
    )

    return PatternResponse(entity_id=company_id, patterns=patterns, total=len(patterns))


@router.get("/graph/company/{company_ref}", response_model=GraphResponse)
async def public_graph_for_company(
    company_ref: str,
    session: Annotated[AsyncSession, Depends(get_session)],
    depth: Annotated[int, Query(ge=1, le=3)] = 2,
) -> GraphResponse:
    company_id, company_cnpj = await _resolve_company(session, company_ref)
    records = await execute_query(
        session,
        "public_graph_company",
        {
            "company_id": company_id,
            "company_identifier": _clean_identifier(company_cnpj),
            "company_identifier_formatted": company_cnpj,
            "depth": depth,
        },
    )
    if not records:
        raise HTTPException(status_code=404, detail="Company graph not found")

    record = records[0]
    raw_nodes = record["nodes"]
    raw_rels = record["relationships"]
    center_id = record["center_id"]

    node_ids: set[str] = set()
    nodes: list[GraphNode] = []
    for node in raw_nodes:
        node_id = node.element_id
        labels = list(node.labels)
        if has_person_labels(labels):
            continue
        props = dict(node)
        source_val = props.pop("source", None)
        sources = _build_sources(source_val)
        clean_props = {
            key: value
            for key, value in props.items()
            if key not in _CPF_KEYS
        }
        nodes.append(
            GraphNode(
                id=node_id,
                label=str(clean_props.get("razao_social", clean_props.get("name", node_id))),
                type=labels[0].lower() if labels else "unknown",
                document_id=str(clean_props.get("cnpj", "")) or None,
                properties=_slim_props(clean_props),
                sources=sources,
                is_pep=False,
                exposure_tier=infer_exposure_tier(labels),
            )
        )
        node_ids.add(node_id)

    edges: list[GraphEdge] = []
    seen: set[str] = set()
    for rel in raw_rels:
        rel_id = rel.element_id
        if rel_id in seen:
            continue
        seen.add(rel_id)
        source_id = rel.start_node.element_id
        target_id = rel.end_node.element_id
        if source_id not in node_ids or target_id not in node_ids:
            continue
        props = dict(rel)
        confidence = float(props.pop("confidence", 1.0))
        source_val = props.pop("source", None)
        edges.append(
            GraphEdge(
                id=rel_id,
                source=source_id,
                target=target_id,
                type=rel.type,
                properties=sanitize_public_properties(sanitize_props(props)),
                confidence=confidence,
                sources=_build_sources(source_val),
                exposure_tier="public_safe",
            )
        )

    return GraphResponse(nodes=nodes, edges=edges, center_id=center_id)
