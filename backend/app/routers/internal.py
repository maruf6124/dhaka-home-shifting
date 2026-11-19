"""Scheduled jobs. Render's free plan has no cron, so a GitHub Actions workflow
calls this endpoint every hour with the secret header. Every job is safe to
run twice."""
import hmac
from datetime import timedelta

from fastapi import APIRouter, Depends, Header
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.database import get_db, utcnow
from app.core.errors import AppError
from app.models import KycDocument, OtpCode, RentListing
from app.services.storage import delete_private_document

router = APIRouter(prefix="/internal", tags=["internal"], include_in_schema=False)
settings = get_settings()


@router.post("/run-jobs")
async def run_jobs(x_job_secret: str = Header(default=""), db: AsyncSession = Depends(get_db)):
    if not hmac.compare_digest(x_job_secret, settings.job_secret):
        raise AppError("forbidden", 403)
    now = utcnow()
    expired = (await db.execute(
        update(RentListing).where(RentListing.status == "active", RentListing.expires_at < now).values(status="expired")
    )).rowcount
    otps = (await db.execute(delete(OtpCode).where(OtpCode.created_at < now - timedelta(days=1)))).rowcount
    docs = (await db.execute(select(KycDocument).where(
        KycDocument.delete_after.is_not(None), KycDocument.delete_after < now, KycDocument.status != "deleted"))).scalars().all()
    for d in docs:
        delete_private_document(d.storage_key)
        d.status, d.storage_key = "deleted", "deleted"
    await db.commit()
    return {"expired_listings": expired, "old_otps": otps, "deleted_documents": len(docs)}
