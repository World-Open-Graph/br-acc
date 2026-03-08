from typing import Annotated

from fastapi import APIRouter, Depends, Response
from fastapi.security import OAuth2PasswordRequestForm
from neo4j import AsyncSession
from starlette.requests import Request

from bracc.dependencies import CurrentUser, get_session
from bracc.middleware.rate_limit import limiter
from bracc.config import settings

from . import controller
from .model import TokenResponse, UserCreate, UserResponse

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit("10/minute")
async def register(
    request: Request,
    body: UserCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> UserResponse:
    return await controller.register(body, session)


@router.post("/login", response_model=TokenResponse)
@limiter.limit("10/minute")
async def login(
    request: Request,
    response: Response,
    form: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> TokenResponse:
    return await controller.login(response, form, session)


@router.get("/me", response_model=UserResponse)
async def me(user: CurrentUser) -> UserResponse:
    return user


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    response.delete_cookie(settings.auth_cookie_name, path="/")

