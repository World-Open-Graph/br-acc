from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from bracc.config import settings
from bracc.models.pattern import PATTERN_METADATA
from bracc.services.intelligence_provider import COMMUNITY_PATTERN_IDS, COMMUNITY_PATTERN_QUERIES
from bracc.services.neo4j_service import CypherLoader


@pytest.fixture(autouse=True)
def _enable_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "patterns_enabled", True)


def test_all_community_patterns_have_metadata() -> None:
    for pattern_id in COMMUNITY_PATTERN_IDS:
        assert pattern_id in PATTERN_METADATA, f"Missing metadata for {pattern_id}"


def test_all_community_patterns_have_query_files() -> None:
    for query_name in COMMUNITY_PATTERN_QUERIES.values():
        try:
            CypherLoader.load(query_name)
        except FileNotFoundError:
            pytest.fail(f"Missing .cypher file for query {query_name}.cypher")
        finally:
            CypherLoader.clear_cache()


def test_pattern_metadata_has_required_fields() -> None:
    for pid, meta in PATTERN_METADATA.items():
        assert "name_pt" in meta, f"{pid} missing name_pt"
        assert "name_en" in meta, f"{pid} missing name_en"
        assert "desc_pt" in meta, f"{pid} missing desc_pt"
        assert "desc_en" in meta, f"{pid} missing desc_en"


@pytest.mark.anyio
async def test_list_patterns_endpoint(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patterns/")
    assert response.status_code == 200
    data = response.json()
    assert "patterns" in data
    assert len(data["patterns"]) == 8

    ids = {row["id"] for row in data["patterns"]}
    assert ids == set(COMMUNITY_PATTERN_IDS)


@pytest.mark.anyio
async def test_patterns_endpoint_returns_503_when_disabled(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "patterns_enabled", False)
    response = await client.get("/api/v1/patterns/")
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


@pytest.mark.anyio
async def test_invalid_pattern_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patterns/test-id/nonexistent_pattern")
    assert response.status_code == 404
    assert "Pattern not found" in response.json()["detail"]


@pytest.mark.anyio
async def test_patterns_endpoint_forwards_include_probable(client: AsyncClient) -> None:
    with patch("bracc.routers.patterns.run_all_patterns", new_callable=AsyncMock) as mock_run_all:
        mock_run_all.return_value = []
        response = await client.get("/api/v1/patterns/test-id?include_probable=true")

    assert response.status_code == 200
    mock_run_all.assert_awaited_once()
    _driver, entity_id, _lang = mock_run_all.await_args.args
    assert entity_id == "test-id"
    assert mock_run_all.await_args.kwargs["include_probable"] is True


@pytest.mark.anyio
async def test_specific_pattern_endpoint_forwards_include_probable(client: AsyncClient) -> None:
    with patch("bracc.routers.patterns.run_pattern", new_callable=AsyncMock) as mock_run_one:
        mock_run_one.return_value = []
        response = await client.get(
            "/api/v1/patterns/test-id/debtor_contracts?include_probable=true",
        )

    assert response.status_code == 200
    mock_run_one.assert_awaited_once()
    _session, pattern_name, entity_id, _lang = mock_run_one.await_args.args
    assert pattern_name == "debtor_contracts"
    assert entity_id == "test-id"
    assert mock_run_one.await_args.kwargs["include_probable"] is True


def test_community_queries_use_bind_params() -> None:
    for query_name in COMMUNITY_PATTERN_QUERIES.values():
        try:
            cypher = CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()
        assert "$company_id" in cypher, f"{query_name}.cypher missing $company_id"
        assert "$company_identifier" in cypher, f"{query_name}.cypher missing $company_identifier"
        assert "$company_identifier_formatted" in cypher, (
            f"{query_name}.cypher missing $company_identifier_formatted"
        )
        assert "${" not in cypher, f"{query_name}.cypher uses unsafe string interpolation"


def test_no_banned_words_in_pattern_metadata() -> None:
    banned = {"suspicious", "corrupt", "criminal", "fraudulent", "illegal", "guilty"}
    for pid, meta in PATTERN_METADATA.items():
        for key, value in meta.items():
            for word in banned:
                assert word not in value.lower(), (
                    f"Banned word '{word}' in {pid}.{key}: {value}"
                )
