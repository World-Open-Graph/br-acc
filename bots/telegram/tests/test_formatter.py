"""Tests for the response formatter."""

from bracc_telegram.formatter import (
    format_cnpj,
    format_company_graph,
    format_error,
    format_meta,
    format_rate_limit_exceeded,
    format_search_results,
)


class TestFormatCnpj:
    def test_formats_14_digits(self) -> None:
        assert format_cnpj("00000000000191") == "00.000.000/0001-91"

    def test_returns_raw_if_not_14(self) -> None:
        assert format_cnpj("12345") == "12345"

    def test_strips_existing_formatting(self) -> None:
        assert format_cnpj("00.000.000/0001-91") == "00.000.000/0001-91"


class TestFormatCompanyGraph:
    def test_empty_nodes(self) -> None:
        result = format_company_graph({"nodes": [], "edges": []})
        assert "Nenhum resultado" in result

    def test_basic_company(self) -> None:
        data = {
            "center_id": "node1",
            "nodes": [
                {
                    "id": "node1",
                    "label": "PETROBRAS",
                    "type": "company",
                    "properties": {"cnpj": "33000167000101"},
                    "sources": [{"database": "cnpj"}],
                },
                {
                    "id": "node2",
                    "label": "Contrato XYZ",
                    "type": "contract",
                    "properties": {},
                    "sources": [],
                },
            ],
            "edges": [{"id": "e1", "source": "node1", "target": "node2", "type": "TEM"}],
        }
        result = format_company_graph(data)
        assert "PETROBRAS" in result
        assert "33.000.167/0001-01" in result
        assert "Conexões encontradas" in result
        assert "contract" in result


class TestFormatSearchResults:
    def test_empty_results(self) -> None:
        result = format_search_results({"results": [], "total": 0})
        assert "Nenhum resultado" in result

    def test_with_results(self) -> None:
        data = {
            "total": 2,
            "results": [
                {"name": "EMPRESA A", "type": "company", "document": "12345678000199"},
                {"name": "EMPRESA B", "type": "company", "document": None},
            ],
        }
        result = format_search_results(data)
        assert "EMPRESA A" in result
        assert "EMPRESA B" in result
        assert "2 encontrados" in result


class TestFormatMeta:
    def test_basic_meta(self) -> None:
        data = {
            "total_nodes": 1_000_000,
            "total_relationships": 5_000_000,
            "company_count": 50_000,
            "contract_count": 200_000,
            "sanction_count": 1_000,
            "source_health": {"implemented_sources": 45, "loaded_sources": 30},
        }
        result = format_meta(data)
        assert "1,000,000" in result
        assert "Empresas" in result
        assert "45" in result


class TestFormatRateLimitExceeded:
    def test_message_content(self) -> None:
        result = format_rate_limit_exceeded(15)
        assert "15" in result
        assert "Limite" in result


class TestFormatError:
    def test_with_detail(self) -> None:
        result = format_error("Something went wrong")
        assert "Erro" in result
        assert "Something went wrong" in result

    def test_without_detail(self) -> None:
        result = format_error()
        assert "Erro" in result
