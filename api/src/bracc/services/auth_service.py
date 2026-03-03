import hmac
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import jwt
from neo4j import AsyncSession

from bracc.config import settings
from bracc.models.user import UserResponse
from bracc.services.neo4j_service import execute_query_single

ALLOWED_JWT_ALGORITHMS = ["HS256"]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_access_token(user_id: str) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": user_id, "exp": expire}
    algo = settings.jwt_algorithm if settings.jwt_algorithm in ALLOWED_JWT_ALGORITHMS else "HS256"
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=algo)


def decode_access_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=ALLOWED_JWT_ALGORITHMS)
        user_id: str | None = payload.get("sub")
        return user_id
    except jwt.PyJWTError:
        return None


async def register_user(
    session: AsyncSession,
    email: str,
    password: str,
    invite_code: str,
) -> UserResponse:
    if settings.invite_code and not hmac.compare_digest(
        str(invite_code), str(settings.invite_code)
    ):
        msg = "Invalid invite code"
        raise ValueError(msg)

    password_hash = hash_password(password)
    record = await execute_query_single(
        session,
        "user_create",
        {"id": str(uuid.uuid4()), "email": email, "password_hash": password_hash},
    )
    if record is None:
        msg = "Failed to create user"
        raise RuntimeError(msg)
    return UserResponse(id=record["id"], email=record["email"], created_at=record["created_at"])


async def authenticate_user(
    session: AsyncSession,
    email: str,
    password: str,
) -> UserResponse | None:
    record = await execute_query_single(session, "user_get_by_email", {"email": email})
    if record is None:
        return None
    if not verify_password(password, record["password_hash"]):
        return None
    return UserResponse(id=record["id"], email=record["email"], created_at=record["created_at"])


async def get_user_by_id(
    session: AsyncSession,
    user_id: str,
) -> UserResponse | None:
    record = await execute_query_single(session, "user_get_by_id", {"id": user_id})
    if record is None:
        return None
    return UserResponse(id=record["id"], email=record["email"], created_at=record["created_at"])
