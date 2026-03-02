"""Activity Feed — Mycelium-inspired event trail for EGOS Inteligência."""
import json
import time
from collections import deque
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1/activity", tags=["activity"])

# In-memory activity store (last 500 events) — Redis upgrade later
_ACTIVITY_LOG: deque[dict[str, Any]] = deque(maxlen=500)


class ActivityItem(BaseModel):
    id: str
    type: str  # search, chat, report, entity_view, tool_call
    title: str
    description: str = ""
    source: str = ""  # which tool/api was used
    result_count: int = 0
    cost_usd: float = 0.0
    timestamp: str = ""
    client_ip: str = ""


def log_activity(
    activity_type: str,
    title: str,
    description: str = "",
    source: str = "",
    result_count: int = 0,
    cost_usd: float = 0.0,
    client_ip: str = "",
) -> None:
    """Log an activity event to the in-memory store."""
    event = {
        "id": f"evt-{int(time.time() * 1000)}",
        "type": activity_type,
        "title": title,
        "description": description,
        "source": source,
        "result_count": result_count,
        "cost_usd": cost_usd,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "client_ip": client_ip,
    }
    _ACTIVITY_LOG.appendleft(event)


@router.get("/feed")
async def get_activity_feed(
    request: Request,
    limit: int = 50,
    type: str = "",
) -> dict[str, Any]:
    """Get recent activity feed."""
    items = list(_ACTIVITY_LOG)
    if type:
        items = [i for i in items if i["type"] == type]
    items = items[:min(limit, 100)]

    # Aggregate stats
    total = len(_ACTIVITY_LOG)
    types = {}
    total_cost = 0.0
    for item in _ACTIVITY_LOG:
        t = item.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
        total_cost += item.get("cost_usd", 0.0)

    return {
        "items": items,
        "stats": {
            "total_events": total,
            "by_type": types,
            "total_cost_usd": round(total_cost, 6),
        },
    }


@router.get("/stats")
async def get_activity_stats() -> dict[str, Any]:
    """Get aggregated activity statistics."""
    total = len(_ACTIVITY_LOG)
    types = {}
    sources = {}
    total_cost = 0.0
    total_results = 0

    for item in _ACTIVITY_LOG:
        t = item.get("type", "unknown")
        types[t] = types.get(t, 0) + 1
        s = item.get("source", "unknown")
        sources[s] = sources.get(s, 0) + 1
        total_cost += item.get("cost_usd", 0.0)
        total_results += item.get("result_count", 0)

    return {
        "total_events": total,
        "by_type": types,
        "by_source": sources,
        "total_cost_usd": round(total_cost, 6),
        "total_results": total_results,
        "avg_cost_per_query": round(total_cost / max(total, 1), 6),
    }
