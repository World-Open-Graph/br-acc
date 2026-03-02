from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from bracc.config import settings
from bracc.models.pattern import PATTERN_METADATA
from bracc.services.pattern_service import PATTERN_QUERIES


@pytest.fixture(autouse=True)
def _enable_patterns(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "patterns_enabled", True)


def test_all_patterns_have_metadata() -> None:
    for pattern_id in PATTERN_QUERIES:
        assert pattern_id in PATTERN_METADATA, f"Missing metadata for {pattern_id}"


def test_all_patterns_have_query_files() -> None:
    from bracc.services.neo4j_service import CypherLoader

    for _pattern_id, query_name in PATTERN_QUERIES.items():
        try:
            CypherLoader.load(query_name)
        except FileNotFoundError:
            pytest.fail(f"Missing .cypher file for pattern {query_name}.cypher")
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

    ids = {p["id"] for p in data["patterns"]}
    assert "sanctioned_still_receiving" in ids
    assert "split_contracts_below_threshold" in ids
    assert "srp_multi_org_hitchhiking" in ids
    assert "inexigibility_recurrence" in ids
    assert "debtor_contracts" in ids


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
    _driver, _entity_id, _lang = mock_run_all.await_args.args
    assert _entity_id == "test-id"
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
    _session, _pattern_name, _entity_id, _lang = mock_run_one.await_args.args
    assert _pattern_name == "debtor_contracts"
    assert _entity_id == "test-id"
    assert mock_run_one.await_args.kwargs["include_probable"] is True


def test_patrimony_query_guards_divide_by_zero() -> None:
    """pattern_patrimony.cypher must require patrimonio_declarado > 0 to avoid div-by-zero."""
    from bracc.services.neo4j_service import CypherLoader

    try:
        cypher = CypherLoader.load("pattern_patrimony")
    finally:
        CypherLoader.clear_cache()
    assert "patrimonio_declarado > 0" in cypher, (
        "pattern_patrimony.cypher missing 'patrimonio_declarado > 0' guard — "
        "ratio computation will divide by zero"
    )


def test_pattern_queries_use_parameter_binding() -> None:
    """All pattern .cypher files must use $entity_id parameter binding, not string interpolation."""
    from bracc.services.neo4j_service import CypherLoader
    from bracc.services.pattern_service import PATTERN_QUERIES

    for _pattern_id, query_name in PATTERN_QUERIES.items():
        try:
            cypher = CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()
        assert "$entity_id" in cypher, (
            f"{query_name}.cypher missing $entity_id parameter binding"
        )
        # No f-string or .format() injection patterns
        assert "${" not in cypher, (
            f"{query_name}.cypher uses string interpolation (unsafe)"
        )


def test_no_banned_words_in_pattern_metadata() -> None:
    banned = {"suspicious", "corrupt", "criminal", "fraudulent", "illegal", "guilty"}
    for pid, meta in PATTERN_METADATA.items():
        for key, value in meta.items():
            for word in banned:
                assert word not in value.lower(), (
                    f"Banned word '{word}' in {pid}.{key}: {value}"
                )


def test_pattern_config_defaults() -> None:
    """Verify the agreed hardening defaults are wired in config."""
    assert settings.pattern_temporal_window_years == 4
    assert settings.pattern_min_contract_value == 100000.0
    assert settings.pattern_min_contract_count == 2
    assert settings.pattern_min_debt_value == 50000.0
    assert settings.pattern_same_as_min_confidence == 0.85
    assert settings.pattern_pep_min_confidence == 0.85
    assert settings.pattern_min_recurrence == 2
    assert settings.pattern_min_discrepancy_ratio == 0.30


def test_critical_patterns_use_temporal_guards() -> None:
    """Critical patterns must include temporal_window_years-based filters."""
    from bracc.services.neo4j_service import CypherLoader

    temporal_patterns = [
        "pattern_donation_contract",
        "pattern_self_dealing",
        "pattern_amendment_beneficiary_contracts",
        "pattern_deputy_supplier_loop",
        "pattern_legislator_supplier_loop",
        "pattern_debtor_contracts",
        "pattern_loan_debtor",
        "pattern_embargoed_receiving",
        "pattern_sanctioned_health_operator",
        "pattern_cvm_sanctioned_receiving",
        "pattern_global_pep_contracts",
        "pattern_offshore_connection",
        "pattern_contract_concentration",
        "pattern_shell_company_contracts",
        "pattern_sanctioned_receiving",
    ]

    for query_name in temporal_patterns:
        try:
            cypher = CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()
        assert "$temporal_window_years" in cypher, (
            f"{query_name}.cypher missing $temporal_window_years guard"
        )


def test_pattern_queries_reference_hardening_threshold_params() -> None:
    """Critical patterns must consume configured threshold/confidence params."""
    from bracc.services.neo4j_service import CypherLoader

    checks = {
        "pattern_debtor_contracts": ["$min_debt_value", "$min_contract_count"],
        "pattern_amendment_beneficiary_contracts": ["$min_contract_count", "$min_contract_value"],
        "pattern_offshore_connection": ["$same_as_min_confidence", "$min_contract_value"],
        "pattern_global_pep_contracts": ["$pep_min_confidence", "$min_contract_count"],
        "pattern_deputy_supplier_loop": ["$min_recurrence", "$min_contract_value"],
        "pattern_legislator_supplier_loop": ["$min_recurrence", "$min_contract_value"],
        "pattern_sanctioned_health_operator": ["$min_recurrence"],
        "pattern_patrimony": ["$min_discrepancy_ratio"],
    }
    for query_name, expected_params in checks.items():
        try:
            cypher = CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()
        for param in expected_params:
            assert param in cypher, f"{query_name}.cypher missing {param}"
