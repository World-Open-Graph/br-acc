from unittest.mock import MagicMock

from bracc.middleware.rate_limit import _get_rate_limit_key, limiter
from bracc.services.auth_service import create_access_token


def _make_request(auth_header: str | None = None, client_ip: str = "127.0.0.1") -> MagicMock:
    request = MagicMock()
    headers: dict[str, str] = {}
    if auth_header:
        headers["authorization"] = auth_header
    request.headers = headers
    request.client = MagicMock()
    request.client.host = client_ip
    return request


def test_key_func_extracts_user_from_jwt() -> None:
    token = create_access_token("user-123")
    request = _make_request(auth_header=f"Bearer {token}")
    key = _get_rate_limit_key(request)
    assert key == "user:user-123"


def test_key_func_fallback_to_ip() -> None:
    request = _make_request(client_ip="192.168.1.1")
    key = _get_rate_limit_key(request)
    assert key == "192.168.1.1"


def test_key_func_invalid_token_fallback() -> None:
    request = _make_request(auth_header="Bearer invalid-token", client_ip="10.0.0.1")
    key = _get_rate_limit_key(request)
    assert key == "10.0.0.1"


def test_limiter_instance_exists() -> None:
    assert limiter is not None
