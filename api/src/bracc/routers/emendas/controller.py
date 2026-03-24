"""Orchestration layer for the emendas endpoint."""

from typing import cast

from neo4j import AsyncSession

from bracc.services.neo4j_service import execute_query, sanitize_props
from bracc.services.public_guard import sanitize_public_properties

from .model import (
    EmendaRecord,
    EmendasCountRow,
    EmendasListResponse,
    EmendasListRow,
    EmendasQueryName,
    EmendasRecordKey,
)


async def list_emendas_tesouro(
    session: AsyncSession,
    skip: int,
    limit: int,
) -> EmendasListResponse:
    """List Tesouro emendas payments with pagination."""

    count_records = cast(
        "list[EmendasCountRow]",
        await execute_query(session, EmendasQueryName.TESOURO_COUNT, {}),
    )
    total_count = (
        count_records[0][EmendasRecordKey.TOTAL.value]
        if count_records
        else 0
    )

    records = cast(
        "list[EmendasListRow]",
        await execute_query(
            session,
            EmendasQueryName.TESOURO_LIST,
            {"skip": skip, "limit": limit},
        ),
    )

    results: list[EmendaRecord] = []
    for record in records:
        payment_props = sanitize_public_properties(
            sanitize_props(
                dict(record[EmendasRecordKey.PAYMENT.value])
            )
        )
        company_props = None
        beneficiary_raw = record[EmendasRecordKey.BENEFICIARY.value]

        if beneficiary_raw is not None:
            company_props = sanitize_public_properties(
                sanitize_props(dict(beneficiary_raw))
            )

        results.append(EmendaRecord(payment=payment_props, beneficiary=company_props))

    return EmendasListResponse(
        data=results,
        total_count=total_count,
        skip=skip,
        limit=limit,
    )
