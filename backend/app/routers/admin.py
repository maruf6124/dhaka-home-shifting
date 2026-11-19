"""Admin panel API. Every change is written to admin_audit_logs."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.deps import get_admin
from app.core.errors import AppError
from app.models import (
    AdminAuditLog, DiamondTransaction, FreeDiamondRequest, KycDocument, PaymentRequest, RentListing, Report,
    Unlock, User, UserRole,
)
from app.schemas import BonusApproveIn, GiftIn, ReviewDecisionIn, SettingsIn, normalize_phone
from app.services.listings import get_listing, link_for
from app.services.notify import notify
from app.services.refunds import refund_unlock
from app.services.settings_store import DEFAULTS, get_all, get_setting, set_setting
from app.services.storage import local_private_path, private_document_url
from app.services.wallet import balance, credit

router = APIRouter(prefix="/admin", tags=["admin"])


def audit(db: AsyncSession, admin: User, action: str, target_type: str | None = None, target_id: int | None = None, **details):
    db.add(AdminAuditLog(admin_id=admin.id, action=action, target_type=target_type, target_id=target_id, details=details))


# ---------------------------------------------------------------- dashboard
@router.get("/stats")
async def stats(admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    now = utcnow()
    count = lambda q: db.scalar(select(func.count()).select_from(q.subquery()))  # noqa: E731
    days = []
    for i in range(13, -1, -1):
        start = (now - timedelta(days=i)).replace(hour=0, minute=0, second=0, microsecond=0)
        sold = await db.scalar(select(func.coalesce(func.sum(DiamondTransaction.amount), 0)).where(
            DiamondTransaction.kind == "purchase", DiamondTransaction.created_at >= start,
            DiamondTransaction.created_at < start + timedelta(days=1)))
        days.append({"date": start.date().isoformat(), "diamonds": int(sold or 0)})
    revenue_30 = await db.scalar(select(func.coalesce(func.sum(PaymentRequest.amount_bdt), 0)).where(
        PaymentRequest.status == "approved", PaymentRequest.reviewed_at >= now - timedelta(days=30)))
    return {
        "users": await count(select(User.id)),
        "verified_providers": await count(select(UserRole.id).where(UserRole.role.in_(["landlord", "driver", "cleaner"]), UserRole.kyc_status == "verified")),
        "active_listings": await count(select(RentListing.id).where(RentListing.status == "active", RentListing.expires_at > now)),
        "pending_kyc": await count(select(UserRole.id).where(UserRole.kyc_status == "pending")),
        "pending_payments": await count(select(PaymentRequest.id).where(PaymentRequest.status == "pending")),
        "pending_free": await count(select(FreeDiamondRequest.id).where(FreeDiamondRequest.status == "pending")),
        "open_reports": await count(select(Report.listing_id).where(Report.status == "open").group_by(Report.listing_type, Report.listing_id)),
        "revenue_30d": int(revenue_30 or 0),
        "diamonds_by_day": days,
    }


# ---------------------------------------------------------------- KYC
@router.get("/kyc")
async def kyc_queue(status: str = Query(default="pending", pattern="^(pending|verified|rejected)$"),
                    admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(UserRole, User).join(User, User.id == UserRole.user_id)
        .where(UserRole.kyc_status == status, UserRole.role.in_(["landlord", "driver", "cleaner"]))
        .order_by(UserRole.updated_at.asc())
    )).all()
    out = []
    for role, user in rows:
        docs = (await db.execute(select(KycDocument).where(
            KycDocument.user_id == user.id, KycDocument.role == role.role, KycDocument.status.in_(["pending", "approved"])))).scalars().all()
        out.append({
            "user": {"id": user.id, "name": user.name, "email": user.email, "phone": user.phone},
            "role": role.role, "status": role.kyc_status, "note": role.review_note, "submitted_at": role.updated_at.isoformat(),
            "documents": [{"id": d.id, "doc_type": d.doc_type, "content_type": d.content_type} for d in docs],
        })
    return out


@router.get("/kyc/documents/{doc_id}/url")
async def kyc_document_url(doc_id: int, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    doc = await db.get(KycDocument, doc_id)
    if doc is None:
        raise AppError("not_found", 404)
    audit(db, admin, "kyc_document_viewed", "kyc_document", doc.id, user_id=doc.user_id)
    await db.commit()
    return {"url": private_document_url(doc.storage_key, doc.id), "content_type": doc.content_type}


@router.get("/kyc/documents/{doc_id}/file")
async def kyc_document_file(doc_id: int, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    """Local-storage mode only (development)."""
    doc = await db.get(KycDocument, doc_id)
    path = local_private_path(doc.storage_key) if doc else None
    if path is None or not path.exists():
        raise AppError("not_found", 404)
    return FileResponse(path, media_type=doc.content_type, headers={"Cache-Control": "no-store"})


async def _decide_kyc(db: AsyncSession, admin: User, user_id: int, role: str, approve: bool, note: str | None):
    row = (await db.execute(select(UserRole).where(UserRole.user_id == user_id, UserRole.role == role))).scalar_one_or_none()
    if row is None or row.kyc_status != "pending":
        raise AppError("not_found", 404)
    row.kyc_status = "verified" if approve else "rejected"
    row.review_note = note
    docs = (await db.execute(select(KycDocument).where(
        KycDocument.user_id == user_id, KycDocument.role == role, KycDocument.status == "pending"))).scalars().all()
    for d in docs:
        d.status = "approved" if approve else "rejected"
        if not approve:
            d.delete_after = utcnow() + timedelta(days=30)
    await notify(db, user_id, "kyc_approved" if approve else "kyc_rejected", note or role, "/become-provider")
    audit(db, admin, "kyc_approved" if approve else "kyc_rejected", "user", user_id, role=role, note=note)
    await db.commit()
    return {"status": row.kyc_status}


@router.post("/kyc/{user_id}/{role}/approve")
async def kyc_approve(user_id: int, role: str, data: ReviewDecisionIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    return await _decide_kyc(db, admin, user_id, role, True, data.note)


@router.post("/kyc/{user_id}/{role}/reject")
async def kyc_reject(user_id: int, role: str, data: ReviewDecisionIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    return await _decide_kyc(db, admin, user_id, role, False, data.note)


# ---------------------------------------------------------------- payments & bonus
@router.get("/payments")
async def payments(status: str = Query(default="pending", pattern="^(pending|approved|rejected)$"),
                   admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PaymentRequest).where(PaymentRequest.status == status).order_by(PaymentRequest.id.desc()).limit(200))).scalars().all()
    return [{
        "id": p.id, "user": {"id": p.user.id, "name": p.user.name, "email": p.user.email},
        "method": p.method, "package_key": p.package_key, "diamonds": p.diamonds, "amount_bdt": p.amount_bdt,
        "trx_id": p.trx_id, "sender_number": p.sender_number, "status": p.status, "created_at": p.created_at.isoformat(),
    } for p in rows]


@router.post("/payments/{payment_id}/approve")
async def payment_approve(payment_id: int, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    p = (await db.execute(select(PaymentRequest).where(PaymentRequest.id == payment_id).with_for_update())).scalar_one_or_none()
    if p is None or p.status != "pending":
        raise AppError("not_found", 404)
    p.status, p.reviewed_by, p.reviewed_at = "approved", admin.id, utcnow()
    await credit(db, p.user_id, paid=p.diamonds, kind="purchase", ref_type="payment", ref_id=p.id, note=p.trx_id)
    await notify(db, p.user_id, "topup_approved", f"+{p.diamonds}", "/wallet")
    audit(db, admin, "payment_approved", "payment", p.id, trx_id=p.trx_id, diamonds=p.diamonds)
    await db.commit()
    return {"status": "approved"}


@router.post("/payments/{payment_id}/reject")
async def payment_reject(payment_id: int, data: ReviewDecisionIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    p = await db.get(PaymentRequest, payment_id)
    if p is None or p.status != "pending":
        raise AppError("not_found", 404)
    p.status, p.reviewed_by, p.reviewed_at = "rejected", admin.id, utcnow()
    await notify(db, p.user_id, "topup_rejected", data.note or p.trx_id, "/wallet")
    audit(db, admin, "payment_rejected", "payment", p.id, trx_id=p.trx_id, note=data.note)
    await db.commit()
    return {"status": "rejected"}


@router.get("/free-requests")
async def free_requests(admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(FreeDiamondRequest).where(FreeDiamondRequest.status == "pending").order_by(FreeDiamondRequest.id))).scalars().all()
    out = []
    for r in rows:
        paid, bonus = await balance(db, r.user_id)
        last_ok = await db.scalar(select(func.max(FreeDiamondRequest.created_at)).where(
            FreeDiamondRequest.user_id == r.user_id, FreeDiamondRequest.status == "approved"))
        out.append({"id": r.id, "user": {"id": r.user.id, "name": r.user.name, "email": r.user.email}, "reason": r.reason,
                    "balance": paid + bonus, "last_approved_at": last_ok.isoformat() if last_ok else None,
                    "created_at": r.created_at.isoformat()})
    return {"max_amount": await get_setting(db, "free_bonus_max"), "items": out}


@router.post("/free-requests/{req_id}/approve")
async def free_approve(req_id: int, data: BonusApproveIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    r = await db.get(FreeDiamondRequest, req_id)
    if r is None or r.status != "pending":
        raise AppError("not_found", 404)
    max_amount = int(await get_setting(db, "free_bonus_max"))
    amount = min(data.amount, max_amount)
    r.status, r.approved_amount, r.reviewed_by = "approved", amount, admin.id
    await credit(db, r.user_id, bonus=amount, kind="bonus", ref_type="free_request", ref_id=r.id, note="free bonus")
    await notify(db, r.user_id, "bonus_approved", f"+{amount}", "/wallet")
    audit(db, admin, "free_bonus_approved", "free_request", r.id, amount=amount)
    await db.commit()
    return {"status": "approved", "amount": amount}


@router.post("/free-requests/{req_id}/reject")
async def free_reject(req_id: int, data: ReviewDecisionIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    r = await db.get(FreeDiamondRequest, req_id)
    if r is None or r.status != "pending":
        raise AppError("not_found", 404)
    r.status, r.reviewed_by = "rejected", admin.id
    await notify(db, r.user_id, "bonus_rejected", data.note or "", "/wallet")
    audit(db, admin, "free_bonus_rejected", "free_request", r.id, note=data.note)
    await db.commit()
    return {"status": "rejected"}


@router.post("/gift")
async def gift(data: GiftIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    target = data.user.strip().lower()
    cond = [User.email == target]
    try:
        cond.append(User.phone == normalize_phone(target))
    except ValueError:
        pass
    user = (await db.execute(select(User).where(or_(*cond)))).scalar_one_or_none()
    if user is None:
        raise AppError("not_found", 404)
    await credit(db, user.id, bonus=data.amount, kind="gift", note=data.reason)
    await notify(db, user, "gift", f"+{data.amount}: {data.reason}", "/wallet")
    audit(db, admin, "gift", "user", user.id, amount=data.amount, reason=data.reason)
    await db.commit()
    return {"status": "ok", "user_id": user.id}


# ---------------------------------------------------------------- reports
@router.get("/reports")
async def reports(admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Report).where(Report.status == "open").order_by(Report.created_at))).scalars().all()
    grouped: dict[tuple[str, int], list[Report]] = {}
    for r in rows:
        grouped.setdefault((r.listing_type, r.listing_id), []).append(r)
    out = []
    for (ltype, lid), reps in grouped.items():
        listing = await get_listing(db, ltype, lid)
        owner = await db.get(User, listing.owner_id)
        unlockers = await db.scalar(select(func.count()).select_from(Unlock).where(
            Unlock.listing_type == ltype, Unlock.listing_id == lid, Unlock.refunded.is_(False)))
        out.append({
            "listing_type": ltype, "listing_id": lid, "title": listing.title, "status": listing.status,
            "link": link_for(ltype, lid), "owner": {"id": owner.id, "name": owner.name, "warnings": owner.warnings},
            "unlockers": unlockers,
            "reports": [{"id": r.id, "reason": r.reason, "note": r.note, "created_at": r.created_at.isoformat()} for r in reps],
        })
    out.sort(key=lambda x: len(x["reports"]), reverse=True)
    return out


@router.post("/reports/{listing_type}/{listing_id}/confirm")
async def confirm_report(listing_type: str, listing_id: int, data: ReviewDecisionIn,
                         admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    """Fake/scam confirmed: post removed, every unlocker refunded, owner warned (banned after N warnings)."""
    listing = await get_listing(db, listing_type, listing_id)
    unlocks = (await db.execute(select(Unlock).where(
        Unlock.listing_type == listing_type, Unlock.listing_id == listing_id, Unlock.refunded.is_(False)))).scalars().all()
    refunded = 0
    for u in unlocks:
        if await refund_unlock(db, u, "report_confirmed"):
            refunded += 1
            await notify(db, u.user_id, "refund", listing.title, "/wallet")
    reps = (await db.execute(select(Report).where(
        Report.listing_type == listing_type, Report.listing_id == listing_id, Report.status == "open"))).scalars().all()
    for r in reps:
        r.status = "confirmed"
    listing.status = "removed"
    owner = await db.get(User, listing.owner_id)
    owner.warnings += 1
    if owner.warnings >= int(await get_setting(db, "warnings_before_ban")):
        owner.is_banned = True
    await notify(db, owner, "post_removed", listing.title, "/dashboard")
    audit(db, admin, "report_confirmed", listing_type, listing_id, refunded=refunded, note=data.note, owner_warnings=owner.warnings)
    await db.commit()
    return {"status": "removed", "refunded": refunded, "owner_banned": owner.is_banned}


@router.post("/reports/{listing_type}/{listing_id}/dismiss")
async def dismiss_report(listing_type: str, listing_id: int, data: ReviewDecisionIn,
                         admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    listing = await get_listing(db, listing_type, listing_id)
    reps = (await db.execute(select(Report).where(
        Report.listing_type == listing_type, Report.listing_id == listing_id, Report.status == "open"))).scalars().all()
    for r in reps:
        r.status = "dismissed"
    if listing.status == "hidden":
        listing.status = "active"
    audit(db, admin, "report_dismissed", listing_type, listing_id, note=data.note)
    await db.commit()
    return {"status": listing.status}


# ---------------------------------------------------------------- users, settings, audit
@router.get("/users")
async def users(q: str = "", page: int = Query(default=1, ge=1), admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    stmt = select(User)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(or_(User.name.ilike(like), User.email.ilike(like), User.phone.ilike(like)))
    rows = (await db.execute(stmt.order_by(User.id.desc()).offset((page - 1) * 50).limit(50))).scalars().all()
    out = []
    for u in rows:
        paid, bonus = await balance(db, u.id)
        out.append({"id": u.id, "name": u.name, "email": u.email, "phone": u.phone, "verified": u.email_verified_at is not None,
                    "banned": u.is_banned, "warnings": u.warnings, "balance": paid + bonus,
                    "roles": [{"role": r.role, "kyc_status": r.kyc_status} for r in u.roles],
                    "created_at": u.created_at.isoformat()})
    return out


@router.post("/users/{user_id}/ban")
async def ban(user_id: int, banned: bool = True, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None or user.id == admin.id:
        raise AppError("not_found", 404)
    user.is_banned = banned
    audit(db, admin, "user_banned" if banned else "user_unbanned", "user", user_id)
    await db.commit()
    return {"banned": banned}


@router.get("/settings")
async def get_settings_(admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    return await get_all(db)


@router.put("/settings")
async def put_settings(data: SettingsIn, admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    unknown = [k for k in data.values if k not in DEFAULTS]
    if unknown:
        raise AppError("invalid", 422, {"unknown": unknown})
    for key, value in data.values.items():
        if type(value) is not type(DEFAULTS[key]):
            raise AppError("invalid", 422, {"field": key})
        await set_setting(db, key, value)
    audit(db, admin, "settings_changed", None, None, keys=list(data.values))
    await db.commit()
    return await get_all(db)


@router.get("/audit-logs")
async def audit_logs(admin: User = Depends(get_admin), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(AdminAuditLog, User.name).join(User, User.id == AdminAuditLog.admin_id)
        .order_by(AdminAuditLog.id.desc()).limit(200)
    )).all()
    return [{"id": a.id, "admin": name, "action": a.action, "target_type": a.target_type, "target_id": a.target_id,
             "details": a.details, "created_at": a.created_at.isoformat()} for a, name in rows]
