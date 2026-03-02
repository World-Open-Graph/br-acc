import pytest
from httpx import AsyncClient

from bracc.routers.search import _escape_lucene


def test_escape_lucene_cnpj() -> None:
    assert _escape_lucene("00.000.000/0001-00") == "00.000.000\\/0001\\-00"


def test_escape_lucene_plain_text() -> None:
    assert _escape_lucene("silva construcoes") == "silva construcoes"


def test_escape_lucene_all_special_chars() -> None:
    for ch in r'+-&|!(){}[]^"~*?:\/':
        assert f"\\{ch}" in _escape_lucene(ch)


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
