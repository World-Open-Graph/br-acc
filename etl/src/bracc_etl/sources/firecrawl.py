"""Firecrawl ETL module for web crawling and entity enrichment.

This module provides web crawling capabilities for extracting entity-related
information from various sources including news sites, company registries,
and public records. It implements retry logic, deduplication, and tracks
last_crawled_at timestamps.
"""

from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

logger = logging.getLogger(__name__)

# Environment-based configuration
FIRECRAWL_API_KEY = os.environ.get("FIRECRAWL_API_KEY", "")
FIRECRAWL_BASE_URL = os.environ.get("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1")
FIRECRAWL_MAX_RETRIES = int(os.environ.get("FIRECRAWL_MAX_RETRIES", "3"))
FIRECRAWL_RETRY_DELAY_BASE = float(os.environ.get("FIRECRAWL_RETRY_DELAY_BASE", "2.0"))
FIRECRAWL_TIMEOUT = float(os.environ.get("FIRECRAWL_TIMEOUT", "30.0"))
FIRECRAWL_MAX_PAGES = int(os.environ.get("FIRECRAWL_MAX_PAGES", "10"))


class CrawlError(Exception):
    """Base exception for crawl operations."""

    pass


class CrawlRetryExhaustedError(CrawlError):
    """Raised when all retry attempts are exhausted."""

    pass


@dataclass(frozen=True)
class CrawledPage:
    """A crawled page with metadata.

    Attributes:
        url: The URL of the crawled page.
        title: The page title.
        content: Extracted content/snippet.
        source: Source type (news, registry, etc.).
        published_at: Optional publication date.
        relevance_score: Calculated relevance (0-1).
        crawl_timestamp: When the page was crawled.
        content_hash: Hash of content for deduplication.
    """

    url: str
    title: str
    content: str
    source: str
    published_at: str | None = None
    relevance_score: float = 0.0
    crawl_timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    content_hash: str = ""

    def __post_init__(self) -> None:
        """Generate content hash if not provided."""
        if not self.content_hash:
            object.__setattr__(
                self,
                "content_hash",
                hashlib.sha256(self.content.encode()).hexdigest()[:16],
            )


@dataclass
class CrawlResult:
    """Result of a crawl operation.

    Attributes:
        entity_id: The entity being crawled.
        pages: List of crawled pages.
        total_pages: Total pages found.
        deduplicated_count: Number of duplicates removed.
        last_crawled_at: Timestamp of this crawl.
        errors: List of error messages.
    """

    entity_id: str
    pages: list[CrawledPage] = field(default_factory=list)
    total_pages: int = 0
    deduplicated_count: int = 0
    last_crawled_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    errors: list[str] = field(default_factory=list)


class DeduplicationStore(Protocol):
    """Protocol for deduplication storage backends."""

    async def is_seen(self, content_hash: str) -> bool:
        """Check if content hash has been seen before."""
        ...

    async def mark_seen(self, content_hash: str, url: str) -> None:
        """Mark content hash as seen."""
        ...

    async def get_last_crawled(self, entity_id: str) -> str | None:
        """Get last crawl timestamp for entity."""
        ...

    async def set_last_crawled(self, entity_id: str, timestamp: str) -> None:
        """Set last crawl timestamp for entity."""
        ...


class InMemoryDeduplicationStore:
    """In-memory implementation of deduplication store.

    Note: This is suitable for single-process use only.
    For production, use a persistent store (Redis, database, etc.).
    """

    def __init__(self) -> None:
        """Initialize the in-memory store."""
        self._seen_hashes: set[str] = set()
        self._hash_to_url: dict[str, str] = {}
        self._last_crawled: dict[str, str] = {}

    async def is_seen(self, content_hash: str) -> bool:
        """Check if content hash has been seen.

        Args:
            content_hash: The hash to check.

        Returns:
            True if seen before, False otherwise.
        """
        return content_hash in self._seen_hashes

    async def mark_seen(self, content_hash: str, url: str) -> None:
        """Mark content hash as seen.

        Args:
            content_hash: The hash to mark.
            url: The URL associated with the hash.
        """
        self._seen_hashes.add(content_hash)
        self._hash_to_url[content_hash] = url

    async def get_last_crawled(self, entity_id: str) -> str | None:
        """Get last crawl timestamp for entity.

        Args:
            entity_id: The entity ID.

        Returns:
            ISO timestamp or None if never crawled.
        """
        return self._last_crawled.get(entity_id)

    async def set_last_crawled(self, entity_id: str, timestamp: str) -> None:
        """Set last crawl timestamp for entity.

        Args:
            entity_id: The entity ID.
            timestamp: ISO timestamp.
        """
        self._last_crawled[entity_id] = timestamp


class FirecrawlClient:
    """Client for Firecrawl web crawling API.

    This client provides methods to crawl web pages with automatic
    retry logic, rate limiting, and error handling.
    """

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        max_retries: int | None = None,
        retry_delay_base: float | None = None,
        timeout: float | None = None,
    ) -> None:
        """Initialize the Firecrawl client.

        Args:
            api_key: Firecrawl API key. Defaults to FIRECRAWL_API_KEY env var.
            base_url: API base URL. Defaults to FIRECRAWL_BASE_URL env var.
            max_retries: Max retry attempts. Defaults to FIRECRAWL_MAX_RETRIES env var.
            retry_delay_base: Base delay between retries. Defaults to env var.
            timeout: Request timeout. Defaults to FIRECRAWL_TIMEOUT env var.
        """
        self._api_key = api_key or FIRECRAWL_API_KEY
        self._base_url = (base_url or FIRECRAWL_BASE_URL).rstrip("/")
        self._max_retries = max_retries or FIRECRAWL_MAX_RETRIES
        self._retry_delay_base = retry_delay_base or FIRECRAWL_RETRY_DELAY_BASE
        self._timeout = timeout or FIRECRAWL_TIMEOUT
        self._headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    async def crawl_url(
        self,
        url: str,
        max_pages: int | None = None,
    ) -> list[dict[str, Any]]:
        """Crawl a URL and return extracted data.

        Args:
            url: The URL to crawl.
            max_pages: Maximum pages to crawl. Defaults to env var.

        Returns:
            List of crawled page data dictionaries.

        Raises:
            CrawlRetryExhaustedError: If all retries fail.
            CrawlError: For other crawl errors.
        """
        if not self._api_key:
            raise CrawlError("Firecrawl API key not configured")

        pages: list[dict[str, Any]] = []
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    payload = {
                        "url": url,
                        "limit": max_pages or FIRECRAWL_MAX_PAGES,
                        "scrapeOptions": {
                            "formats": ["markdown", "html"],
                            "onlyMainContent": True,
                        },
                    }

                    response = await client.post(
                        f"{self._base_url}/crawl",
                        headers=self._headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("success") and "data" in data:
                        pages = data["data"]
                        break

                    error_msg = data.get("error", "Unknown error")
                    raise CrawlError(f"Firecrawl error: {error_msg}")

            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                wait_time = self._retry_delay_base * (2**attempt)
                logger.warning(
                    "Crawl attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                    attempt + 1,
                    self._max_retries,
                    url,
                    str(e),
                    wait_time,
                )
                import asyncio

                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                last_error = e
                status_code = e.response.status_code

                if status_code == 429:  # Rate limit
                    wait_time = self._retry_delay_base * (2**attempt) * 2
                    logger.warning(
                        "Rate limited on %s. Retrying in %.1fs",
                        url,
                        wait_time,
                    )
                    import asyncio

                    await asyncio.sleep(wait_time)
                elif status_code >= 500:  # Server error, retry
                    wait_time = self._retry_delay_base * (2**attempt)
                    logger.warning(
                        "Server error %d on %s. Retrying in %.1fs",
                        status_code,
                        url,
                        wait_time,
                    )
                    import asyncio

                    await asyncio.sleep(wait_time)
                else:
                    # Client error, don't retry
                    raise CrawlError(f"HTTP {status_code}: {str(e)}") from e

        if not pages and last_error:
            raise CrawlRetryExhaustedError(
                f"Failed to crawl {url} after {self._max_retries} attempts"
            ) from last_error

        return pages

    async def scrape_url(self, url: str) -> dict[str, Any] | None:
        """Scrape a single URL.

        Args:
            url: The URL to scrape.

        Returns:
            Scraped data or None if failed.
        """
        if not self._api_key:
            return None

        for attempt in range(self._max_retries):
            try:
                async with httpx.AsyncClient(timeout=self._timeout) as client:
                    payload = {
                        "url": url,
                        "formats": ["markdown", "html"],
                        "onlyMainContent": True,
                    }

                    response = await client.post(
                        f"{self._base_url}/scrape",
                        headers=self._headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()

                    if data.get("success") and "data" in data:
                        return data["data"]

                    return None

            except (httpx.TimeoutException, httpx.ConnectError):
                wait_time = self._retry_delay_base * (2**attempt)
                import asyncio

                await asyncio.sleep(wait_time)

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 429:
                    wait_time = self._retry_delay_base * (2**attempt) * 2
                    import asyncio

                    await asyncio.sleep(wait_time)
                else:
                    return None

        return None


class EntityWebEnricher:
    """Enrich entity data with web-crawled information.

    This class coordinates crawling multiple sources for an entity,
    handles deduplication, and tracks crawl history.
    """

    # Search URL templates by source type
    SEARCH_URLS: dict[str, str] = {
        "news": "https://news.google.com/rss/search?q={query}",
        "company_registry": "https://receitaws.com.br/v1/cnpj/{cnpj}",
    }

    def __init__(
        self,
        client: FirecrawlClient | None = None,
        dedup_store: DeduplicationStore | None = None,
    ) -> None:
        """Initialize the enricher.

        Args:
            client: Firecrawl client instance. Creates default if None.
            dedup_store: Deduplication store. Creates in-memory if None.
        """
        self._client = client or FirecrawlClient()
        self._dedup_store = dedup_store or InMemoryDeduplicationStore()

    def _calculate_relevance(
        self,
        content: str,
        entity_name: str,
        identifier: str | None,
    ) -> float:
        """Calculate relevance score for crawled content.

        Args:
            content: The crawled content.
            entity_name: Entity name to match against.
            identifier: Optional CPF/CNPJ identifier.

        Returns:
            Relevance score between 0 and 1.
        """
        content_lower = content.lower()
        name_lower = entity_name.lower()

        score = 0.0

        # Name match scoring
        if name_lower in content_lower:
            score += 0.5

        # Identifier match scoring (higher weight)
        if identifier:
            clean_id = identifier.replace(".", "").replace("-", "").replace("/", "")
            if clean_id in content:
                score += 0.4
            # Also check formatted versions
            if len(clean_id) == 14:  # CNPJ
                formatted = f"{clean_id[:2]}.{clean_id[2:5]}.{clean_id[5:8]}/{clean_id[8:12]}-{clean_id[12:]}"
                if formatted in content:
                    score += 0.3

        # Content quality scoring
        if len(content) > 500:
            score += 0.1

        return min(score, 1.0)

    async def crawl_entity(
        self,
        entity_id: str,
        entity_name: str,
        identifier: str | None,
        sources: list[str],
        max_pages: int = 10,
    ) -> CrawlResult:
        """Crawl multiple sources for an entity.

        Args:
            entity_id: The entity ID.
            entity_name: The entity name.
            identifier: Optional CPF/CNPJ.
            sources: List of source types to crawl.
            max_pages: Max pages per source.

        Returns:
            CrawlResult with crawled pages and metadata.
        """
        result = CrawlResult(entity_id=entity_id)
        pages: list[CrawledPage] = []

        # Check if recently crawled
        last_crawled = await self._dedup_store.get_last_crawled(entity_id)
        if last_crawled:
            last_dt = datetime.fromisoformat(last_crawled.replace("Z", "+00:00"))
            now = datetime.now(UTC)
            hours_since = (now - last_dt).total_seconds() / 3600

            if hours_since < 24:  # Skip if crawled within 24 hours
                logger.info(
                    "Skipping crawl for %s - last crawled %.1f hours ago",
                    entity_id,
                    hours_since,
                )
                result.errors.append(f"Skipped: crawled {hours_since:.1f} hours ago")
                return result

        for source in sources:
            if source == "all":
                # Crawl all available sources
                sources_to_crawl = ["news", "company_registry"]
            else:
                sources_to_crawl = [source]

            for src in sources_to_crawl:
                try:
                    crawled = await self._crawl_source(
                        src, entity_name, identifier, max_pages
                    )
                    pages.extend(crawled)
                except CrawlError as e:
                    logger.warning("Crawl failed for %s: %s", src, str(e))
                    result.errors.append(f"{src}: {str(e)}")

        # Deduplicate by content hash
        seen_hashes: set[str] = set()
        deduplicated: list[CrawledPage] = []

        for page in pages:
            if await self._dedup_store.is_seen(page.content_hash):
                result.deduplicated_count += 1
                continue
            if page.content_hash in seen_hashes:
                result.deduplicated_count += 1
                continue

            seen_hashes.add(page.content_hash)
            deduplicated.append(page)
            await self._dedup_store.mark_seen(page.content_hash, page.url)

        result.pages = deduplicated
        result.total_pages = len(pages)
        result.last_crawled_at = datetime.now(UTC).isoformat()

        await self._dedup_store.set_last_crawled(entity_id, result.last_crawled_at)

        return result

    async def _crawl_source(
        self,
        source: str,
        entity_name: str,
        identifier: str | None,
        max_pages: int,
    ) -> list[CrawledPage]:
        """Crawl a specific source type.

        Args:
            source: Source type (news, company_registry, etc.).
            entity_name: Entity name to search.
            identifier: Optional CPF/CNPJ.
            max_pages: Max pages to crawl.

        Returns:
            List of crawled pages.
        """
        pages: list[CrawledPage] = []

        if source == "company_registry" and identifier and len(identifier) == 14:
            # CNPJ lookup via ReceitaWS
            url = self.SEARCH_URLS["company_registry"].format(cnpj=identifier)
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        data = response.json()
                        if "nome" in data:
                            content = f"{data.get('nome', '')} - {data.get('atividade_principal', '')}"
                            page = CrawledPage(
                                url=url,
                                title=f"Empresa: {data.get('nome', 'N/A')}",
                                content=content,
                                source="company_registry",
                                relevance_score=0.9,
                            )
                            pages.append(page)
            except Exception as e:
                logger.warning("Company registry lookup failed: %s", str(e))

        elif source == "news":
            # News search via Google RSS
            import urllib.parse

            query = urllib.parse.quote(entity_name)
            url = self.SEARCH_URLS["news"].format(query=query)

            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        # Parse RSS for article links
                        import re

                        content = response.text
                        items = re.findall(
                            r"<item>.*?<title>(.*?)</title>.*?<link>(.*?)</link>.*?</item>",
                            content,
                            re.DOTALL,
                        )

                        for title, link in items[:max_pages]:
                            # Scrape each article
                            scraped = await self._client.scrape_url(link)
                            if scraped:
                                content_text = scraped.get("markdown", "") or scraped.get(
                                    "html", ""
                                )
                                relevance = self._calculate_relevance(
                                    content_text, entity_name, identifier
                                )

                                page = CrawledPage(
                                    url=link,
                                    title=title.strip(),
                                    content=content_text[:2000],
                                    source="news",
                                    relevance_score=relevance,
                                )
                                pages.append(page)
            except Exception as e:
                logger.warning("News search failed: %s", str(e))

        return pages


async def crawl_entity(
    entity_id: str,
    entity_name: str,
    identifier: str | None = None,
    sources: list[str] | None = None,
    max_pages: int = 10,
) -> CrawlResult:
    """Convenience function to crawl an entity.

    Args:
        entity_id: The entity ID.
        entity_name: The entity name.
        identifier: Optional CPF/CNPJ.
        sources: List of sources to crawl. Defaults to ["news"].
        max_pages: Max pages per source.

    Returns:
        CrawlResult with crawled data.
    """
    enricher = EntityWebEnricher()
    return await enricher.crawl_entity(
        entity_id=entity_id,
        entity_name=entity_name,
        identifier=identifier,
        sources=sources or ["news"],
        max_pages=max_pages,
    )
