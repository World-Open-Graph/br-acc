"""Types and contracts for the emendas module."""

from enum import StrEnum
from typing import Any, TypedDict

from bracc.models.emendas import EmendaRecord, EmendasListResponse


class EmendasQueryName(StrEnum):
    """Cypher query names used by the emendas endpoint."""

    TESOURO_COUNT = "emendas_tesouro_count"
    TESOURO_LIST = "emendas_tesouro_list"


class EmendasRecordKey(StrEnum):
    """Expected keys in Neo4j record payloads."""

    TOTAL = "total"
    PAYMENT = "p"
    BENEFICIARY = "c"


class EmendasCountRow(TypedDict):
    """Shape of each row returned by the count query."""

    total: int


class EmendasListRow(TypedDict):
    """Shape of each row returned by the list query."""

    p: dict[str, Any]
    c: dict[str, Any] | None


__all__ = [
    "EmendaRecord",
    "EmendasListResponse",
    "EmendasCountRow",
    "EmendasListRow",
    "EmendasQueryName",
    "EmendasRecordKey"
]
