import pytest
from httpx import AsyncClient

from icarus.services.neo4j_service import CypherLoader

# Expected node labels that form the IDOR allowlist.
# If a new label is added to the queries, add it here too.
EXPECTED_LABELS = {
    "Person", "Company", "Contract", "Sanction", "Election",
    "Amendment", "Finance", "Embargo", "Health", "Education",
    "Convenio", "LaborStats", "PublicOffice",
}

# Expected entity ID property fields in lookup/coalesce chains.
EXPECTED_ID_FIELDS = {
    "cpf", "cnpj", "contract_id", "sanction_id", "amendment_id",
    "cnes_code", "finance_id", "embargo_id", "school_id", "convenio_id",
    "stats_id",
}


def _load_cypher(name: str) -> str:
    try:
        return CypherLoader.load(name)
    finally:
        CypherLoader.clear_cache()


def test_entity_by_id_has_label_allowlist() -> None:
    """IDOR prevention: entity_by_id.cypher must restrict to known labels."""
    cypher = _load_cypher("entity_by_id")
    for label in EXPECTED_LABELS:
        assert f"e:{label}" in cypher, (
            f"entity_by_id.cypher missing label allowlist entry: {label}"
        )


def test_investigation_add_entity_has_label_allowlist() -> None:
    """IDOR prevention: investigation_add_entity.cypher must restrict to known labels."""
    cypher = _load_cypher("investigation_add_entity")
    for label in EXPECTED_LABELS:
        assert f"e:{label}" in cypher, (
            f"investigation_add_entity.cypher missing label allowlist entry: {label}"
        )


def test_investigation_remove_entity_has_label_allowlist() -> None:
    """IDOR prevention: investigation_remove_entity.cypher must restrict to known labels."""
    cypher = _load_cypher("investigation_remove_entity")
    for label in EXPECTED_LABELS:
        assert f"e:{label}" in cypher, (
            f"investigation_remove_entity.cypher missing label allowlist entry: {label}"
        )


def test_label_allowlists_are_consistent_across_queries() -> None:
    """All three entity-resolving queries must use the same label allowlist."""
    import re

    queries = ["entity_by_id", "investigation_add_entity", "investigation_remove_entity"]
    label_sets: dict[str, set[str]] = {}
    for qname in queries:
        cypher = _load_cypher(qname)
        # Extract labels like e:Person, e:Company etc.
        labels = set(re.findall(r"e:(\w+)", cypher))
        label_sets[qname] = labels

    base = label_sets["entity_by_id"]
    for qname in queries[1:]:
        assert label_sets[qname] == base, (
            f"Label allowlist mismatch between entity_by_id and {qname}: "
            f"missing={base - label_sets[qname]}, extra={label_sets[qname] - base}"
        )


def test_entity_by_id_has_all_id_fields() -> None:
    """entity_by_id.cypher must look up by all entity ID property fields."""
    cypher = _load_cypher("entity_by_id")
    for field in EXPECTED_ID_FIELDS:
        assert f"e.{field}" in cypher, (
            f"entity_by_id.cypher missing ID field lookup: e.{field}"
        )


@pytest.mark.anyio
async def test_entity_lookup_rejects_invalid_format(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entity/abc")
    assert response.status_code == 400
    assert "Invalid CPF or CNPJ" in response.json()["detail"]


@pytest.mark.anyio
async def test_entity_lookup_rejects_short_number(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entity/12345")
    assert response.status_code == 400


@pytest.mark.anyio
async def test_entity_lookup_rejects_15_digits(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entity/123456789012345")
    assert response.status_code == 400


@pytest.mark.anyio
async def test_connections_rejects_invalid_depth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entity/test-id/connections?depth=5")
    assert response.status_code == 422


@pytest.mark.anyio
async def test_connections_rejects_zero_depth(client: AsyncClient) -> None:
    response = await client.get("/api/v1/entity/test-id/connections?depth=0")
    assert response.status_code == 422


# ── entity_by_id: all 11 ID fields are present in WHERE clause ──────────


def test_entity_by_id_has_all_11_id_fields() -> None:
    """entity_by_id.cypher must resolve all 11 entity ID property fields."""
    cypher = _load_cypher("entity_by_id")
    all_fields = {
        "cpf", "cnpj", "contract_id", "sanction_id", "amendment_id",
        "cnes_code", "finance_id", "embargo_id", "school_id",
        "convenio_id", "stats_id",
    }
    for field in all_fields:
        assert f"e.{field}" in cypher, (
            f"entity_by_id.cypher missing ID field: e.{field}"
        )


# ── entity_by_element_id: PublicOffice label ────────────────────────────


def test_entity_by_element_id_has_public_office_label() -> None:
    """entity_by_element_id.cypher must include PublicOffice in label allowlist."""
    cypher = _load_cypher("entity_by_element_id")
    assert "e:PublicOffice" in cypher, (
        "entity_by_element_id.cypher missing PublicOffice label"
    )


def test_entity_by_element_id_has_all_labels() -> None:
    """entity_by_element_id.cypher must include all 13 entity labels."""
    cypher = _load_cypher("entity_by_element_id")
    for label in EXPECTED_LABELS:
        assert f"e:{label}" in cypher, (
            f"entity_by_element_id.cypher missing label: {label}"
        )


# ── Investigation coalesce chains: all 6 queries include all 11 ID fields ──


INVESTIGATION_COALESCE_QUERIES = [
    "investigation_get",
    "investigation_list",
    "investigation_update",
    "investigation_by_token",
    "investigation_add_entity",
]

ALL_ID_FIELDS = [
    "e.cpf", "e.cnpj", "e.contract_id", "e.sanction_id", "e.amendment_id",
    "e.cnes_code", "e.finance_id", "e.embargo_id", "e.school_id",
    "e.convenio_id", "e.stats_id",
]


@pytest.mark.parametrize("query_name", INVESTIGATION_COALESCE_QUERIES)
def test_investigation_coalesce_has_all_id_fields(query_name: str) -> None:
    """Every investigation coalesce chain must include all 11 entity ID fields."""
    cypher = _load_cypher(query_name)
    for field in ALL_ID_FIELDS:
        assert field in cypher, (
            f"{query_name}.cypher coalesce chain missing {field}"
        )


INVESTIGATION_WHERE_QUERIES = [
    "investigation_add_entity",
    "investigation_remove_entity",
]


@pytest.mark.parametrize("query_name", INVESTIGATION_WHERE_QUERIES)
def test_investigation_where_has_all_id_fields(query_name: str) -> None:
    """Investigation add/remove WHERE clauses must look up all 11 entity ID fields."""
    cypher = _load_cypher(query_name)
    for field in ALL_ID_FIELDS:
        assert field in cypher, (
            f"{query_name}.cypher WHERE clause missing {field}"
        )


# ── pattern_self_dealing: uses correct Amendment field names ─────────


def test_self_dealing_uses_value_committed_or_value_paid() -> None:
    """pattern_self_dealing.cypher must read value_committed/value_paid with a.value fallback."""
    try:
        cypher = _load_cypher("pattern_self_dealing")
    except FileNotFoundError:
        pytest.skip("pattern_self_dealing.cypher not available in this scope")
    # Must use coalesce with both TransfereGov fields AND Transparencia fallback
    assert "a.value_committed" in cypher, (
        "pattern_self_dealing.cypher missing a.value_committed (TransfereGov)"
    )
    assert "a.value_paid" in cypher, (
        "pattern_self_dealing.cypher missing a.value_paid (TransfereGov)"
    )
    # Transparencia Amendments use a.value and a.object — must be in coalesce fallback
    lines = cypher.splitlines()
    for line in lines:
        if "amendment_value" in line:
            assert "a.value" in line, (
                f"amendment_value line missing a.value fallback for Transparencia: {line.strip()}"
            )
        if "amendment_object" in line:
            assert "a.function" in line and "a.object" in line, (
                f"amendment_object line missing dual-source fallback: {line.strip()}"
            )
