"""Tests for the API client using mocked HTTP responses."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bracc_telegram.api_client import BraccApiClient


@pytest.fixture
def client() -> BraccApiClient:
    return BraccApiClient(base_url="http://test-api:8000")


def _mock_httpx(response_data: dict) -> MagicMock:  # type: ignore[type-arg]
    """Create a mock httpx.AsyncClient that returns *response_data* on GET."""
    mock_resp = MagicMock()
    mock_resp.json.return_value = response_data
    mock_resp.raise_for_status = MagicMock()

    mock_http = AsyncMock()
    mock_http.get = AsyncMock(return_value=mock_resp)
    mock_http.__aenter__ = AsyncMock(return_value=mock_http)
    mock_http.__aexit__ = AsyncMock(return_value=False)
    return mock_http


class TestBraccApiClient:
    @pytest.mark.asyncio
    async def test_get_company_graph(self, client: BraccApiClient) -> None:
        mock_response = {
            "nodes": [{"id": "n1", "label": "Test Corp"}],
            "edges": [],
            "center_id": "n1",
        }
        with patch("bracc_telegram.api_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_httpx(mock_response)
            result = await client.get_company_graph("00000000000191")

        assert result["center_id"] == "n1"
        assert len(result["nodes"]) == 1

    @pytest.mark.asyncio
    async def test_search(self, client: BraccApiClient) -> None:
        mock_response = {
            "results": [{"name": "Petrobras", "type": "company"}],
            "total": 1,
        }
        with patch("bracc_telegram.api_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_httpx(mock_response)
            result = await client.search("Petrobras")

        assert result["total"] == 1

    @pytest.mark.asyncio
    async def test_get_meta(self, client: BraccApiClient) -> None:
        mock_response = {"total_nodes": 1000, "total_relationships": 5000}
        with patch("bracc_telegram.api_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_httpx(mock_response)
            result = await client.get_meta()

        assert result["total_nodes"] == 1000

    @pytest.mark.asyncio
    async def test_health_check_ok(self, client: BraccApiClient) -> None:
        with patch("bracc_telegram.api_client.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value = _mock_httpx({"status": "ok"})
            assert await client.health_check() is True

    @pytest.mark.asyncio
    async def test_health_check_fail(self, client: BraccApiClient) -> None:
        with patch("bracc_telegram.api_client.httpx.AsyncClient") as mock_cls:
            mock_http = AsyncMock()
            mock_http.get = AsyncMock(side_effect=Exception("connection refused"))
            mock_http.__aenter__ = AsyncMock(return_value=mock_http)
            mock_http.__aexit__ = AsyncMock(return_value=False)
            mock_cls.return_value = mock_http
            assert await client.health_check() is False
