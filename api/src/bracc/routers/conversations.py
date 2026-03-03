"""Conversation persistence — Redis-backed chat history for EGOS Inteligência.

Allows users to:
- Create, list, and delete conversations
- Continue conversations across page reloads
- Each conversation stores full message history (30-day TTL)

Identity: anonymous client_id (UUID) stored in localStorage, sent via x-client-id header.
"""

import json
import logging
import time
import uuid
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from bracc.services.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])

_CONV_TTL = 30 * 24 * 3600  # 30 days
_MAX_CONVERSATIONS = 50  # per client
_MAX_MESSAGES = 100  # per conversation


def _get_client_id(request: Request) -> str:
    """Get client_id from header, or derive from IP."""
    client_id = (request.headers.get("x-client-id") or "").strip()
    if client_id and len(client_id) <= 64:
        return client_id
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return f"ip:{forwarded.split(',')[0].strip()}"
    return f"ip:{request.client.host}" if request.client else "ip:unknown"


def _conv_key(conv_id: str) -> str:
    return f"egos:conv:{conv_id}"


def _list_key(client_id: str) -> str:
    return f"egos:convlist:{client_id}"


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: float
    updated_at: float
    message_count: int


class ConversationDetail(BaseModel):
    id: str
    title: str
    created_at: float
    updated_at: float
    messages: list[dict[str, Any]] = []


class CreateConversationRequest(BaseModel):
    title: str = Field(default="Nova pesquisa", max_length=200)


@router.get("")
async def list_conversations(request: Request) -> dict[str, Any]:
    """List all conversations for the current client."""
    client_id = _get_client_id(request)
    redis = cache._client
    if not redis or not cache._available:
        return {"conversations": [], "client_id": client_id}

    try:
        # Get conversation IDs sorted by score (updated_at) desc
        conv_ids = await redis.zrevrange(_list_key(client_id), 0, _MAX_CONVERSATIONS - 1)
        conversations = []
        for conv_id in conv_ids:
            raw = await redis.get(_conv_key(conv_id))
            if not raw:
                # Stale reference, remove from list
                await redis.zrem(_list_key(client_id), conv_id)
                continue
            data = json.loads(raw)
            conversations.append(ConversationSummary(
                id=data["id"],
                title=data.get("title", "Sem título"),
                created_at=data.get("created_at", 0),
                updated_at=data.get("updated_at", 0),
                message_count=len(data.get("messages", [])),
            ))
        return {"conversations": [c.model_dump() for c in conversations], "client_id": client_id}
    except Exception as e:
        logger.warning("Failed to list conversations: %s", e)
        return {"conversations": [], "client_id": client_id}


@router.post("")
async def create_conversation(request: Request, body: CreateConversationRequest) -> ConversationDetail:
    """Create a new conversation."""
    client_id = _get_client_id(request)
    conv_id = str(uuid.uuid4())
    now = time.time()

    conv_data = {
        "id": conv_id,
        "client_id": client_id,
        "title": body.title,
        "created_at": now,
        "updated_at": now,
        "messages": [],
    }

    redis = cache._client
    if redis and cache._available:
        try:
            await redis.setex(_conv_key(conv_id), _CONV_TTL, json.dumps(conv_data, ensure_ascii=False))
            await redis.zadd(_list_key(client_id), {conv_id: now})
            await redis.expire(_list_key(client_id), _CONV_TTL)

            # Enforce max conversations limit
            count = await redis.zcard(_list_key(client_id))
            if count > _MAX_CONVERSATIONS:
                oldest = await redis.zrange(_list_key(client_id), 0, count - _MAX_CONVERSATIONS - 1)
                for old_id in oldest:
                    await redis.delete(_conv_key(old_id))
                    await redis.zrem(_list_key(client_id), old_id)
        except Exception as e:
            logger.warning("Failed to save conversation: %s", e)

    return ConversationDetail(**conv_data)


@router.get("/{conv_id}")
async def get_conversation(conv_id: str, request: Request) -> ConversationDetail:
    """Get a conversation with full message history."""
    client_id = _get_client_id(request)
    redis = cache._client
    if not redis or not cache._available:
        return ConversationDetail(id=conv_id, title="", created_at=0, updated_at=0)

    try:
        raw = await redis.get(_conv_key(conv_id))
        if not raw:
            return ConversationDetail(id=conv_id, title="Não encontrada", created_at=0, updated_at=0)
        data = json.loads(raw)
        # Security: verify client owns this conversation
        if data.get("client_id") != client_id:
            return ConversationDetail(id=conv_id, title="Acesso negado", created_at=0, updated_at=0)
        return ConversationDetail(**{k: v for k, v in data.items() if k != "client_id"})
    except Exception as e:
        logger.warning("Failed to get conversation: %s", e)
        return ConversationDetail(id=conv_id, title="Erro", created_at=0, updated_at=0)


@router.delete("/{conv_id}")
async def delete_conversation(conv_id: str, request: Request) -> dict[str, str]:
    """Delete a conversation."""
    client_id = _get_client_id(request)
    redis = cache._client
    if not redis or not cache._available:
        return {"status": "unavailable"}

    try:
        # Verify ownership before deleting
        raw = await redis.get(_conv_key(conv_id))
        if raw:
            data = json.loads(raw)
            if data.get("client_id") != client_id:
                return {"status": "forbidden"}
        await redis.delete(_conv_key(conv_id))
        await redis.zrem(_list_key(client_id), conv_id)
        return {"status": "deleted"}
    except Exception as e:
        logger.warning("Failed to delete conversation: %s", e)
        return {"status": "error"}


@router.patch("/{conv_id}/title")
async def update_title(conv_id: str, request: Request, body: CreateConversationRequest) -> dict[str, str]:
    """Update conversation title."""
    client_id = _get_client_id(request)
    redis = cache._client
    if not redis or not cache._available:
        return {"status": "unavailable"}

    try:
        raw = await redis.get(_conv_key(conv_id))
        if not raw:
            return {"status": "not_found"}
        data = json.loads(raw)
        if data.get("client_id") != client_id:
            return {"status": "forbidden"}
        data["title"] = body.title
        data["updated_at"] = time.time()
        await redis.setex(_conv_key(conv_id), _CONV_TTL, json.dumps(data, ensure_ascii=False))
        return {"status": "updated"}
    except Exception as e:
        logger.warning("Failed to update title: %s", e)
        return {"status": "error"}


# --- Helper used by chat.py ---

async def get_conversation_messages(conv_id: str, client_id: str) -> list[dict[str, str]]:
    """Get messages for a conversation (used by chat endpoint)."""
    redis = cache._client
    if not redis or not cache._available:
        return []
    try:
        raw = await redis.get(_conv_key(conv_id))
        if not raw:
            return []
        data = json.loads(raw)
        if data.get("client_id") != client_id:
            return []
        return data.get("messages", [])
    except Exception:
        return []


async def save_conversation_messages(
    conv_id: str,
    client_id: str,
    user_msg: str,
    assistant_msg: str,
    auto_title: bool = False,
) -> None:
    """Append user+assistant messages to a conversation."""
    redis = cache._client
    if not redis or not cache._available:
        return
    try:
        raw = await redis.get(_conv_key(conv_id))
        now = time.time()
        if raw:
            data = json.loads(raw)
            if data.get("client_id") != client_id:
                return
        else:
            # Auto-create conversation if it doesn't exist
            data = {
                "id": conv_id,
                "client_id": client_id,
                "title": user_msg[:60] + ("..." if len(user_msg) > 60 else ""),
                "created_at": now,
                "updated_at": now,
                "messages": [],
            }
            await redis.zadd(_list_key(client_id), {conv_id: now})
            await redis.expire(_list_key(client_id), _CONV_TTL)

        data["messages"].append({"role": "user", "content": user_msg})
        data["messages"].append({"role": "assistant", "content": assistant_msg})
        data["updated_at"] = now

        # Auto-title from first user message
        if auto_title and len(data["messages"]) <= 2:
            data["title"] = user_msg[:60] + ("..." if len(user_msg) > 60 else "")

        # Trim to max messages
        if len(data["messages"]) > _MAX_MESSAGES:
            data["messages"] = data["messages"][-_MAX_MESSAGES:]

        await redis.setex(_conv_key(conv_id), _CONV_TTL, json.dumps(data, ensure_ascii=False))
        # Update sorted set score
        await redis.zadd(_list_key(client_id), {conv_id: now})
    except Exception as e:
        logger.warning("Failed to save messages: %s", e)
