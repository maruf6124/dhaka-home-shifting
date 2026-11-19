"""Lookup across listing types. MVP has 'rent'; truck, goods and cleaning
plug in here later with the same unlock / report / review engine."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import utcnow
from app.core.errors import AppError
from app.models import RentListing

LISTING_MODELS = {"rent": RentListing}
LINKS = {"rent": "/rent/{id}"}


async def get_listing(db: AsyncSession, listing_type: str, listing_id: int):
    model = LISTING_MODELS.get(listing_type)
    if model is None:
        raise AppError("invalid", 422)
    listing = await db.get(model, listing_id)
    if listing is None or listing.status == "deleted":
        raise AppError("not_found", 404)
    return listing


def is_open(listing) -> bool:
    return listing.status == "active" and listing.expires_at > utcnow()


def link_for(listing_type: str, listing_id: int) -> str:
    return LINKS[listing_type].format(id=listing_id)
