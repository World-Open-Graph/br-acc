from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock

from bracc_etl.pipelines.comprasnet import ComprasnetPipeline

FIXTURES = Path(__file__).parent / "fixtures"


def _make_pipeline() -> ComprasnetPipeline:
    driver = MagicMock()
    return ComprasnetPipeline(driver, data_dir=str(FIXTURES))


def _extract_from_fixtures(pipeline: ComprasnetPipeline) -> None:
    """Load raw records from fixture JSON."""
    fixture_file = FIXTURES / "comprasnet_contratos.json"
    pipeline._raw_records = json.loads(fixture_file.read_text(encoding="utf-8"))


def test_pipeline_name_and_source_id() -> None:
    pipeline = _make_pipeline()
    assert pipeline.name == "comprasnet"
    assert pipeline.source_id == "comprasnet"


def test_transform_produces_correct_contracts() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    # 5 records: 3 valid PJ, 1 PF (skipped), 1 zero-value (skipped) = 3
    assert len(pipeline.contracts) == 3


def test_transform_formats_cnpj() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    cnpjs = [c["cnpj"] for c in pipeline.contracts]
    assert "11.222.333/0001-81" in cnpjs
    assert "44.555.666/0001-99" in cnpjs
    assert "77.888.999/0001-00" in cnpjs


def test_transform_skips_pessoa_fisica() -> None:
    """Contracts with tipoPessoa=PF should be skipped."""
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    names = [c["razao_social"] for c in pipeline.contracts]
    assert "JOAO DA SILVA" not in names


def test_transform_skips_zero_value() -> None:
    """Contracts with zero value should be skipped."""
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    names = [c["razao_social"] for c in pipeline.contracts]
    assert "FORNECEDOR ZERADO LTDA" not in names


def test_transform_normalizes_names() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    # "Serviços Gerais ME" -> "SERVICOS GERAIS ME" (normalized)
    names = [c["razao_social"] for c in pipeline.contracts]
    assert any("SERVICOS GERAIS" in n for n in names)


def test_transform_extracts_contracting_org() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    orgs = {c["contracting_org"] for c in pipeline.contracts}
    assert "MINISTERIO DA SAUDE" in orgs
    assert "MINISTERIO DA EDUCACAO" in orgs


def test_transform_sets_source() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    for c in pipeline.contracts:
        assert c["source"] == "comprasnet"


def test_transform_contract_ids_are_unique() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    ids = [c["contract_id"] for c in pipeline.contracts]
    assert len(set(ids)) == len(ids)


def test_transform_extracts_values() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    values = sorted(c["value"] for c in pipeline.contracts)
    assert 150000.00 in values
    assert 480000.00 in values
    assert 3200000.50 in values


def test_transform_extracts_bid_reference() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    bid_refs = {c["bid_id"] for c in pipeline.contracts}
    assert "11222333000181-1-000050/2023" in bid_refs
    assert "44555666000199-1-000010/2024" in bid_refs
    assert "77888999000100-1-000020/2024" in bid_refs


def test_transform_extracts_dates() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    dates = {c["date"] for c in pipeline.contracts}
    assert "2024-01-15" in dates
    assert "2024-03-01" in dates
    assert "2024-02-15" in dates


def test_transform_sanitizes_absurd_future_date() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)

    pipeline._raw_records.append({
        "numeroControlePNCP": "00600371000104-2-000035/2024",
        "niFornecedor": "00600371000104",
        "tipoPessoa": "PJ",
        "nomeRazaoSocialFornecedor": "FORNECEDOR FUTURO LTDA",
        "objetoContrato": "OBJETO TESTE",
        "valorGlobal": 1000.0,
        "dataAssinatura": "2102-09-24",
        "dataVigenciaFim": "2103-01-01",
        "orgaoEntidade": {
            "cnpj": "00394445000166",
            "razaoSocial": "CAMARA MUNICIPAL DE CORDEIROPOLIS",
        },
        "tipoContrato": {"id": 1, "nome": "Empenho"},
        "anoContrato": 2024,
        "sequencialContrato": 35,
    })

    pipeline.transform()
    target = next(
        c for c in pipeline.contracts if c["contract_id"] == "00600371000104-2-000035/2024"
    )
    assert target["date"] == ""
    assert target["date_end"] == ""


def test_transform_limit() -> None:
    pipeline = _make_pipeline()
    pipeline.limit = 2
    _extract_from_fixtures(pipeline)
    pipeline.transform()

    assert len(pipeline.contracts) == 2


def test_transform_caps_absurd_value() -> None:
    """Contracts with values above R$ 10B (data entry errors) get value=None."""
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)

    # Inject a record with a garbage R$ 50B value
    pipeline._raw_records.append({
        "numeroControlePNCP": "88777666000100-2-000099/2024",
        "niFornecedor": "88777666000100",
        "tipoPessoa": "PJ",
        "nomeRazaoSocialFornecedor": "EMPRESA ABSURDA LTDA",
        "objetoContrato": "MUDANCA DE 2 PESSOAS",
        "valorGlobal": 50_000_000_000.0,
        "dataAssinatura": "2024-06-01",
        "dataVigenciaFim": "2024-12-31",
        "orgaoEntidade": {
            "cnpj": "00394445000166",
            "razaoSocial": "MINISTERIO DA SAUDE",
        },
        "tipoContrato": {"id": 1, "nome": "Contrato"},
        "anoContrato": 2024,
        "sequencialContrato": 99,
    })

    pipeline.transform()

    absurd = next(
        c for c in pipeline.contracts if c["razao_social"] == "EMPRESA ABSURDA LTDA"
    )
    assert absurd["value"] is None


def test_load_calls_batch_loader() -> None:
    pipeline = _make_pipeline()
    _extract_from_fixtures(pipeline)
    pipeline.transform()
    pipeline.load()

    driver = pipeline.driver
    session = driver.session.return_value.__enter__.return_value
    # Should have called session.run for Contract nodes, Company nodes, VENCEU and REFERENTE_A rels
    assert session.run.call_count >= 4
