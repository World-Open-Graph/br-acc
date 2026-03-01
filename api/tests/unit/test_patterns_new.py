"""Community public-safe pattern registry and query contract tests."""

import pytest

from bracc.models.pattern import PATTERN_METADATA
from bracc.services.intelligence_provider import COMMUNITY_PATTERN_IDS, COMMUNITY_PATTERN_QUERIES
from bracc.services.neo4j_service import CypherLoader


def test_community_pattern_registry_exact_ids() -> None:
    assert len(COMMUNITY_PATTERN_IDS) == 8
    assert set(COMMUNITY_PATTERN_IDS) == {
        "sanctioned_still_receiving",
        "amendment_beneficiary_contracts",
        "split_contracts_below_threshold",
        "contract_concentration",
        "embargoed_receiving",
        "debtor_contracts",
        "srp_multi_org_hitchhiking",
        "inexigibility_recurrence",
    }


def test_community_pattern_query_mapping_is_complete() -> None:
    assert set(COMMUNITY_PATTERN_QUERIES.keys()) == set(COMMUNITY_PATTERN_IDS)
    for query_name in COMMUNITY_PATTERN_QUERIES.values():
        assert query_name.startswith("public_pattern_")


@pytest.mark.parametrize("query_name", COMMUNITY_PATTERN_QUERIES.values())
def test_public_pattern_query_files_load(query_name: str) -> None:
    try:
        CypherLoader.load(query_name)
    finally:
        CypherLoader.clear_cache()


@pytest.mark.parametrize("query_name", COMMUNITY_PATTERN_QUERIES.values())
def test_public_pattern_query_required_return_aliases(query_name: str) -> None:
    try:
        cypher = CypherLoader.load(query_name)
    finally:
        CypherLoader.clear_cache()

    for required_alias in (
        " AS pattern_id",
        " AS risk_signal",
        " AS amount_total",
        " AS window_start",
        " AS window_end",
        " AS evidence_refs",
        " AS evidence_count",
    ):
        assert required_alias in cypher, f"{query_name}.cypher missing alias: {required_alias}"


@pytest.mark.parametrize("pattern_id", COMMUNITY_PATTERN_IDS)
def test_community_pattern_metadata_is_present(pattern_id: str) -> None:
    meta = PATTERN_METADATA.get(pattern_id)
    assert meta is not None
    assert meta.get("name_pt")
    assert meta.get("name_en")
    assert meta.get("desc_pt")
    assert meta.get("desc_en")


def test_threshold_params_used_in_threshold_patterns() -> None:
    query_params = {
        "public_pattern_split_contracts_below_threshold": "$pattern_split_threshold_value",
        "public_pattern_contract_concentration": "$pattern_share_threshold",
        "public_pattern_srp_multi_org_hitchhiking": "$pattern_srp_min_orgs",
        "public_pattern_inexigibility_recurrence": "$pattern_inexig_min_recurrence",
    }
    for query_name, required_param in query_params.items():
        try:
            cypher = CypherLoader.load(query_name)
        finally:
            CypherLoader.clear_cache()
        assert required_param in cypher, f"{query_name}.cypher missing {required_param}"
