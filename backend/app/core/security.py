import hashlib
import hmac
import secrets
from datetime import timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings
from app.core.database import utcnow

settings = get_settings()
_ph = PasswordHasher()


def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def create_token(user_id: int, kind: str) -> str:
    """kind = 'access' | 'refresh'"""
    lifetime = (
        timedelta(minutes=settings.access_token_minutes)
        if kind == "access"
        else timedelta(days=settings.refresh_token_days)
    )
    now = utcnow()
    payload = {"sub": str(user_id), "type": kind, "iat": now, "exp": now + lifetime}
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, kind: str) -> int | None:
    try:
        data = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    if data.get("type") != kind:
        return None
    try:
        return int(data["sub"])
    except (KeyError, ValueError):
        return None


def new_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def hash_secret(value: str) -> str:
    """Keyed hash for OTPs and device tokens (never stored in plain text)."""
    return hmac.new(settings.otp_pepper.encode(), value.encode(), hashlib.sha256).hexdigest()


def new_device_token() -> str:
    return secrets.token_urlsafe(32)
