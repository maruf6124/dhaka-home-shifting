from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import is_admin
from app.models import ListingImage, RentListing, Review, User
from app.schemas import RoleOut, UserOut
from app.services.wallet import balance


async def user_out(db: AsyncSession, user: User) -> UserOut:
    paid, bonus = await balance(db, user.id)
    return UserOut(
        id=user.id, name=user.name, email=user.email, phone=user.phone, language=user.language,
        email_verified=user.email_verified_at is not None,
        roles=[RoleOut(role=r.role, kyc_status=r.kyc_status, review_note=r.review_note) for r in user.roles],
        is_admin=is_admin(user), balance=paid + bonus, paid_balance=paid, bonus_balance=bonus,
    )


async def rating_summary(db: AsyncSession, user_id: int) -> dict:
    avg, count = (await db.execute(
        select(func.avg(Review.rating), func.count(Review.id)).where(Review.target_user_id == user_id)
    )).one()
    return {"avg": round(float(avg), 1) if avg else None, "count": count}


async def images_for(db: AsyncSession, listing_type: str, ids: list[int]) -> dict[int, list[str]]:
    if not ids:
        return {}
    rows = (await db.execute(
        select(ListingImage).where(ListingImage.listing_type == listing_type, ListingImage.listing_id.in_(ids))
        .order_by(ListingImage.listing_id, ListingImage.sort_order)
    )).scalars().all()
    out: dict[int, list[str]] = {i: [] for i in ids}
    for img in rows:
        out[img.listing_id].append(img.url)
    return out


def rent_out(listing: RentListing, images: list[str], show_private: bool, lang: str = "bn",
             owner_rating: dict | None = None, unlocked: bool = False, is_owner: bool = False) -> dict:
    """Private fields are left out of the response (not just hidden in the UI)
    unless the viewer is the owner, an admin or has unlocked the post."""
    area = listing.area
    owner_verified = any(r.role == "landlord" and r.kyc_status == "verified" for r in listing.owner.roles)
    data = {
        "id": listing.id,
        "type": listing.type,
        "area": {"id": area.id, "name": area.name_en if lang == "en" else area.name_bn,
                 "name_bn": area.name_bn, "name_en": area.name_en},
        "title": listing.title,
        "description": listing.description,
        "rent": listing.rent,
        "service_charge": listing.service_charge,
        "advance_months": listing.advance_months,
        "rooms": listing.rooms,
        "baths": listing.baths,
        "size_sqft": listing.size_sqft,
        "floor": listing.floor,
        "tenant_type": listing.tenant_type,
        "amenities": listing.amenities or [],
        "available_from": listing.available_from.isoformat() if listing.available_from else None,
        "images": images,
        "status": listing.status,
        "expires_at": listing.expires_at.isoformat(),
        "created_at": listing.created_at.isoformat(),
        "owner": {"id": listing.owner.id, "verified": owner_verified, "rating": owner_rating},
        "unlocked": unlocked,
        "is_owner": is_owner,
        "private": None,
    }
    if show_private:
        data["private"] = {
            "road_no": listing.road_no,
            "house_no": listing.house_no,
            "contact_phone": listing.contact_phone,
        }
    return data
