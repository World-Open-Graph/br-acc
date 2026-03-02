from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.requests import Request

from bracc.config import settings
from bracc.services.auth_service import decode_access_token


def _get_rate_limit_key(request: Request) -> str:
    """Extract user_id from JWT (Bearer or cookie) for rate limiting, fallback to IP."""
    auth = request.headers.get("authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        user_id = decode_access_token(token)
        if user_id:
            return f"user:{user_id}"
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if isinstance(cookie_token, str) and cookie_token.strip():
        user_id = decode_access_token(cookie_token.strip())
        if user_id:
            return f"user:{user_id}"
    return get_remote_address(request)


limiter = Limiter(
    key_func=_get_rate_limit_key,
    default_limits=[settings.rate_limit_anon],
)
