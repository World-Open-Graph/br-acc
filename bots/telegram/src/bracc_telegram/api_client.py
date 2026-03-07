"""HTTP client for the BR-ACC public API."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from bracc_telegram.config import get_api_url

logger = logging.getLogger(__name__)

_TIMEOUT = 15.0


class BraccApiClient:
    """Async client that wraps calls to the BR-ACC FastAPI backend."""

    def __init__(self, base_url: str | None = None) -> None:
        self._base_url = (base_url or get_api_url()).rstrip("/")

    async def get_company_graph(self, cnpj: str) -> dict[str, Any]:
        """Fetch the public company subgraph by CNPJ.

        Calls ``GET /api/v1/public/graph/company/{cnpj}``.
        """
        url = f"{self._base_url}/api/v1/public/graph/company/{cnpj}"
        return await self._get(url)

    async def search(self, query: str, limit: int = 5) -> dict[str, Any]:
        """Full-text search across entities.

        Calls ``GET /api/v1/search?q={query}&size={limit}``.
        """
        url = f"{self._base_url}/api/v1/search"
        return await self._get(url, params={"q": query, "size": limit})

    async def get_meta(self) -> dict[str, Any]:
        """Fetch aggregated graph statistics.

        Calls ``GET /api/v1/public/meta``.
        """
        url = f"{self._base_url}/api/v1/public/meta"
        return await self._get(url)

    async def health_check(self) -> bool:
        """Return ``True`` if the API is reachable."""
        try:
            url = f"{self._base_url}/health"
            data = await self._get(url)
            return data.get("status") == "ok"
        except (httpx.HTTPError, Exception):  # noqa: BLE001
            return False

    # ------------------------------------------------------------------

    async def _get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.get(url, params=params)
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result
