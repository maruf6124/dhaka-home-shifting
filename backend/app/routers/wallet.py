from datetime import timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.deps import get_verified_user
from app.core.errors import AppError
from app.models import DiamondTransaction, FreeDiamondRequest, PaymentRequest, User
from app.schemas import FreeRequestIn, TopupIn
from app.services.notify import notify_admins
from app.services.settings_store import get_all
from app.services.wallet import balance

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("")
async def wallet(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    paid, bonus = await balance(db, user.id)
    cfg = await get_all(db)
    last_free = (await db.execute(
        select(FreeDiamondRequest).where(FreeDiamondRequest.user_id == user.id).order_by(FreeDiamondRequest.id.desc()).limit(1)
    )).scalar_one_or_none()
    pending_topups = (await db.execute(
        select(PaymentRequest).where(PaymentRequest.user_id == user.id, PaymentRequest.status == "pending")
    )).scalars().all()
    return {
        "balance": paid + bonus, "paid_balance": paid, "bonus_balance": bonus,
        "packages": [p for p in cfg["packages"] if p.get("active", True)],
        "payment_numbers": cfg["payment_numbers"],
        "costs": cfg["costs"],
        "free_bonus": {
            "cooldown_days": cfg["free_bonus_cooldown_days"],
            "last_request": None if last_free is None else {
                "status": last_free.status, "created_at": last_free.created_at.isoformat(),
                "approved_amount": last_free.approved_amount},
        },
        "pending_topups": [{"id": p.id, "trx_id": p.trx_id, "diamonds": p.diamonds, "amount_bdt": p.amount_bdt,
                            "created_at": p.created_at.isoformat()} for p in pending_topups],
    }


@router.get("/transactions")
async def transactions(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(DiamondTransaction).where(DiamondTransaction.user_id == user.id)
        .order_by(DiamondTransaction.id.desc()).limit(100)
    )).scalars().all()
    return [{"id": t.id, "amount": t.amount, "kind": t.kind, "note": t.note, "balance_after": t.balance_after,
             "created_at": t.created_at.isoformat()} for t in rows]


@router.post("/topup", status_code=201)
async def topup(data: TopupIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    cfg = await get_all(db)
    package = next((p for p in cfg["packages"] if p["key"] == data.package_key and p.get("active", True)), None)
    if package is None:
        raise AppError("bad_package")
    if await db.scalar(select(PaymentRequest.id).where(PaymentRequest.trx_id == data.trx_id)):
        raise AppError("trx_used", 409)
    req = PaymentRequest(user_id=user.id, method=data.method, package_key=package["key"], diamonds=int(package["diamonds"]),
                         amount_bdt=int(package["price"]), trx_id=data.trx_id, sender_number=data.sender_number)
    db.add(req)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError("trx_used", 409)
    await notify_admins(db, "admin_review", f"TrxID {data.trx_id}", "/admin/payments")
    await db.commit()
    return {"id": req.id, "status": "pending"}


@router.post("/free-request", status_code=201)
async def free_request(data: FreeRequestIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    paid, bonus = await balance(db, user.id)
    if paid + bonus > 0:
        raise AppError("free_not_allowed")
    cfg = await get_all(db)
    last = (await db.execute(
        select(FreeDiamondRequest).where(FreeDiamondRequest.user_id == user.id).order_by(FreeDiamondRequest.id.desc()).limit(1)
    )).scalar_one_or_none()
    if last is not None:
        if last.status == "pending":
            raise AppError("free_pending", 409)
        if last.status == "approved" and last.created_at > utcnow() - timedelta(days=int(cfg["free_bonus_cooldown_days"])):
            raise AppError("free_cooldown", 429)
    req = FreeDiamondRequest(user_id=user.id, reason=data.reason)
    db.add(req)
    await notify_admins(db, "admin_review", data.reason[:100], "/admin/payments")
    await db.commit()
    return {"id": req.id, "status": "pending"}
