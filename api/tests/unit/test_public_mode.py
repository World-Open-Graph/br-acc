from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, patch

import pytest

from bracc.config import settings
from bracc.models.entity import SourceAttribution
from bracc.models.pattern import PatternResult

if TYPE_CHECKING:
    from httpx import AsyncClient


class _FakeNode(dict):
    def __init__(self, element_id: str, labels: list[str], **props: object) -> None:
        super().__init__(props)
        self.element_id = element_id
        self.labels = set(labels)


class _FakeEndpoint:
    def __init__(self, element_id: str) -> None:
        self.element_id = element_id


class _FakeRel(dict):
    def __init__(
        self,
        element_id: str,
        source_id: str,
        target_id: str,
        rel_type: str,
        **props: object,
    ) -> None:
        super().__init__(props)
        self.element_id = element_id
        self.start_node = _FakeEndpoint(source_id)
        self.end_node = _FakeEndpoint(target_id)
        self.type = rel_type


@pytest.mark.anyio
async def test_entity_lookup_disabled_in_public_mode(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_mode", True)
    monkeypatch.setattr(settings, "public_allow_entity_lookup", False)
    response = await client.get("/api/v1/entity/12345678901")
    assert response.status_code == 403
    assert "disabled in public mode" in response.json()["detail"]


@pytest.mark.anyio
async def test_person_lookup_disabled_in_public_mode(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_mode", True)
    monkeypatch.setattr(settings, "public_allow_entity_lookup", True)
    monkeypatch.setattr(settings, "public_allow_person", False)
    response = await client.get("/api/v1/entity/12345678901")
    assert response.status_code == 403
    assert "Person lookup disabled" in response.json()["detail"]


@pytest.mark.anyio
async def test_search_hides_person_nodes_in_public_mode(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_mode", True)
    monkeypatch.setattr(settings, "public_allow_person", False)
    mocked_records = [
        {
            "node": {"name": "Pessoa Teste", "cpf": "12345678900"},
            "node_labels": ["Person"],
            "node_id": "p1",
            "score": 3.1,
            "document_id": "12345678900",
        },
        {
            "node": {"razao_social": "Empresa Teste", "cnpj": "11.111.111/0001-11"},
            "node_labels": ["Company"],
            "node_id": "c1",
            "score": 2.9,
            "document_id": "11.111.111/0001-11",
        },
    ]
    with patch(
        "bracc.routers.search.execute_query",
        new_callable=AsyncMock,
        return_value=mocked_records,
    ):
        response = await client.get("/api/v1/search?q=teste")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["results"][0]["type"] == "company"


@pytest.mark.anyio
async def test_public_meta_endpoint(client: AsyncClient) -> None:
    with patch(
        "bracc.routers.public.execute_query_single",
        new_callable=AsyncMock,
        return_value={
            "total_nodes": 10,
            "total_relationships": 20,
            "company_count": 3,
            "contract_count": 4,
            "sanction_count": 5,
            "finance_count": 6,
            "bid_count": 7,
            "cpi_count": 8,
        },
    ):
        response = await client.get("/api/v1/public/meta")
    assert response.status_code == 200
    payload = response.json()
    assert payload["product"] == "World Transparency Graph"
    assert payload["mode"] == "public_safe"


@pytest.mark.anyio
async def test_public_patterns_company_endpoint(client: AsyncClient) -> None:
    with patch("bracc.routers.public.settings.patterns_enabled", False):
        response = await client.get("/api/v1/public/patterns/company/11111111000111")
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


@pytest.mark.anyio
async def test_public_patterns_company_endpoint_when_enabled(client: AsyncClient) -> None:
    with (
        patch("bracc.routers.public.settings.patterns_enabled", True),
        patch(
            "bracc.routers.public.execute_query_single",
            new_callable=AsyncMock,
            return_value={
                "c": {"cnpj": "11.111.111/0001-11", "razao_social": "Empresa Teste"},
                "entity_labels": ["Company"],
                "entity_id": "c1",
            },
        ),
        patch(
            "bracc.routers.public._PUBLIC_PROVIDER.run_pattern",
            new_callable=AsyncMock,
            return_value=[
                PatternResult(
                    pattern_id="debtor_contracts",
                    pattern_name="Devedor com contratos públicos",
                    description="Coocorrência factual entre dívida ativa e contratos recorrentes",
                    data={
                        "cnpj": "11.111.111/0001-11",
                        "company_name": "Empresa Teste",
                        "risk_signal": 5.0,
                        "amount_total": 120000.0,
                        "window_start": "2024-01-01",
                        "window_end": "2024-12-31",
                        "evidence_refs": ["contract:1", "debt:2"],
                        "evidence_count": 2,
                    },
                    entity_ids=["c1"],
                    sources=[SourceAttribution(database="neo4j_public")],
                    exposure_tier="public_safe",
                    intelligence_tier="community",
                )
            ],
        ),
    ):
        response = await client.get("/api/v1/public/patterns/company/11111111000111")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["patterns"][0]["exposure_tier"] == "public_safe"
    assert payload["patterns"][0]["data"]["evidence_refs"]
    assert payload["patterns"][0]["data"]["risk_signal"] >= 1
    assert "cpf" not in str(payload).lower()


@pytest.mark.anyio
async def test_public_graph_company_filters_person_nodes(client: AsyncClient) -> None:
    with (
        patch(
            "bracc.routers.public.execute_query_single",
            new_callable=AsyncMock,
            return_value={
                "c": {"cnpj": "11.111.111/0001-11", "razao_social": "Empresa Teste"},
                "entity_labels": ["Company"],
                "entity_id": "c1",
            },
        ),
        patch(
            "bracc.routers.public.execute_query",
            new_callable=AsyncMock,
            return_value=[
                {
                    "nodes": [
                        _FakeNode(
                            "c1",
                            ["Company"],
                            razao_social="Empresa Teste",
                            cnpj="11.111.111/0001-11",
                        ),
                        _FakeNode("p1", ["Person"], name="Pessoa Teste", cpf="12345678900"),
                    ],
                    "relationships": [
                        _FakeRel("r1", "c1", "p1", "SOCIO_DE", confidence=1.0),
                    ],
                    "center_id": "c1",
                }
            ],
        ),
    ):
        response = await client.get("/api/v1/public/graph/company/11111111000111")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["nodes"]) == 1
    assert payload["nodes"][0]["type"] == "company"
    assert len(payload["edges"]) == 0


@pytest.mark.anyio
async def test_investigations_disabled_in_public_mode(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "public_mode", True)
    monkeypatch.setattr(settings, "public_allow_investigations", False)
    response = await client.get("/api/v1/investigations/")
    assert response.status_code == 403
    assert "disabled in public mode" in response.json()["detail"]
