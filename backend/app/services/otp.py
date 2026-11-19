from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import AppError
from app.core.security import hash_secret, new_otp
from app.models import OtpCode

OTP_MINUTES = 10
MAX_ATTEMPTS = 5
MAX_SENDS_PER_15_MIN = 3


async def create_otp(db: AsyncSession, email: str, purpose: str) -> str:
    """Creates a new code (older unused codes for the same purpose stop working)."""
    since = utcnow() - timedelta(minutes=15)
    recent = await db.scalar(
        select(func.count()).select_from(OtpCode).where(
            OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.created_at >= since
        )
    )
    if recent >= MAX_SENDS_PER_15_MIN:
        raise AppError("otp_too_many", 429)
    old = (await db.execute(
        select(OtpCode).where(OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.consumed_at.is_(None))
    )).scalars().all()
    for row in old:
        row.consumed_at = utcnow()
    code = new_otp()
    db.add(OtpCode(email=email, purpose=purpose, code_hash=hash_secret(f"{email}:{purpose}:{code}"),
                   expires_at=utcnow() + timedelta(minutes=OTP_MINUTES)))
    return code


async def check_otp(db: AsyncSession, email: str, purpose: str, code: str) -> None:
    """Raises AppError unless the code is right. Consumes it on success.
    Wrong attempts are committed by the caller's error path (see routers.auth)."""
    row = (await db.execute(
        select(OtpCode).where(OtpCode.email == email, OtpCode.purpose == purpose, OtpCode.consumed_at.is_(None))
        .order_by(OtpCode.id.desc()).limit(1)
    )).scalar_one_or_none()
    if row is None or row.expires_at < utcnow():
        raise AppError("otp_invalid")
    if row.attempts >= MAX_ATTEMPTS:
        raise AppError("otp_locked", 429)
    if row.code_hash != hash_secret(f"{email}:{purpose}:{code.strip()}"):
        row.attempts += 1
        await db.commit()
        raise AppError("otp_locked" if row.attempts >= MAX_ATTEMPTS else "otp_invalid", 429 if row.attempts >= MAX_ATTEMPTS else 400)
    row.consumed_at = utcnow()
