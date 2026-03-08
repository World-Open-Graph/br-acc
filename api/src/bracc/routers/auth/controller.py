from typing import Annotated

from fastapi import Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from neo4j import AsyncSession
from neo4j.exceptions import ConstraintError

from bracc.config import settings
from bracc.models.user import TokenResponse, UserCreate, UserResponse
from bracc.services import auth_service


async def register(
    body: UserCreate,
    session: AsyncSession,
) -> UserResponse:
    try:
        return await auth_service.register_user(
            session, body.email, body.password, body.invite_code
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Invalid invite code"
        ) from exc
    except ConstraintError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Email already registered"
        ) from exc


async def login(
    response: Response,
    form: OAuth2PasswordRequestForm,
    session: AsyncSession,
) -> TokenResponse:
    user = await auth_service.authenticate_user(session, form.username, form.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = auth_service.create_access_token(user.id)
    effective_secure = settings.auth_cookie_secure or (
        settings.app_env.strip().lower() == "prod"
    )
    response.set_cookie(
        key=settings.auth_cookie_name,
        value=token,
        max_age=settings.jwt_expire_minutes * 60,
        httponly=True,
        secure=effective_secure,
        samesite=settings.auth_cookie_samesite,
        path="/",
    )
    return TokenResponse(access_token=token)


