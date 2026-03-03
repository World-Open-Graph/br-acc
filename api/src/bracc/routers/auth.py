from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from neo4j import AsyncSession
from neo4j.exceptions import ConstraintError
from starlette.requests import Request

from bracc.config import settings
from bracc.dependencies import CurrentUser, get_session
from bracc.middleware.rate_limit import limiter
from bracc.models.user import TokenResponse, UserCreate, UserResponse
from bracc.services import auth_service

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
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


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
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


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(settings.auth_cookie_name, path="/")
