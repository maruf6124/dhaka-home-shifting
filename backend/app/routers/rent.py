"""House rent: Entire Flat (verified landlords only) and Sublet (any verified user)."""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.deps import get_optional_user, get_verified_user, has_verified_role, is_admin
from app.core.errors import AppError, pick_lang
from app.models import Area, ListingImage, RentListing, Report, Unlock, User, UserRole
from app.schemas import RentIn, RentUpdateIn, StatusIn
from app.services.contact_filter import clean_public_text
from app.services.notify import notify
from app.services.serializers import images_for, rating_summary, rent_out
from app.services.settings_store import get_setting
from app.services.refunds import refund_unlock

router = APIRouter(prefix="/rent", tags=["rent"])
LISTING_TYPE = "rent"


async def _get(db: AsyncSession, listing_id: int) -> RentListing:
    listing = await db.get(RentListing, listing_id)
    if listing is None or listing.status == "deleted":
        raise AppError("not_found", 404)
    return listing


async def _has_unlock(db: AsyncSession, user: User | None, listing_id: int) -> bool:
    if user is None:
        return False
    return bool(await db.scalar(select(Unlock.id).where(
        Unlock.user_id == user.id, Unlock.listing_type == LISTING_TYPE, Unlock.listing_id == listing_id,
        Unlock.refunded.is_(False),
    )))


async def _set_images(db: AsyncSession, listing_id: int, urls: list[str]) -> None:
    if len(urls) > 8:
        raise AppError("too_many_images")
    await db.execute(delete(ListingImage).where(ListingImage.listing_type == LISTING_TYPE, ListingImage.listing_id == listing_id))
    for i, url in enumerate(urls):
        db.add(ListingImage(listing_type=LISTING_TYPE, listing_id=listing_id, url=url[:500], sort_order=i))


def _check_can_post(user: User, listing_type: str) -> None:
    if listing_type == "entire_flat" and not has_verified_role(user, "landlord"):
        raise AppError("kyc_required", 403, {"role": "landlord"})


@router.get("")
async def list_rent(
    request: Request,
    type: str | None = Query(default=None, pattern="^(entire_flat|sublet)$"),
    area_id: int | None = None,
    min_rent: int | None = None,
    max_rent: int | None = None,
    rooms: int | None = Query(default=None, ge=1),
    tenant_type: str | None = Query(default=None, pattern="^(family|bachelor|female|any)$"),
    verified_only: bool = False,
    sort: str = Query(default="newest", pattern="^(newest|price_asc|price_desc)$"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    now = utcnow()
    q = select(RentListing).where(RentListing.status == "active", RentListing.expires_at > now)
    if type:
        q = q.where(RentListing.type == type)
    if area_id:
        child_ids = (await db.execute(select(Area.id).where(Area.parent_id == area_id))).scalars().all()
        q = q.where(RentListing.area_id.in_([area_id, *child_ids]))
    if min_rent is not None:
        q = q.where(RentListing.rent >= min_rent)
    if max_rent is not None:
        q = q.where(RentListing.rent <= max_rent)
    if rooms:
        q = q.where(RentListing.rooms >= rooms) if rooms >= 4 else q.where(RentListing.rooms == rooms)
    if tenant_type and tenant_type != "any":
        q = q.where(or_(RentListing.tenant_type == tenant_type, RentListing.tenant_type == "any"))
    if verified_only:
        verified_landlords = select(UserRole.user_id).where(UserRole.role == "landlord", UserRole.kyc_status == "verified")
        q = q.where(RentListing.owner_id.in_(verified_landlords))
    total = await db.scalar(select(func.count()).select_from(q.subquery()))
    order = {"newest": RentListing.created_at.desc(), "price_asc": RentListing.rent.asc(), "price_desc": RentListing.rent.desc()}[sort]
    rows = (await db.execute(q.order_by(order, RentListing.id.desc()).offset((page - 1) * page_size).limit(page_size))).scalars().unique().all()
    imgs = await images_for(db, LISTING_TYPE, [r.id for r in rows])
    lang = pick_lang(request)
    return {
        "items": [rent_out(r, imgs[r.id], show_private=False, lang=lang) for r in rows],
        "total": total, "page": page, "page_size": page_size,
    }


@router.get("/{listing_id}")
async def get_rent(listing_id: int, request: Request, user: User | None = Depends(get_optional_user), db: AsyncSession = Depends(get_db)):
    listing = await _get(db, listing_id)
    is_owner = user is not None and user.id == listing.owner_id
    admin = user is not None and is_admin(user)
    if listing.status in ("hidden", "removed") and not (is_owner or admin):
        raise AppError("listing_unavailable", 410)
    unlocked = await _has_unlock(db, user, listing_id)
    imgs = await images_for(db, LISTING_TYPE, [listing.id])
    room_id = None
    if unlocked:
        room_id = await db.scalar(select(Unlock.room_id).where(
            Unlock.user_id == user.id, Unlock.listing_type == LISTING_TYPE, Unlock.listing_id == listing_id))
    data = rent_out(listing, imgs[listing.id], show_private=is_owner or admin or unlocked, lang=pick_lang(request),
                    owner_rating=await rating_summary(db, listing.owner_id), unlocked=unlocked, is_owner=is_owner)
    data["room_id"] = room_id
    if is_owner:
        data["stats"] = {
            "unlocks": await db.scalar(select(func.count()).select_from(Unlock).where(
                Unlock.listing_type == LISTING_TYPE, Unlock.listing_id == listing_id)),
            "open_reports": await db.scalar(select(func.count()).select_from(Report).where(
                Report.listing_type == LISTING_TYPE, Report.listing_id == listing_id, Report.status == "open")),
        }
    return data


@router.post("", status_code=201)
async def create_rent(data: RentIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    _check_can_post(user, data.type)
    if await db.get(Area, data.area_id) is None:
        raise AppError("invalid", 422, {"field": "area_id"})
    days = await get_setting(db, "rent_expiry_days")
    payload = data.model_dump(exclude={"images"})
    payload["title"] = clean_public_text(payload["title"])
    payload["description"] = clean_public_text(payload["description"])
    listing = RentListing(**payload, owner_id=user.id, status="active", expires_at=utcnow() + timedelta(days=int(days)))
    db.add(listing)
    await db.flush()
    await _set_images(db, listing.id, data.images)
    await db.commit()
    return {"id": listing.id}


@router.patch("/{listing_id}")
async def update_rent(listing_id: int, data: RentUpdateIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await _get(db, listing_id)
    if listing.owner_id != user.id:
        raise AppError("forbidden", 403)
    if listing.status == "removed":
        raise AppError("listing_unavailable", 410)
    changes = data.model_dump(exclude_unset=True, exclude={"images"})
    for field in ("title", "description"):
        if field in changes and changes[field] is not None:
            changes[field] = clean_public_text(changes[field])
    for key, value in changes.items():
        if value is not None or key in ("size_sqft", "floor", "available_from"):
            setattr(listing, key, value)
    if data.images is not None:
        await _set_images(db, listing.id, data.images)
    await db.commit()
    return {"status": "ok"}


@router.post("/{listing_id}/status")
async def set_status(listing_id: int, data: StatusIn, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await _get(db, listing_id)
    if listing.owner_id != user.id:
        raise AppError("forbidden", 403)
    if listing.status in ("hidden", "removed"):
        raise AppError("listing_unavailable", 410)
    if data.status == "active" and listing.expires_at < utcnow():
        raise AppError("listing_unavailable", 410)
    listing.status = data.status
    await db.commit()
    return {"status": listing.status}


@router.post("/{listing_id}/renew")
async def renew(listing_id: int, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await _get(db, listing_id)
    if listing.owner_id != user.id:
        raise AppError("forbidden", 403)
    if listing.status not in ("active", "expired"):
        raise AppError("listing_unavailable", 410)
    days = await get_setting(db, "rent_expiry_days")
    listing.expires_at = utcnow() + timedelta(days=int(days))
    listing.status = "active"
    await db.commit()
    return {"status": "active", "expires_at": listing.expires_at.isoformat()}


@router.delete("/{listing_id}")
async def delete_rent(listing_id: int, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    listing = await _get(db, listing_id)
    if listing.owner_id != user.id:
        raise AppError("forbidden", 403)
    # Refund anyone who unlocked in the last N hours: they paid for a post that vanished.
    hours = int(await get_setting(db, "delete_refund_hours"))
    since = utcnow() - timedelta(hours=hours)
    recent = (await db.execute(select(Unlock).where(
        Unlock.listing_type == LISTING_TYPE, Unlock.listing_id == listing_id,
        Unlock.refunded.is_(False), Unlock.created_at >= since,
    ))).scalars().all()
    for unlock in recent:
        await refund_unlock(db, unlock, "owner_deleted")
        await notify(db, unlock.user_id, "refund", listing.title, f"/rent/{listing_id}")
    listing.status = "deleted"
    listing.deleted_at = utcnow()
    await db.commit()
    return {"status": "deleted", "refunded": len(recent)}
