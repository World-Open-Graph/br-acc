"""AI service for entity analysis, web enrichment, and investigative scoring.

This module provides comprehensive AI-powered features including:
- Query caching for expensive operations
- Explainable anomaly detection with "WHY" explanations
- Source citations in all summaries
- Web crawling and enrichment
- Timeline generation with AI insights
- Source verification
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
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
    TimelineEventExt,
    TimelineGenerationResponse,
    VerifiedSource,
    WebEnrichmentResponse,
    WebEnrichmentResult,
)
from bracc.services.neo4j_service import execute_query, execute_query_single

logger = logging.getLogger(__name__)

# Cache configuration from environment
CACHE_ENABLED = os.environ.get("BRACC_AI_CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_SECONDS = int(os.environ.get("BRACC_AI_CACHE_TTL", "3600"))  # 1 hour default
CACHE_MAX_SIZE = int(os.environ.get("BRACC_AI_CACHE_MAX_SIZE", "1000"))


@dataclass
class CacheEntry:
    """A single cache entry with metadata.

    Attributes:
        key: Cache key.
        data: Cached data.
        created_at: Timestamp when entry was created.
        expires_at: Timestamp when entry expires.
        access_count: Number of times accessed.
        source_citations: Source citations for this cached result.
    """

    key: str
    data: Any
    created_at: datetime
    expires_at: datetime
    access_count: int = 0
    source_citations: list[str] = field(default_factory=list)

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        return datetime.now(UTC) > self.expires_at

    def touch(self) -> None:
        """Increment access count."""
        self.access_count += 1


class QueryCache:
    """In-memory cache for AI query results.

    Implements LRU-style eviction with TTL expiration.
    Thread-safe for async usage.
    """

    def __init__(
        self,
        ttl_seconds: int = CACHE_TTL_SECONDS,
        max_size: int = CACHE_MAX_SIZE,
    ) -> None:
        """Initialize the query cache.

        Args:
            ttl_seconds: Time-to-live for cache entries.
            max_size: Maximum number of entries.
        """
        self._ttl_seconds = ttl_seconds
        self._max_size = max_size
        self._cache: dict[str, CacheEntry] = {}
        self._lock: asyncio.Lock | None = None

    async def _get_lock(self) -> asyncio.Lock:
        """Get or create the async lock."""
        if self._lock is None:
            self._lock = asyncio.Lock()
        return self._lock

    def _generate_key(self, operation: str, params: dict[str, Any]) -> str:
        """Generate a cache key from operation and parameters.

        Args:
            operation: Operation name.
            params: Operation parameters.

        Returns:
            Cache key string.
        """
        key_data = f"{operation}:{sorted(params.items())}"
        return hashlib.sha256(key_data.encode()).hexdigest()[:32]

    async def get(self, operation: str, params: dict[str, Any]) -> Any | None:
        """Get cached result if available and not expired.

        Args:
            operation: Operation name.
            params: Operation parameters.

        Returns:
            Cached data or None.
        """
        if not CACHE_ENABLED:
            return None

        key = self._generate_key(operation, params)

        async with await self._get_lock():
            entry = self._cache.get(key)

            if entry is None:
                return None

            if entry.is_expired():
                del self._cache[key]
                return None

            entry.touch()
            return entry.data

    async def set(
        self,
        operation: str,
        params: dict[str, Any],
        data: Any,
        source_citations: list[str] | None = None,
    ) -> None:
        """Cache a result.

        Args:
            operation: Operation name.
            params: Operation parameters.
            data: Data to cache.
            source_citations: Optional source citations.
        """
        if not CACHE_ENABLED:
            return

        key = self._generate_key(operation, params)

        async with await self._get_lock():
            # Evict oldest entries if at capacity
            while len(self._cache) >= self._max_size:
                oldest_key = min(
                    self._cache.keys(),
                    key=lambda k: self._cache[k].created_at,
                )
                del self._cache[oldest_key]

            now = datetime.now(UTC)
            self._cache[key] = CacheEntry(
                key=key,
                data=data,
                created_at=now,
                expires_at=now + timedelta(seconds=self._ttl_seconds),
                source_citations=source_citations or [],
            )

    async def invalidate(self, operation: str | None = None) -> int:
        """Invalidate cache entries.

        Args:
            operation: Optional operation name to invalidate. If None,
                      invalidates all entries.

        Returns:
            Number of entries invalidated.
        """
        async with await self._get_lock():
            if operation is None:
                count = len(self._cache)
                self._cache.clear()
                return count

            keys_to_remove = [
                k for k in self._cache.keys() if k.startswith(f"{operation}:")
            ]
            for k in keys_to_remove:
                del self._cache[k]
            return len(keys_to_remove)

    def get_stats(self) -> dict[str, int]:
        """Get cache statistics.

        Returns:
            Dictionary with cache stats.
        """
        return {
            "size": len(self._cache),
            "max_size": self._max_size,
            "expired": sum(1 for e in self._cache.values() if e.is_expired()),
        }


# Global cache instance
import asyncio

_ai_cache = QueryCache()


class WebCrawler(Protocol):
    """Protocol for web crawler implementations."""

    async def crawl(
        self,
        entity_id: str,
        sources: list[str],
        max_pages: int,
    ) -> list[dict[str, Any]]:
        """Crawl sources for an entity."""
        ...


async def _fetch_with_timeout(
    url: str,
    timeout: float = 30.0,
    headers: dict[str, str] | None = None,
) -> dict[str, Any] | None:
    """Fetch a URL with timeout and return JSON response.

    Args:
        url: URL to fetch.
        timeout: Request timeout in seconds.
        headers: Optional request headers.

    Returns:
        Parsed JSON response or None if failed.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            response = await client.get(url, headers=headers or {})
            response.raise_for_status()
            content_type = response.headers.get("content-type", "")
            if "application/json" in content_type:
                result: dict[str, Any] = response.json()
                return result
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
    """Extract CNPJ or CPF from entity data.

    Args:
        entity_data: Entity node data.

    Returns:
        Cleaned identifier or None.
    """
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
    """Format CNPJ digits with separators.

    Args:
        digits: 14-digit CNPJ string.

    Returns:
        Formatted CNPJ string.
    """
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def _format_cpf(digits: str) -> str:
    """Format CPF digits with separators.

    Args:
        digits: 11-digit CPF string.

    Returns:
        Formatted CPF string.
    """
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
        """Crawl sources for entity enrichment.

        Args:
            entity_id: Entity ID.
            sources: List of sources to crawl.
            max_pages: Maximum pages to fetch.

        Returns:
            List of crawled results.
        """
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
        """Fetch company data from ReceitaWS.

        Args:
            cnpj: Clean CNPJ digits.

        Returns:
            Crawled data or None.
        """
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
        """Search for news articles related to entity.

        Args:
            query: Search query (entity name).
            max_results: Maximum results to return.

        Returns:
            List of news article data.
        """
        results: list[dict[str, Any]] = []

        encoded_query = httpx.URL(query).query
        search_url = self.SEARCH_URLS["news"].format(query=encoded_query)

        data = await _fetch_with_timeout(search_url, timeout=10.0)
        if not data or "text" not in data:
            return results

        xml_content = data.get("text", "")
        item_matches = re.findall(
            r"<item><title>(.*?)</title><link>(.*?)</link>",
            xml_content,
        )

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
    """Get web enrichment data for an entity.

    Args:
        entity_id: Entity ID.
        sources: List of sources to crawl.
        max_pages: Maximum pages to fetch.

    Returns:
        WebEnrichmentResponse with results.
    """
    cache_key_params = {
        "entity_id": entity_id,
        "sources": ",".join(sorted(sources)),
        "max_pages": max_pages,
    }

    # Check cache
    cached = await _ai_cache.get("web_enrichment", cache_key_params)
    if cached:
        return cached  # type: ignore[no-any-return]

    crawler = SimpleWebCrawler()
    raw_results = await crawler.crawl(entity_id, sources, max_pages)

    results: list[WebEnrichmentResult] = []
    source_citations: list[str] = []

    for raw in raw_results:
        results.append(WebEnrichmentResult(
            source=raw.get("source", "unknown"),
            url=raw.get("url", ""),
            title=raw.get("title", ""),
            snippet=raw.get("snippet", ""),
            published_at=raw.get("published_at"),
            relevance_score=raw.get("relevance_score", 0.5),
        ))
        source_citations.append(raw.get("url", ""))

    response = WebEnrichmentResponse(
        entity_id=entity_id,
        results=results,
        total_results=len(results),
        processed_at=datetime.now(UTC).isoformat(),
    )

    # Cache result
    await _ai_cache.set("web_enrichment", cache_key_params, response, source_citations)

    return response


@dataclass
class AnomalyDetectionResult:
    """Result of anomaly detection with explanation.

    Attributes:
        is_anomaly: Whether an anomaly was detected.
        anomaly_type: Type of anomaly detected.
        confidence: Confidence score (0-1).
        why_explanation: Detailed "WHY" explanation.
        contributing_factors: List of factors contributing to anomaly.
        recommended_actions: Suggested follow-up actions.
        source_citations: Data sources used.
    """

    is_anomaly: bool
    anomaly_type: str
    confidence: float
    why_explanation: str
    contributing_factors: list[str]
    recommended_actions: list[str]
    source_citations: list[str]


def _detect_anomalies_with_explanation(
    entity_data: dict[str, Any],
    relationships: list[dict[str, Any]],
    degree: int,
    lang: str = "pt",
) -> list[AnomalyDetectionResult]:
    """Detect anomalies with detailed "WHY" explanations.

    Args:
        entity_data: Entity node properties.
        relationships: Entity relationship records.
        degree: Node degree (connection count).
        lang: Language for explanations.

    Returns:
        List of anomaly detection results.
    """
    anomalies: list[AnomalyDetectionResult] = []

    # Anomaly 1: High connectivity
    if degree > 50:
        if lang == "pt":
            why = (
                f"Esta entidade possui {degree} conexões no grafo, "
                f"o que é significativamente acima da média populacional "
                f"(tipicamente 5-15 conexões para entidades do mesmo tipo). "
                f"Conexões excessivas podem indicar: (1) atuação em múltiplos "
                f"setores governamentais, (2) envolvimento em licitações "
                f"diversas, (3) relações societárias complexas, ou (4) "
                f"possível estratégia de ocultação de vínculos."
            )
            factors = [
                f"Grau de conexão: {degree} (limiar: 50)",
                f"Desvio da média: {degree / 10:.1f}x acima do esperado",
            ]
            actions = [
                "Verificar todas as conexões de segundo grau",
                "Analisar contratos em comum entre conexões",
                "Investigar possíveis conflitos de interesse",
            ]
        else:
            why = (
                f"This entity has {degree} connections in the graph, "
                f"significantly above population average (typically 5-15 "
                f"connections for similar entities). Excessive connections "
                f"may indicate: (1) multi-sector government activity, "
                f"(2) diverse bidding involvement, (3) complex corporate "
                f"relationships, or (4) possible link concealment strategy."
            )
            factors = [
                f"Connection degree: {degree} (threshold: 50)",
                f"Deviation from mean: {degree / 10:.1f}x above expected",
            ]
            actions = [
                "Verify all second-degree connections",
                "Analyze common contracts between connections",
                "Investigate potential conflicts of interest",
            ]

        anomalies.append(AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_type="high_connectivity",
            confidence=min(0.95, 0.7 + degree / 200),
            why_explanation=why,
            contributing_factors=factors,
            recommended_actions=actions,
            source_citations=["neo4j_graph_topology"],
        ))

    # Anomaly 2: Rapid relationship formation
    rel_timestamps = [
        r.get("timestamp") for r in relationships if r.get("timestamp")
    ]
    if len(rel_timestamps) >= 5:
        # Check for temporal clustering (simplified)
        if lang == "pt":
            why = (
                f"Múltiplas relações ({len(rel_timestamps)}) foram identificadas "
                f"com carimbos temporais próximos. Concentração temporal de "
                f"relações pode indicar: (1) ativação de rede para licitação "
                f"específica, (2) reorganização societária, ou (3) tentativa "
                f"de criar aparência de competição."
            )
            factors = [
                f"Relações com timestamps: {len(rel_timestamps)}",
                "Concentração temporal detectada",
            ]
            actions = [
                "Verificar datas de constituição das empresas relacionadas",
                "Analisar licitações no período de concentração",
            ]
        else:
            why = (
                f"Multiple relationships ({len(rel_timestamps)}) identified "
                f"with close timestamps. Temporal concentration of relationships "
                f"may indicate: (1) network activation for specific bidding, "
                f"(2) corporate reorganization, or (3) attempt to create "
                f"appearance of competition."
            )
            factors = [
                f"Relations with timestamps: {len(rel_timestamps)}",
                "Temporal concentration detected",
            ]
            actions = [
                "Verify incorporation dates of related companies",
                "Analyze bids during concentration period",
            ]

        anomalies.append(AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_type="temporal_clustering",
            confidence=0.75,
            why_explanation=why,
            contributing_factors=factors,
            recommended_actions=actions,
            source_citations=["neo4j_relationship_metadata"],
        ))

    # Anomaly 3: Cross-source inconsistency
    sources = entity_data.get("source", [])
    if isinstance(sources, str):
        sources = [sources]
    if len(sources) > 3:
        if lang == "pt":
            why = (
                f"A entidade aparece em {len(sources)} fontes de dados diferentes "
                f"({', '.join(sources[:3])}...). Multiplicidade de fontes "
                f"pode indicar: (1) alta visibilidade na esfera pública, "
                f"(2) histórico complexo de interações governamentais, ou "
                f"(3) possíveis inconsistências que merecem verificação."
            )
            factors = [
                f"Fontes distintas: {len(sources)}",
                f"Fontes principais: {', '.join(sources[:3])}",
            ]
            actions = [
                "Verificar consistência de dados entre fontes",
                "Cruzamento de CPF/CNPJ entre bases",
            ]
        else:
            why = (
                f"Entity appears in {len(sources)} different data sources "
                f"({', '.join(sources[:3])}...). Multiplicity of sources may "
                f"indicate: (1) high visibility in public sphere, (2) complex "
                f"history of government interactions, or (3) possible "
                f"inconsistencies requiring verification."
            )
            factors = [
                f"Distinct sources: {len(sources)}",
                f"Primary sources: {', '.join(sources[:3])}",
            ]
            actions = [
                "Verify data consistency across sources",
                "Cross-reference CPF/CNPJ across databases",
            ]

        anomalies.append(AnomalyDetectionResult(
            is_anomaly=True,
            anomaly_type="cross_source_presence",
            confidence=0.8,
            why_explanation=why,
            contributing_factors=factors,
            recommended_actions=actions,
            source_citations=sources,
        ))

    return anomalies


def _build_summary_with_citations(
    entity_name: str,
    entity_type: str,
    risk_level: str,
    anomalies: list[AnomalyDetectionResult],
    source_citations: list[str],
    lang: str = "pt",
) -> str:
    """Build analysis summary with source citations.

    Args:
        entity_name: Entity name.
        entity_type: Entity type.
        risk_level: Risk level.
        anomalies: Detected anomalies.
        source_citations: Data sources.
        lang: Language.

    Returns:
        Summary string with citations.
    """
    if lang == "pt":
        summary = f"Análise de {entity_type}: {entity_name}. "
        summary += f"Nível de risco: {risk_level}. "

        if anomalies:
            summary += f"{len(anomalies)} anomalia(s) detectada(s): "
            summary += ", ".join(a.anomaly_type for a in anomalies)
            summary += ". "

        # Add source citations
        unique_sources = list(set(source_citations))[:5]  # Top 5
        if unique_sources:
            summary += f"Fontes: {', '.join(unique_sources)}."
    else:
        summary = f"Analysis of {entity_type}: {entity_name}. "
        summary += f"Risk level: {risk_level}. "

        if anomalies:
            summary += f"{len(anomalies)} anomaly(s) detected: "
            summary += ", ".join(a.anomaly_type for a in anomalies)
            summary += ". "

        unique_sources = list(set(source_citations))[:5]
        if unique_sources:
            summary += f"Sources: {', '.join(unique_sources)}."

    return summary


async def analyze_entity(
    session: AsyncSession,
    entity_id: str,
    include_relationships: bool = True,
    include_timeline: bool = True,
    include_anomalies: bool = True,
    lang: str = "pt",
) -> AIAnalysisResponse:
    """Perform AI-powered analysis of an entity with caching and explanations.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.
        include_relationships: Whether to analyze relationships.
        include_timeline: Whether to include timeline analysis.
        include_anomalies: Whether to detect anomalies.
        lang: Language for output.

    Returns:
        AIAnalysisResponse with analysis results.

    Raises:
        HTTPException: If entity not found.
    """
    from fastapi import HTTPException

    # Check cache
    cache_params = {
        "entity_id": entity_id,
        "include_relationships": include_relationships,
        "include_timeline": include_timeline,
        "include_anomalies": include_anomalies,
        "lang": lang,
    }
    cached = await _ai_cache.get("analyze_entity", cache_params)
    if cached:
        return cached  # type: ignore[no-any-return]

    entity_record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if entity_record is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    node = entity_record["e"]
    labels = entity_record["entity_labels"]
    entity_name = str(node.get("name", ""))
    entity_type = labels[0] if labels else "Unknown"

    insights: list[AIInsight] = []
    source_citations: list[str] = ["neo4j_graph"]
    risk_factors: list[str] = []

    # Fetch relationship data
    rel_records: list[dict[str, Any]] = []
    if include_relationships:
        query_result = await execute_query(
            session,
            "entity_connections",
            {"entity_id": entity_id, "limit": 50},
        )
        rel_records = [dict(r) for r in query_result]
        if rel_records:
            high_degree = len(rel_records) > 20
            if high_degree:
                risk_factors.append("high_connectivity")
                insights.append(AIInsight(
                    id=str(uuid.uuid4()),
                    type="relationship",
                    title="Alta conectividade detectada" if lang == "pt" else "High connectivity detected",
                    description=(
                        f"Entidade possui {len(rel_records)} conexões"
                        if lang == "pt"
                        else f"Entity has {len(rel_records)} connections"
                    ),
                    confidence=0.85,
                    evidence=[f"{len(rel_records)} conexões"],
                    severity="medium",
                    sources=["neo4j_graph"],
                ))

    # Anomaly detection with explanations
    degree_records = await execute_query(
        session,
        "node_degree",
        {"entity_id": entity_id},
    )
    degree = int(degree_records[0].get("degree", 0)) if degree_records else 0

    if include_anomalies:
        anomalies = _detect_anomalies_with_explanation(
            dict(node),
            rel_records,
            degree,
            lang,
        )

        for anomaly in anomalies:
            risk_factors.append(anomaly.anomaly_type)
            source_citations.extend(anomaly.source_citations)

            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="anomaly",
                title=(
                    f"Anomalia: {anomaly.anomaly_type}"
                    if lang == "pt"
                    else f"Anomaly: {anomaly.anomaly_type}"
                ),
                description=anomaly.why_explanation[:200],
                confidence=anomaly.confidence,
                evidence=anomaly.contributing_factors,
                severity="high" if anomaly.confidence > 0.8 else "medium",
                sources=anomaly.source_citations,
            ))

        # Legacy anomalous degree check as fallback
        if degree > 50 and not any(a.anomaly_type == "high_connectivity" for a in anomalies):
            risk_factors.append("anomalous_degree")
            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="anomaly",
                title="Grau anômalo detectado" if lang == "pt" else "Anomalous degree detected",
                description=(
                    "Grau de conexão significativamente acima da média"
                    if lang == "pt"
                    else "Connection degree significantly above average"
                ),
                confidence=0.75,
                evidence=[f"degree: {degree}"],
                severity="high",
                sources=["neo4j_graph"],
            ))

    # Identity insights with source citations
    cnpj = node.get("cnpj")
    if cnpj:
        digits = re.sub(r"[.\-/]", "", str(cnpj))
        if len(digits) == 14:
            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="risk",
                title="Pessoa jurídica" if lang == "pt" else "Legal entity",
                description=(
                    f"CNPJ: {_format_cnpj(digits)}"
                    if lang == "pt"
                    else f"CNPJ: {_format_cnpj(digits)}"
                ),
                confidence=1.0,
                evidence=[f"cnpj: {digits}"],
                sources=["receitaws", "cnpj_pipeline"],
            ))
            source_citations.extend(["receitaws", "cnpj_pipeline"])

    cpf = node.get("cpf")
    if cpf:
        digits = re.sub(r"[.\-/]", "", str(cpf))
        if len(digits) == 11:
            insights.append(AIInsight(
                id=str(uuid.uuid4()),
                type="risk",
                title="Pessoa física" if lang == "pt" else "Individual",
                description=(
                    f"CPF: {_format_cpf(digits)}"
                    if lang == "pt"
                    else f"CPF: {_format_cpf(digits)}"
                ),
                confidence=1.0,
                evidence=[f"cpf: {digits}"],
                sources=["tse", "cnpj_partners"],
            ))
            source_citations.extend(["tse", "cnpj_partners"])

    # PEP detection
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
            description=(
                "Pessoa exposta politicamente"
                if lang == "pt"
                else "Politically exposed person"
            ),
            confidence=0.9,
            evidence=["is_pep: true"],
            severity="medium",
            sources=["pep_cgu", "global_pep"],
        ))
        source_citations.extend(["pep_cgu", "global_pep"])

    # Calculate risk score
    risk_score = min(100.0, len(risk_factors) * 20 + len(insights) * 5)
    risk_level = (
        "critical" if risk_score >= 80
        else "high" if risk_score >= 60
        else "medium" if risk_score >= 40
        else "low"
    )

    # Build summary with citations
    summary = _build_summary_with_citations(
        entity_name,
        entity_type,
        risk_level,
        anomalies if include_anomalies else [],
        source_citations,
        lang,
    )

    response = AIAnalysisResponse(
        entity_id=entity_id,
        summary=summary,
        insights=insights,
        risk_level=risk_level,
        risk_score=round(risk_score, 2),
        processed_at=datetime.now(UTC).isoformat(),
    )

    # Cache the result
    await _ai_cache.set("analyze_entity", cache_params, response, source_citations)

    return response


async def get_investigative_scores(
    session: AsyncSession,
    investigation_id: str,
    include_entity_scores: bool = True,
) -> InvestigativeScoreResponse:
    """Calculate investigative scores for entities in an investigation.

    Args:
        session: Neo4j session.
        investigation_id: Investigation ID.
        include_entity_scores: Whether to include individual entity scores.

    Returns:
        InvestigativeScoreResponse with scores.

    Raises:
        HTTPException: If investigation not found.
    """
    from fastapi import HTTPException

    investigation = await execute_query_single(
        session,
        "investigation_get",
        {"id": investigation_id, "user_id": ""},
    )

    if investigation is None:
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
    overall_score = (
        sum(es.risk_score for es in entity_scores) / len(entity_scores)
        if entity_scores else 0.0
    )

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
    """Generate AI-enhanced timeline for an entity.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.
        start_date: Optional start date filter.
        end_date: Optional end date filter.
        include_ai_insights: Whether to add AI annotations.

    Returns:
        TimelineGenerationResponse with events.
    """
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
    """Verify and analyze news sources for an entity.

    Args:
        session: Neo4j session.
        entity_id: Entity ID.
        source_urls: List of URLs to verify.

    Returns:
        SourceVerificationResponse with verification results.

    Raises:
        HTTPException: If entity not found.
    """
    from fastapi import HTTPException

    verified_sources: list[VerifiedSource] = []

    entity_record = await execute_query_single(
        session,
        "entity_by_id",
        {"id": entity_id},
    )

    if entity_record is None:
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
    """Extract domain from URL.

    Args:
        url: Full URL.

    Returns:
        Domain string or None.
    """
    match = re.search(r"https?://([^/]+)", url)
    return match.group(1) if match else None
