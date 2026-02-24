"""Tests for new Phase 14 pattern queries."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from icarus.services.pattern_service import PATTERN_QUERIES, run_pattern


def test_debtor_contracts_registered() -> None:
    assert "debtor_contracts" in PATTERN_QUERIES
    assert PATTERN_QUERIES["debtor_contracts"] == "pattern_debtor_contracts"


def test_embargoed_receiving_registered() -> None:
    assert "embargoed_receiving" in PATTERN_QUERIES
    assert PATTERN_QUERIES["embargoed_receiving"] == "pattern_embargoed_receiving"


def test_loan_debtor_registered() -> None:
    assert "loan_debtor" in PATTERN_QUERIES
    assert PATTERN_QUERIES["loan_debtor"] == "pattern_loan_debtor"


def test_donation_amendment_loop_registered() -> None:
    assert "donation_amendment_loop" in PATTERN_QUERIES
    assert PATTERN_QUERIES["donation_amendment_loop"] == "pattern_donation_amendment_loop"


def test_amendment_beneficiary_contracts_registered() -> None:
    assert "amendment_beneficiary_contracts" in PATTERN_QUERIES
    expected = "pattern_amendment_beneficiary_contracts"
    assert PATTERN_QUERIES["amendment_beneficiary_contracts"] == expected


def test_debtor_health_operator_registered() -> None:
    assert "debtor_health_operator" in PATTERN_QUERIES
    assert PATTERN_QUERIES["debtor_health_operator"] == "pattern_debtor_health_operator"


def test_sanctioned_health_operator_registered() -> None:
    assert "sanctioned_health_operator" in PATTERN_QUERIES
    assert PATTERN_QUERIES["sanctioned_health_operator"] == "pattern_sanctioned_health_operator"


def test_shell_company_contracts_registered() -> None:
    assert "shell_company_contracts" in PATTERN_QUERIES
    assert PATTERN_QUERIES["shell_company_contracts"] == "pattern_shell_company_contracts"


def test_pattern_count_is_thirteen() -> None:
    assert len(PATTERN_QUERIES) == 13


@pytest.mark.anyio
async def test_run_unknown_pattern_returns_empty() -> None:
    session = AsyncMock()
    result = await run_pattern(session, "nonexistent_pattern")
    assert result == []


@pytest.mark.anyio
async def test_debtor_contracts_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "total_debt", "total_contracts", "debt_count",
        "contract_count", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Test Corp",
        "company_cnpj": "12345678000100",
        "company_id": "4:abc:123",
        "total_debt": 100000.0,
        "total_contracts": 500000.0,
        "debt_count": 2,
        "contract_count": 3,
        "pattern_id": "debtor_contracts",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "debtor_contracts")

    assert len(results) == 1
    assert results[0].pattern_id == "debtor_contracts"
    assert results[0].pattern_name == "Devedor com contratos públicos"


@pytest.mark.anyio
async def test_embargoed_receiving_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "embargo_description", "embargo_date", "embargo_biome",
        "embargo_uf",
        "contract_count", "loan_count",
        "total_contract_value", "total_loan_value", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Embargo Corp",
        "company_cnpj": "98765432000100",
        "company_id": "4:abc:456",
        "embargo_description": "Desmatamento ilegal",
        "embargo_date": "2023-01-15",
        "embargo_biome": "Amazonia",
        "embargo_uf": "PA",
        "contract_count": 5,
        "loan_count": 1,
        "total_contract_value": 2000000.0,
        "total_loan_value": 500000.0,
        "pattern_id": "embargoed_receiving",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "embargoed_receiving")

    assert len(results) == 1
    assert results[0].pattern_id == "embargoed_receiving"
    assert results[0].pattern_name == "Embargada recebendo recursos"


@pytest.mark.anyio
async def test_loan_debtor_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "total_loans", "total_debt", "loan_count",
        "debt_count", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Loan Debtor Corp",
        "company_cnpj": "11222333000144",
        "company_id": "4:abc:789",
        "total_loans": 3000000.0,
        "total_debt": 750000.0,
        "loan_count": 2,
        "debt_count": 4,
        "pattern_id": "loan_debtor",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "loan_debtor")

    assert len(results) == 1
    assert results[0].pattern_id == "loan_debtor"
    assert results[0].pattern_name == "Tomador de empréstimo com dívida"


@pytest.mark.anyio
async def test_donation_amendment_loop_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "politician_name", "politician_cpf", "politician_id",
        "company_name", "company_cnpj", "company_id",
        "donation_value", "amendment_value", "amendment_object",
        "election_year", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "politician_name": "Pol Test",
        "politician_cpf": "11122233344",
        "politician_id": "4:abc:101",
        "company_name": "Loop Corp",
        "company_cnpj": "12345678000100",
        "company_id": "4:abc:102",
        "donation_value": 50000.0,
        "amendment_value": 2000000.0,
        "amendment_object": "Saude",
        "election_year": 2022,
        "pattern_id": "donation_amendment_loop",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "donation_amendment_loop")

    assert len(results) == 1
    assert results[0].pattern_id == "donation_amendment_loop"
    assert results[0].pattern_name == "Ciclo doação-emenda-benefício"


@pytest.mark.anyio
async def test_amendment_beneficiary_contracts_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "politician_name", "politician_id",
        "company_name", "company_cnpj", "company_id",
        "total_amendment_value", "amendment_count",
        "total_contract_value", "contract_count", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "politician_name": "Pol Test",
        "politician_id": "4:abc:201",
        "company_name": "Amend Corp",
        "company_cnpj": "98765432000100",
        "company_id": "4:abc:202",
        "total_amendment_value": 5000000.0,
        "amendment_count": 3,
        "total_contract_value": 8000000.0,
        "contract_count": 7,
        "pattern_id": "amendment_beneficiary_contracts",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "amendment_beneficiary_contracts")

    assert len(results) == 1
    assert results[0].pattern_id == "amendment_beneficiary_contracts"
    assert results[0].pattern_name == "Beneficiário de emenda com contratos"


@pytest.mark.anyio
async def test_debtor_health_operator_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "total_debt", "debt_count", "facility_count", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Health Debtor Corp",
        "company_cnpj": "11222333000144",
        "company_id": "4:abc:301",
        "total_debt": 1500000.0,
        "debt_count": 5,
        "facility_count": 3,
        "pattern_id": "debtor_health_operator",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "debtor_health_operator")

    assert len(results) == 1
    assert results[0].pattern_id == "debtor_health_operator"
    assert results[0].pattern_name == "Devedor fiscal operando unidade SUS"


@pytest.mark.anyio
async def test_sanctioned_health_operator_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "sanction_type", "sanction_start", "sanction_reason",
        "facility_name", "facility_cnes", "facility_type",
        "facility_uf", "facility_id", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Sanctioned Health Corp",
        "company_cnpj": "55666777000188",
        "company_id": "4:abc:401",
        "sanction_type": "CEIS",
        "sanction_start": "2023-06-01",
        "sanction_reason": "Contrato rescindido",
        "facility_name": "UBS Central",
        "facility_cnes": "1234567",
        "facility_type": "UBS",
        "facility_uf": "SP",
        "facility_id": "4:abc:402",
        "pattern_id": "sanctioned_health_operator",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "sanctioned_health_operator")

    assert len(results) == 1
    assert results[0].pattern_id == "sanctioned_health_operator"
    assert results[0].pattern_name == "Sancionada operando unidade SUS"


@pytest.mark.anyio
async def test_shell_company_contracts_returns_results() -> None:
    mock_record = MagicMock()
    mock_record.__iter__ = lambda self: iter([
        "company_name", "company_cnpj", "company_id",
        "contract_count", "total_value",
        "company_cnae", "company_uf",
        "sector_avg_employees", "sector_total_employees",
        "sector_establishments", "pattern_id",
    ])
    mock_record.__getitem__ = lambda self, key: {
        "company_name": "Shell Corp",
        "company_cnpj": "99888777000166",
        "company_id": "4:abc:501",
        "contract_count": 12,
        "total_value": 4500000.0,
        "company_cnae": "4120400",
        "company_uf": "MG",
        "sector_avg_employees": 2.3,
        "sector_total_employees": 45,
        "sector_establishments": 20,
        "pattern_id": "shell_company_contracts",
    }[key]

    session = AsyncMock()

    with patch("icarus.services.pattern_service.execute_query", new_callable=AsyncMock) as mock_eq:
        mock_eq.return_value = [mock_record]
        results = await run_pattern(session, "shell_company_contracts")

    assert len(results) == 1
    assert results[0].pattern_id == "shell_company_contracts"
    assert results[0].pattern_name == "Empresa com poucos empregados e muitos contratos"
