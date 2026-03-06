from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query
from neo4j import AsyncSession

from bracc.dependencies import get_session
from bracc.services.neo4j_service import execute_query, sanitize_props
from bracc.services.public_guard import sanitize_public_properties

router = APIRouter(prefix="/api/v1/emendas", tags=["emendas"])

@router.get("/")
async def list_emendas_tesouro(
    session: Annotated[AsyncSession, Depends(get_session)],
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> dict[str, Any]:
    """List Tesouro Emendas payments."""
    records = await execute_query(
        session,
        "emendas_tesouro_list",
        {"skip": skip, "limit": limit},
    )

    results = []
    for record in records:
        payment_props = sanitize_public_properties(sanitize_props(dict(record["p"])))
        company_props = None
        if record["c"] is not None:
            company_props = sanitize_public_properties(sanitize_props(dict(record["c"])))
        
        results.append({
            "payment": payment_props,
            "beneficiary": company_props,
        })

    return {
        "data": results,
        "skip": skip,
        "limit": limit,
        "total_returned": len(results)
    }
