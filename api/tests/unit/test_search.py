import pytest
from httpx import AsyncClient


@pytest.mark.anyio
async def test_search_rejects_short_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=a")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_missing_query(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_invalid_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test&page=0")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_search_rejects_oversized_page(client: AsyncClient) -> None:
    response = await client.get("/api/v1/search?q=test&size=200")
    assert response.status_code == 422
