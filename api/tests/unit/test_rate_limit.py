from unittest.mock import MagicMock

from bracc.config import settings
from bracc.middleware.rate_limit import _get_rate_limit_key, limiter
from bracc.services.auth_service import create_access_token


def _make_request(
    auth_header: str | None = None,
    client_ip: str = "127.0.0.1",
    cookie_token: str | None = None,
    x_forwarded_for: str | None = None,
) -> MagicMock:
    request = MagicMock()
    headers: dict[str, str] = {}
    if auth_header:
        headers["authorization"] = auth_header
    if x_forwarded_for:
        headers["x-forwarded-for"] = x_forwarded_for
    request.headers = headers
    request.cookies = {settings.auth_cookie_name: cookie_token} if cookie_token else {}
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


def test_key_func_extracts_user_from_cookie_token() -> None:
    token = create_access_token("cookie-user-1")
    request = _make_request(cookie_token=token)
    key = _get_rate_limit_key(request)
    assert key == "user:cookie-user-1"


def test_key_func_uses_forwarded_ip_when_enabled() -> None:
    original = settings.trust_proxy_headers
    try:
        settings.trust_proxy_headers = True
        request = _make_request(client_ip="127.0.0.1", x_forwarded_for="203.0.113.9, 10.0.0.4")
        key = _get_rate_limit_key(request)
        assert key == "203.0.113.9"
    finally:
        settings.trust_proxy_headers = original


def test_limiter_instance_exists() -> None:
    assert limiter is not None
