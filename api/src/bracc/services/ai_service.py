from __future__ import annotations

import logging
import re
import uuid
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx
from neo4j import AsyncSession

from bracc.config import settings
from bracc.models.ai import (
    AIAnalysisResponse,
    AIInsight,
    EntityScore,
    InvestigativeScoreResponse,
    SourceVerificationResponse,
    TimelineGenerationResponse,
    TimelineEventExt,
    VerifiedSource,
    WebEnrichmentResponse,
    WebEnrichmentResult,
)
from bracc.services.neo4j_service import execute_query, execute_query_single

logger = logging.getLogger(__name__)


class WebCrawler(Protocol):
    async def crawl(
        self,
        entity_id: str,
        sources: list[str],
        max_pages: int,
    ) -> list[dict[str, Any]]:
        ...


async def _fetch_with_timeout(
    url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Fetch a URL with timeout and return JSON response."""
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers or {})
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                return response.json()
            return {"text": response.text[:5000]}
    except httpx.TimeoutException:
        logger.warning("Timeout fetching URL: %s", url)
        return None
    except httpx.HTTPStatusError as e:
        logger.warning("HTTP error fetching URL %s: %s", url, e)
        return None
    except Exception:
        logger.exception("Error fetching URL: %s", url)
        return None


def _extract_entity_identifier(entity_data: dict[str, Any]) -> str | None:
    """Extract CNPJ or CPF from entity data."""
    cnpj = entity_data.get("cnpj")
    if cnpj:
        digits = re.sub(r"[.\-/]", "", str(cnpj))
        if len(digits) == 14:
            return digits
    cpf = entity_data.get("cpf")
    if cpf:
        digits = re.sub(r"[.\-/]", "", str(cpf))
        if len(digits) == 11:
            return digits
    return None


def _format_cnpj(digits: str) -> str:
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _format_cpf(digits: str) -> str:
    return f"{digits[:3]}.{digits[3:6]}.{digits[6:9]}-{digits[9:]}"


class SimpleWebCrawler:
    """Simple web crawler for entity enrichment."""

    SEARCH_URLS = {
        "news": "https://news.google.com/rss/search?q={query}",
        "company_registry": "https://receitaws.com.br/v1/cnpj/{cnpj}",
    }

    async def crawl(
        self,
        entity_id: str,
        sources: list[str],
        max_pages: int,
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []

        entity_record = await execute_query_single(
            None,  # type: ignore[arg-type]
            "entity_by_id",
            {"id": entity_id},
        )

        if entity_record is None:
            return results

        node = entity_record["e"]
        entity_name = str(node.get("name", ""))
        identifier = _extract_entity_identifier(node)

        if not identifier or not entity_name:
            return results

        if "company_registry" in sources or "all" in sources:
            if len(identifier) == 14:
                registry_result = await self._crawl_company_registry(identifier)
                if registry_result:
                    results.append(registry_result)

        if "news" in sources or "all" in sources:
            news_results = await self._crawl_news(entity_name, max_pages)
            results.extend(news_results)

        return results

    async def _crawl_company_registry(self, cnpj: str) -> dict[str, Any] | None:
        """Fetch company data from ReceitaWS."""
        url = self.SEARCH_URLS["company_registry"].format(cnpj=cnpj)
        data = await _fetch_with_timeout(url, timeout=15.0)
        if data and "nome" in data:
            return {
                "source": "company_registry",
                "url": url,
                "title": f"Empresa: {data.get('nome', 'N/A')}",
                "snippet": f"Atividade: {data.get('atividade_principal', 'N/A')}",
                "published_at": data.get("data_situacao"),
                "relevance_score": 0.9,
                "raw_data": data,
            }
        return None

    async def _crawl_news(self, query: str, max_results: int) -> list[dict[str, Any]]:
        """Search for news articles related to entity."""
        results: list[dict[str, Any]] = []

        encoded_query = httpx.URL(query).query.encode("utf-8").decode("utf-8")
        search_url = self.SEARCH_URLS["news"].format(query=encoded_query)

        data = await _fetch_with_timeout(search_url, timeout=10.0)
        if not data or "text" not in data:
            return results

        xml_content = data.get("text", "")
        item_matches = re.findall(r"<item><title>(.*?)</title><link>(.*?)</link>", xml_content)

        for title, link in item_matches[:max_results]:
            results.append({
                "source": "news",
                "url": link,
                "title": title.strip(),
                "snippet": "",
                "published_at": None,
                "relevance_score": 0.5,
            })

        return results


async def get_web_enrichment(
    entity_id: str,
    sources: list[str],
    max_pages: int,
) -> WebEnrichmentResponse:
    """Get web enrichment data for an entity."""
    crawler = SimpleWebCrawler()
    raw_results = await crawler.crawl(entity_id, sources, max_pages)

    results: list[WebEnrichmentResult] = []
    for raw in raw_results:
        results.append(WebEnrichmentResult(
            source=raw.get("source", "unknown"),
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            snippet=raw.get("snippet", ""),
            published_at=raw.get("published_at"),
            relevance_score=raw.get("relevance_score", 0.5),
        ))

    return WebEnrichmentResponse(
        entity_id=entity_id,
        results=results,
        total_results=len(results),
        processed_at=datetime.now(UTC).isoformat(),
    )


async def analyze_entity(
    session: AsyncSession,
    entity_id: str,
    include_relationships: bool = True,
    include_timeline: bool = True,
    include_anomalies: bool = True,
    lang: str = "pt",
) -> AIAnalysisResponse:
    """Perform AI-powered analysis of an entity."""
    entity_record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if entity_record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Entity not found")

    node = entity_record["e"]
    labels = entity_record["entity_labels"]
    entity_name = str(node.get("name", ""))
    entity_type = labels[0] if labels else "Unknown"

    insights: list[AIInsight] = []
    risk_factors: list[str] = []

    if include_relationships:
        rel_records = await execute_query(
            session,
            "entity_connections",
            {"entity_id": entity_id, "limit": 50},
        )
        if rel_records:
            high_degree = len(rel_records) > 20
            if high_degree:
                risk_factors.append("high_connectivity")
                insights.append(AIInsight(
                    id=str(uuid.uuid4()),
                    type="relationship",
                    title="Alta conectividade detectada" if lang == "pt" else "High connectivity detected",
                    description=f"Entidade possui {len(rel_records)} conexões" if lang == "pt" else f"Entity has {len(rel_records)} connections",
                    confidence=0.85,
                    evidence=[f"{len(rel_records)} conexões"],
                    severity="medium",
                ))

    if include_anomalies:
        degree_records = await execute_query(
            session,
            "node_degree",
            {"entity_id": entity_id},
        )
        if degree_records:
            degree = int(degree_records[0].get("degree", 0))
            if degree > 50:
                risk_factors.append("anomalous_degree")
                insights.append(AIInsight(
                    id=str(uuid.uuid4()),
                    type="anomaly",
                    title="Grau anômalo detectado" if lang == "pt" else "Anomalous degree detected",
                    description="Grau de conexão significativamente acima da média" if lang == "pt" else "Connection degree significantly above average",
                    confidence=0.75,
                    evidence=[f"degree: {degree}"],
                    severity="high",
                ))

    cnpj = node.get("cnpj")
    if cnpj:
        digits = re.sub(r"[.\-/]", "", str(cnpj))
        if len(digits) == 14:
            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="risk",
                title="Pessoa jurídica" if lang == "pt" else "Legal entity",
                description=f"CNPJ: {_format_cnpj(digits)}" if lang == "pt" else f"CNPJ: {_format_cnpj(digits)}",
                confidence=1.0,
                evidence=[f"cnpj: {digits}"],
            ))

    cpf = node.get("cpf")
    if cpf:
        digits = re.sub(r"[.\-/]", "", str(cpf))
        if len(digits) == 11:
            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="risk",
                title="Pessoa física" if lang == "pt" else "Individual",
                description=f"CPF: {_format_cpf(digits)}" if lang == "pt" else f"CPF: {_format_cpf(digits)}",
                confidence=1.0,
                evidence=[f"cpf: {digits}"],
            ))

    is_pep = node.get("is_pep", node.get("role")) or any(
        "pep" in str(node.get(k, "")).lower()
        for k in ["role", "cargo", "position"]
    )
    if is_pep:
        risk_factors.append("pep_flag")
        insights.append(AIInsight(
            id=str(uuid.uuid4()),
            type="risk",
            title="PEP detectado" if lang == "pt" else "PEP detected",
            description="Pessoa exposta politicamente" if lang == "pt" else "Politically exposed person",
            confidence=0.9,
            evidence=["is_pep: true"],
            severity="medium",
        ))

    risk_score = min(100.0, len(risk_factors) * 20 + len(insights) * 5)
    risk_level = "critical" if risk_score >= 80 else "high" if risk_score >= 60 else "medium" if risk_score >= 40 else "low"

    summary_parts = [f"Análise de {entity_type}: {entity_name}"]
    if risk_factors:
        summary_parts.append(f"Fatores de risco: {', '.join(risk_factors)}")
    summary_parts.append(f"Nível de risco: {risk_level}")

    return AIAnalysisResponse(
        entity_id=entity_id,
        summary=". ".join(summary_parts),
        insights=insights,
        risk_level=risk_level,
        risk_score=round(risk_score, 2),
        processed_at=datetime.now(UTC).isoformat(),
    )


async def get_investigative_scores(
    session: AsyncSession,
    investigation_id: str,
    include_entity_scores: bool = True,
) -> InvestigativeScoreResponse:
    """Calculate investigative scores for entities in an investigation."""
    investigation = await execute_query_single(
        session,
        "investigation_get",
        {"id": investigation_id, "user_id": ""},
    )

    if investigation is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Investigation not found")

    entity_ids = investigation.get("entity_ids", [])

    entity_scores: list[EntityScore] = []
    if include_entity_scores and entity_ids:
        for idx, eid in enumerate(entity_ids):
            entity_record = await execute_query_single(
                session,
                "entity_by_id",
                {"id": eid},
            )
            if entity_record:
                node = entity_record["e"]
                labels = entity_record["entity_labels"]

                degree_record = await execute_query(
                    session,
                    "node_degree",
                    {"entity_id": eid},
                )
                degree = int(degree_record[0].get("degree", 0)) if degree_record else 0

                risk_factors = []
                if degree > 20:
                    risk_factors.append("high_connectivity")
                if node.get("is_pep") or node.get("role"):
                    risk_factors.append("pep_flag")

                entity_scores.append(EntityScore(
                    entity_id=eid,
                    entity_name=str(node.get("name", "")),
                    entity_type=labels[0] if labels else "Unknown",
                    risk_score=min(100.0, degree * 2 + len(risk_factors) * 15),
                    risk_factors=risk_factors,
                    priority=idx + 1,
                ))

    entity_scores.sort(key=lambda x: x.risk_score, reverse=True)
    for idx, es in enumerate(entity_scores):
        es.priority = idx + 1

    high_risk = sum(1 for es in entity_scores if es.risk_score >= 60)
    overall_score = sum(es.risk_score for es in entity_scores) / len(entity_scores) if entity_scores else 0.0

    recommended_actions = []
    if high_risk > 0:
        recommended_actions.append("Revisar entidades de alto risco")
    if any(es.risk_factors for es in entity_scores):
        recommended_actions.append("Verificar conexões com PEPs")
    if len(entity_scores) > 10:
        recommended_actions.append("Considerar separar em sub-investigações")

    return InvestigativeScoreResponse(
        investigation_id=investigation_id,
        investigation_title=str(investigation.get("title", "")),
        overall_risk_score=round(overall_score, 2),
        entity_count=len(entity_ids),
        high_risk_entities=high_risk,
        entity_scores=entity_scores,
        recommended_actions=recommended_actions,
        generated_at=datetime.now(UTC).isoformat(),
    )


async def generate_timeline(
    session: AsyncSession,
    entity_id: str,
    start_date: str | None = None,
    end_date: str | None = None,
    include_ai_insights: bool = True,
) -> TimelineGenerationResponse:
    """Generate AI-enhanced timeline for an entity."""
    query_params: dict[str, Any] = {
        "entity_id": entity_id,
        "limit": 100,
    }
    if start_date:
        query_params["start_date"] = start_date
    if end_date:
        query_params["end_date"] = end_date

    records = await execute_query(
        session,
        "entity_timeline",
        query_params,
    )

    events: list[TimelineEventExt] = []
    for idx, record in enumerate(records):
        event_date = record.get("date", "")
        event_label = record.get("label", "")
        event_type = record.get("type", "")

        ai_annotation = None
        if include_ai_insights and event_label:
            if "contract" in event_label.lower() or "contrato" in event_label.lower():
                ai_annotation = "Verificar valor do contrato e órgão contratante"
            elif "donation" in event_label.lower() or "doação" in event_label.lower():
                ai_annotation = "Analisar origem dos recursos"
            elif "sanction" in event_label.lower() or "sanção" in event_label.lower():
                ai_annotation = "Verificar período da sanção"

        events.append(TimelineEventExt(
            id=str(uuid.uuid4()),
            date=event_date,
            label=event_label,
            entity_type=event_type,
            properties=dict(record),
            sources=[str(record.get("source", "neo4j"))],
            ai_annotation=ai_annotation,
        ))

    events.sort(key=lambda x: x.date)

    return TimelineGenerationResponse(
        entity_id=entity_id,
        events=events,
        total=len(events),
        next_cursor=None,
        generated_at=datetime.now(UTC).isoformat(),
    )


async def verify_sources(
    session: AsyncSession,
    entity_id: str,
    source_urls: list[str],
) -> SourceVerificationResponse:
    """Verify and analyze news sources for an entity."""
    verified_sources: list[VerifiedSource] = []

    entity_record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if entity_record is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Entity not found")

    entity_name = str(entity_record["e"].get("name", ""))

    for url in source_urls:
        result = await _fetch_with_timeout(url, timeout=10.0)
        is_verified = result is not None
        credibility = 0.7 if is_verified else 0.0

        verified_sources.append(VerifiedSource(
            url=url,
            is_verified=is_verified,
            source_name=_extract_domain(url),
            published_date=None,
            author=None,
            credibility_score=credibility,
            bias_indicator="unknown",
            fact_check_result=None,
        ))

    return SourceVerificationResponse(
        entity_id=entity_id,
        verified_sources=verified_sources,
        total_verified=sum(1 for vs in verified_sources if vs.is_verified),
        processed_at=datetime.now(UTC).isoformat(),
    )


def _extract_domain(url: str) -> str | None:
    """Extract domain from URL."""
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1) if match else None
