from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest

from bracc.config import settings
from bracc.services.auth_service import (
    authenticate_user,
    create_access_token,
    decode_access_token,
    hash_password,
    register_user,
    verify_password,
)


def _mock_record(data: dict[str, object]) -> MagicMock:
    record = MagicMock()
    record.__getitem__ = lambda self, key: data[key]
    return record


def test_hash_password_returns_bcrypt_hash() -> None:
    hashed = hash_password("mypassword")
    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


def test_verify_password_correct() -> None:
    hashed = hash_password("mypassword")
    assert verify_password("mypassword", hashed) is True


def test_verify_password_wrong() -> None:
    hashed = hash_password("mypassword")
    assert verify_password("wrongpassword", hashed) is False


def test_create_access_token_returns_string() -> None:
    token = create_access_token("user-123")
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_access_token_valid() -> None:
    token = create_access_token("user-123")
    user_id = decode_access_token(token)
    assert user_id == "user-123"


def test_decode_access_token_expired() -> None:
    expire = datetime.now(UTC) - timedelta(minutes=1)
    payload = {"sub": "user-123", "exp": expire}
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    assert decode_access_token(token) is None


def test_decode_access_token_invalid() -> None:
    assert decode_access_token("not-a-valid-token") is None


@pytest.mark.anyio
async def test_register_user_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "invite_code", "")

    mock_record = _mock_record({
        "id": "user-uuid",
        "email": "test@example.com",
        "created_at": "2026-01-01T00:00:00Z",
    })

    with patch(
        "bracc.services.auth_service.execute_query_single",
        new_callable=AsyncMock,
        return_value=mock_record,
    ):
        session = AsyncMock()
        user = await register_user(session, "test@example.com", "password123", "")
        assert user.email == "test@example.com"
        assert user.id == "user-uuid"


@pytest.mark.anyio
async def test_register_user_bad_invite(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "invite_code", "secret-code")
    session = AsyncMock()
    with pytest.raises(ValueError, match="Invalid invite code"):
        await register_user(session, "test@example.com", "password123", "wrong-code")


@pytest.mark.anyio
async def test_authenticate_user_success() -> None:
    hashed = hash_password("password123")
    mock_record = _mock_record({
        "id": "user-uuid",
        "email": "test@example.com",
        "password_hash": hashed,
        "created_at": "2026-01-01T00:00:00Z",
    })

    with patch(
        "bracc.services.auth_service.execute_query_single",
        new_callable=AsyncMock,
        return_value=mock_record,
    ):
        session = AsyncMock()
        user = await authenticate_user(session, "test@example.com", "password123")
        assert user is not None
        assert user.email == "test@example.com"


@pytest.mark.anyio
async def test_authenticate_user_wrong_password() -> None:
    hashed = hash_password("password123")
    mock_record = _mock_record({
        "id": "user-uuid",
        "email": "test@example.com",
        "password_hash": hashed,
        "created_at": "2026-01-01T00:00:00Z",
    })

    with patch(
        "bracc.services.auth_service.execute_query_single",
        new_callable=AsyncMock,
        return_value=mock_record,
    ):
        session = AsyncMock()
        user = await authenticate_user(session, "test@example.com", "wrongpassword")
        assert user is None


@pytest.mark.anyio
async def test_authenticate_user_not_found() -> None:
    with patch(
        "bracc.services.auth_service.execute_query_single",
        new_callable=AsyncMock,
        return_value=None,
    ):
        session = AsyncMock()
        user = await authenticate_user(session, "nobody@example.com", "password123")
        assert user is None
