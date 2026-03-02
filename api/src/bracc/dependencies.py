from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from neo4j import AsyncDriver, AsyncGraphDatabase, AsyncSession

from bracc.config import settings
from bracc.models.user import UserResponse
from bracc.services import auth_service
from bracc.services.intelligence_provider import IntelligenceProvider, get_default_provider

_driver: AsyncDriver | None = None

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


async def init_driver() -> AsyncDriver:
    global _driver
    _driver = AsyncGraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
        max_connection_pool_size=50,
        connection_acquisition_timeout=10,
    )
    await _driver.verify_connectivity()
    return _driver


async def close_driver() -> None:
    global _driver
    if _driver is not None:
        await _driver.close()
        _driver = None


async def get_driver(request: Request) -> AsyncDriver:
    driver: AsyncDriver | None = getattr(request.app.state, "neo4j_driver", None)
    if driver is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection not available",
        )
    return driver


async def get_session(
    driver: Annotated[AsyncDriver, Depends(get_driver)],
) -> AsyncGenerator[AsyncSession]:
    async with driver.session(database=settings.neo4j_database) as session:
        yield session


def get_intelligence_provider() -> IntelligenceProvider:
    return get_default_provider()


def _resolve_token(token: str | None, request: Request) -> str | None:
    if token:
        return token
    cookie_token = request.cookies.get(settings.auth_cookie_name)
    if isinstance(cookie_token, str) and cookie_token.strip():
        return cookie_token.strip()
    return None


async def get_current_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    resolved_token = _resolve_token(token, request)
    if resolved_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    user_id = auth_service.decode_access_token(resolved_token)
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    user = await auth_service.get_user_by_id(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


async def get_optional_user(
    request: Request,
    token: Annotated[str | None, Depends(oauth2_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse | None:
    resolved_token = _resolve_token(token, request)
    if resolved_token is None:
        return None
    user_id = auth_service.decode_access_token(resolved_token)
    if user_id is None:
        return None
    return await auth_service.get_user_by_id(session, user_id)


CurrentUser = Annotated[UserResponse, Depends(get_current_user)]
