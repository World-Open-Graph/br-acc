from typing import Annotated

from fastapi import APIRouter, Depends, Query
from neo4j import AsyncSession

from bracc.dependencies import get_session
from bracc.models.emendas import EmendaRecord, EmendasListResponse
from bracc.services.neo4j_service import execute_query, sanitize_props
from bracc.services.public_guard import sanitize_public_properties

router = APIRouter(prefix="/api/v1/emendas", tags=["emendas"])


@router.get("/", response_model=EmendasListResponse)
async def list_emendas_tesouro(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> EmendasListResponse:
    """List Tesouro Emendas payments with pagination."""
    count_records = await execute_query(
        session, "emendas_tesouro_count", {}
    )
    total_count = count_records[0]["total"] if count_records else 0

    records = await execute_query(
        session,
        "emendas_tesouro_list",
        {"skip": skip, "limit": limit},
    )

    results: list[EmendaRecord] = []
    for record in records:
        payment_props = sanitize_public_properties(
            sanitize_props(dict(record["p"]))
        )
        company_props = None
        if record["c"] is not None:
            company_props = sanitize_public_properties(
                sanitize_props(dict(record["c"]))
            )

        results.append(
            EmendaRecord(payment=payment_props, beneficiary=company_props)
        )

    return EmendasListResponse(
        data=results,
        total_count=total_count,
        skip=skip,
        limit=limit,
    )
