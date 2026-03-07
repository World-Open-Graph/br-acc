import pytest
from httpx import AsyncClient

from bracc.services.neo4j_service import CypherLoader


def _load_cypher(name: str) -> str:
    try:
        return CypherLoader.load(name)
    finally:
        CypherLoader.clear_cache()


class TestEmendasCypherQueries:
    """Validate the Cypher queries used by the emendas endpoint."""

    def test_list_query_filters_by_source(self) -> None:
        cypher = _load_cypher("emendas_tesouro_list")
        assert "source: 'tesouro_emendas'" in cypher

    def test_list_query_has_pagination(self) -> None:
        cypher = _load_cypher("emendas_tesouro_list")
        assert "$skip" in cypher
        assert "$limit" in cypher

    def test_list_query_uses_optional_match(self) -> None:
        cypher = _load_cypher("emendas_tesouro_list")
        assert "OPTIONAL MATCH" in cypher

    def test_count_query_exists(self) -> None:
        cypher = _load_cypher("emendas_tesouro_count")
        assert "count(p)" in cypher

    def test_count_query_filters_by_source(self) -> None:
        cypher = _load_cypher("emendas_tesouro_count")
        assert "source: 'tesouro_emendas'" in cypher


class TestEmendasEndpoint:
    """Validate the /api/v1/emendas/ endpoint behaviour."""

    @pytest.mark.anyio
    async def test_emendas_rejects_negative_skip(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/emendas/?skip=-1")
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_emendas_rejects_zero_limit(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/emendas/?limit=0")
        assert response.status_code == 422

    @pytest.mark.anyio
    async def test_emendas_rejects_excessive_limit(
        self, client: AsyncClient
    ) -> None:
        response = await client.get("/api/v1/emendas/?limit=101")
        assert response.status_code == 422
