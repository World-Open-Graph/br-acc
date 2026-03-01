from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from bracc.config import settings
from bracc.services.auth_service import decode_access_token


def _extract_token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:].strip()
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if isinstance(cookie_token, str) and cookie_token.strip():
        return cookie_token.strip()
    return None


def _resolve_client_ip(request: Request) -> str:
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        if forwarded:
            first_hop = forwarded.split(",", 1)[0].strip()
            if first_hop:
                return first_hop
        real_ip = request.headers.get("x-real-ip", "").strip()
        if real_ip:
            return real_ip
    return get_remote_address(request)


def _get_rate_limit_key(request: Request) -> str:
    """Extract user_id from JWT for rate limiting, fallback to IP."""
    token = _extract_token(request)
    if token:
        user_id = decode_access_token(token)
        if user_id:
            return f"user:{user_id}"
    return _resolve_client_ip(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[settings.rate_limit_anon],
)
