import pytest
from httpx import AsyncClient

from icarus.models.pattern import PATTERN_METADATA
from icarus.services.pattern_service import PATTERN_QUERIES


def test_all_patterns_have_metadata() -> None:
    for pattern_id in PATTERN_QUERIES:
        assert pattern_id in PATTERN_METADATA, f"Missing metadata for {pattern_id}"


def test_all_patterns_have_query_files() -> None:
    from icarus.services.neo4j_service import CypherLoader

    for pattern_id, query_name in PATTERN_QUERIES.items():
        try:
            CypherLoader.load(query_name)
        except FileNotFoundError:
            pytest.fail(f"Missing .cypher file for pattern {pattern_id}: {query_name}.cypher")
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
    assert len(data["patterns"]) == 13

    ids = {p["id"] for p in data["patterns"]}
    assert "self_dealing_amendment" in ids
    assert "donation_contract_loop" in ids


@pytest.mark.anyio
async def test_invalid_pattern_returns_404(client: AsyncClient) -> None:
    response = await client.get("/api/v1/patterns/test-id/nonexistent_pattern")
    assert response.status_code == 404
    assert "Pattern not found" in response.json()["detail"]


def test_no_banned_words_in_pattern_metadata() -> None:
    banned = {"suspicious", "corrupt", "criminal", "fraudulent", "illegal", "guilty"}
    for pid, meta in PATTERN_METADATA.items():
        for key, value in meta.items():
            for word in banned:
                assert word not in value.lower(), (
                    f"Banned word '{word}' in {pid}.{key}: {value}"
                )
