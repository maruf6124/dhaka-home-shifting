"""Diamond unlocks, reports (with refunds) and reviews."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.deps import get_verified_user
from app.core.errors import AppError, pick_lang
from app.models import ChatParticipant, ChatRoom, Message, Report, Review, Unlock, User
from app.schemas import ReportIn, ReviewIn, UnlockIn
from app.services.listings import get_listing, is_open, link_for
from app.services.notify import notify, notify_admins
from app.services.refunds import refund_unlock
from app.services.serializers import images_for, rent_out
from app.services.settings_store import get_setting
from app.services.wallet import spend

router = APIRouter(tags=["unlocks & reports"])


async def _room_for(db: AsyncSession, listing_type: str, listing_id: int, owner_id: int, user_id: int) -> ChatRoom:
    room = (await db.execute(
        select(ChatRoom).join(ChatParticipant).where(
            ChatRoom.listing_type == listing_type, ChatRoom.listing_id == listing_id, ChatParticipant.user_id == user_id)
    )).scalars().first()
    if room is None:
        room = ChatRoom(listing_type=listing_type, listing_id=listing_id)
        room.participants = [ChatParticipant(user_id=owner_id), ChatParticipant(user_id=user_id)]
        db.add(room)
        await db.flush()
    return room


@router.post("/unlocks", status_code=201)
async def unlock(data: UnlockIn, request: Request, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await get_listing(db, data.listing_type, data.listing_id)
    if listing.owner_id == user.id:
        raise AppError("own_listing")
    if not is_open(listing):
        raise AppError("listing_unavailable", 410)
    existing = (await db.execute(select(Unlock).where(
        Unlock.user_id == user.id, Unlock.listing_type == data.listing_type, Unlock.listing_id == data.listing_id,
    ))).scalar_one_or_none()
    if existing is not None and not existing.refunded:
        raise AppError("already_unlocked", 409)

    cost = int((await get_setting(db, "costs")).get(data.listing_type, 1))
    room = await _room_for(db, data.listing_type, data.listing_id, listing.owner_id, user.id)
    if existing is None:
        existing = Unlock(user_id=user.id, listing_type=data.listing_type, listing_id=data.listing_id, cost=cost, room_id=room.id)
        db.add(existing)
        await db.flush()
    else:  # unlocking again after a refund
        existing.refunded, existing.refund_reason, existing.cost, existing.created_at = False, None, cost, utcnow()
    used = await spend(db, user.id, cost, "unlock", "unlock", existing.id, note=f"{data.listing_type}:{data.listing_id}")
    existing.paid_part, existing.bonus_part = used.paid, used.bonus
    await notify(db, listing.owner_id, "unlocked", listing.title, f"/messages/{room.id}")
    try:
        await db.commit()
    except IntegrityError:  # a parallel request unlocked first; nothing was charged
        await db.rollback()
        raise AppError("already_unlocked", 409)
    imgs = await images_for(db, data.listing_type, [listing.id])
    detail = rent_out(listing, imgs[listing.id], show_private=True, lang=pick_lang(request), unlocked=True)
    detail["room_id"] = room.id
    return {"unlock_id": existing.id, "room_id": room.id, "listing": detail}


@router.get("/unlocks/mine")
async def my_unlocks(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Unlock).where(Unlock.user_id == user.id).order_by(Unlock.created_at.desc()))).scalars().all()
    out = []
    for u in rows:
        listing = await get_listing(db, u.listing_type, u.listing_id) if u.listing_type else None
        out.append({
            "id": u.id, "listing_type": u.listing_type, "listing_id": u.listing_id, "title": listing.title,
            "room_id": u.room_id, "cost": u.cost, "refunded": u.refunded, "refund_reason": u.refund_reason,
            "created_at": u.created_at.isoformat(), "link": link_for(u.listing_type, u.listing_id),
        })
    return out


@router.post("/unlocks/{unlock_id}/claim-refund")
async def claim_no_reply_refund(unlock_id: int, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    """If the owner never replied in chat within N hours, the unlocker can take the diamond back."""
    u = await db.get(Unlock, unlock_id)
    if u is None or u.user_id != user.id:
        raise AppError("not_found", 404)
    hours = int(await get_setting(db, "no_reply_refund_hours"))
    if u.refunded or u.created_at > utcnow() - timedelta(hours=hours):
        raise AppError("refund_not_eligible")
    listing = await get_listing(db, u.listing_type, u.listing_id)
    owner_msgs = await db.scalar(select(func.count()).select_from(Message).where(
        Message.room_id == u.room_id, Message.sender_id == listing.owner_id))
    if owner_msgs:
        raise AppError("refund_not_eligible")
    await refund_unlock(db, u, "no_reply")
    await notify(db, user, "refund", listing.title, link_for(u.listing_type, u.listing_id))
    await db.commit()
    return {"status": "refunded"}


@router.post("/reports", status_code=201)
async def report(data: ReportIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await get_listing(db, data.listing_type, data.listing_id)
    if listing.owner_id == user.id:
        raise AppError("forbidden", 403)
    db.add(Report(reporter_id=user.id, listing_type=data.listing_type, listing_id=data.listing_id,
                  reason=data.reason, note=data.note))
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise AppError("already_reported", 409)
    link = link_for(data.listing_type, data.listing_id)
    if data.reason == "already_rented":
        await notify(db, listing.owner_id, "already_rented_report", listing.title, "/dashboard")
    open_count = await db.scalar(select(func.count()).select_from(Report).where(
        Report.listing_type == data.listing_type, Report.listing_id == data.listing_id, Report.status == "open"))
    threshold = int(await get_setting(db, "report_hide_threshold"))
    hidden = False
    if open_count >= threshold and listing.status == "active":
        listing.status = "hidden"  # temporary; an admin decides
        hidden = True
        await notify(db, listing.owner_id, "report_hidden", listing.title, "/dashboard")
        await notify_admins(db, "admin_review", listing.title, "/admin/reports")
    await db.commit()
    return {"status": "reported", "hidden": hidden}


@router.get("/reports/on-my-listings")
async def reports_on_my_listings(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    from app.models import RentListing
    rows = (await db.execute(
        select(Report, RentListing.title).join(RentListing, (Report.listing_type == "rent") & (Report.listing_id == RentListing.id))
        .where(RentListing.owner_id == user.id, Report.status == "open").order_by(Report.created_at.desc())
    )).all()
    return [{"id": r.id, "listing_id": r.listing_id, "title": title, "reason": r.reason, "note": r.note,
             "created_at": r.created_at.isoformat()} for r, title in rows]


@router.post("/reports/{report_id}/owner-confirm-rented")
async def owner_confirm_rented(report_id: int, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    """The owner agrees the home was already rented: the reporter gets the diamond back
    and the post is marked rented."""
    r = await db.get(Report, report_id)
    if r is None or r.reason != "already_rented" or r.status != "open":
        raise AppError("not_found", 404)
    listing = await get_listing(db, r.listing_type, r.listing_id)
    if listing.owner_id != user.id:
        raise AppError("forbidden", 403)
    u = (await db.execute(select(Unlock).where(
        Unlock.user_id == r.reporter_id, Unlock.listing_type == r.listing_type, Unlock.listing_id == r.listing_id))).scalar_one_or_none()
    if u is not None and await refund_unlock(db, u, "already_rented"):
        await notify(db, r.reporter_id, "refund", listing.title, link_for(r.listing_type, r.listing_id))
    r.status = "confirmed"
    if listing.status in ("active", "hidden"):
        listing.status = "rented"
    await db.commit()
    return {"status": "ok"}


@router.post("/reviews", status_code=201)
async def review(data: ReviewIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await get_listing(db, data.listing_type, data.listing_id)
    unlocked = await db.scalar(select(Unlock.id).where(
        Unlock.user_id == user.id, Unlock.listing_type == data.listing_type, Unlock.listing_id == data.listing_id))
    if not unlocked:
        raise AppError("unlock_required", 403)
    db.add(Review(reviewer_id=user.id, target_user_id=listing.owner_id, listing_type=data.listing_type,
                  listing_id=data.listing_id, rating=data.rating, comment=data.comment))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise AppError("already_reviewed", 409)
    return {"status": "ok"}


@router.get("/users/{user_id}/reviews")
async def user_reviews(user_id: int, db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Review, User.name).join(User, User.id == Review.reviewer_id)
        .where(Review.target_user_id == user_id).order_by(Review.created_at.desc()).limit(50)
    )).all()
    return [{"rating": r.rating, "comment": r.comment, "reviewer": name.split(" ")[0],
             "created_at": r.created_at.isoformat()} for r, name in rows]
