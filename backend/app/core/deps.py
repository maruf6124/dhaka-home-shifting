from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.errors import AppError
from app.core.security import decode_token
from app.models import User

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
DEVICE_COOKIE = "device_token"


def _token_from_request(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(ACCESS_COOKIE)


async def get_optional_user(request: Request, db: AsyncSession = Depends(get_db)) -> User | None:
    token = _token_from_request(request)
    if not token:
        return None
    user_id = decode_token(token, "access")
    if user_id is None:
        return None
    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.is_banned:
        return None
    return user


async def get_current_user(request: Request, db: AsyncSession = Depends(get_db)) -> User:
    token = _token_from_request(request)
    user_id = decode_token(token, "access") if token else None
    if user_id is None:
        raise AppError("not_authenticated", 401)
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise AppError("not_authenticated", 401)
    if user.is_banned:
        raise AppError("banned", 403)
    return user


async def get_verified_user(user: User = Depends(get_current_user)) -> User:
    if user.email_verified_at is None:
        raise AppError("email_not_verified", 403)
    return user


def has_verified_role(user: User, role: str) -> bool:
    return any(r.role == role and r.kyc_status == "verified" for r in user.roles)


def is_admin(user: User) -> bool:
    return any(r.role == "admin" for r in user.roles)


async def get_admin(user: User = Depends(get_current_user)) -> User:
    if not is_admin(user):
        raise AppError("forbidden", 403)
    return user
