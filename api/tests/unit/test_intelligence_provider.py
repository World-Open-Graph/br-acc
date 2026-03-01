from unittest.mock import AsyncMock, patch

import pytest
from pytest import MonkeyPatch

from bracc.config import settings
from bracc.services import intelligence_provider as provider_module


def test_falls_back_to_community_when_full_modules_missing(
    monkeypatch: MonkeyPatch,
) -> None:
    original_tier = settings.product_tier
    try:
        monkeypatch.setattr(settings, "product_tier", "full")
        monkeypatch.setattr(
            provider_module,
            "_full_modules_available",
            lambda: False,
        )
        provider_module._PROVIDER_CACHE.clear()

        provider = provider_module.get_default_provider()

        assert isinstance(provider, provider_module.CommunityIntelligenceProvider)
    finally:
        provider_module._PROVIDER_CACHE.clear()
        settings.product_tier = original_tier


def test_keeps_full_when_modules_are_available(
    monkeypatch: MonkeyPatch,
) -> None:
    original_tier = settings.product_tier
    try:
        monkeypatch.setattr(settings, "product_tier", "full")
        monkeypatch.setattr(
            provider_module,
            "_full_modules_available",
            lambda: True,
        )
        provider_module._PROVIDER_CACHE.clear()

        provider = provider_module.get_default_provider()

        assert isinstance(provider, provider_module.FullIntelligenceProvider)
    finally:
        provider_module._PROVIDER_CACHE.clear()
        settings.product_tier = original_tier


def test_community_provider_exposes_exactly_8_patterns() -> None:
    provider = provider_module.CommunityIntelligenceProvider()
    pattern_ids = [row["id"] for row in provider.list_patterns()]
    assert len(pattern_ids) == 8
    assert set(pattern_ids) == set(provider_module.COMMUNITY_PATTERN_IDS)


def test_community_patterns_have_query_files() -> None:
    from bracc.services.neo4j_service import CypherLoader

    for query_name in provider_module.COMMUNITY_PATTERN_QUERIES.values():
        try:
            CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()


@pytest.mark.anyio
async def test_community_provider_enforces_public_evidence_fields() -> None:
    provider = provider_module.CommunityIntelligenceProvider()
    fake_session = object()

    with (
        patch(
            "bracc.services.intelligence_provider.execute_query_single",
            new_callable=AsyncMock,
            return_value={
                "entity_labels": ["Company"],
                "e": {"cnpj": "11.111.111/0001-11"},
            },
        ),
        patch(
            "bracc.services.intelligence_provider.execute_query",
            new_callable=AsyncMock,
            return_value=[
                {
                    "pattern_id": "debtor_contracts",
                    "cnpj": "11.111.111/0001-11",
                    "company_name": "Empresa Teste",
                    "amount_total": 1000.0,
                    "window_start": "2024-01-01",
                    "window_end": "2024-12-31",
                    "evidence_refs": ["contract:1", "debt:2"],
                }
            ],
        ),
    ):
        results = await provider.run_pattern(
            fake_session,  # type: ignore[arg-type]
            pattern_id="debtor_contracts",
            entity_id="c1",
            lang="pt",
        )

    assert len(results) == 1
    payload = results[0].data
    assert payload["evidence_refs"]
    assert "risk_signal" in payload
