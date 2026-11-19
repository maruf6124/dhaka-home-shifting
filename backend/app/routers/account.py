"""The logged-in user's own things: profile, posts, KYC, uploads, notifications."""
from typing import Literal

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, utcnow
from app.core.deps import get_current_user, get_verified_user
from app.core.errors import AppError
from app.models import Area, KycDocument, Notification, RentListing, User, UserRole
from app.schemas import UserUpdateIn
from app.services.notify import notify_admins
from app.services.serializers import images_for, user_out
from app.services.storage import save_private_document, save_public_image

router = APIRouter(tags=["account"])

REQUIRED_DOCS: dict[str, list[str]] = {
    "landlord": ["nid_front", "nid_back", "utility_bill"],
    "driver": ["nid_front", "nid_back", "driving_license", "vehicle_registration"],
    "cleaner": ["nid_front", "nid_back", "team_photo"],
}
ProviderRole = Literal["landlord", "driver", "cleaner"]


@router.patch("/users/me")
async def update_me(data: UserUpdateIn, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if data.name is not None:
        user.name = data.name
    if data.language is not None:
        user.language = data.language
    await db.commit()
    return await user_out(db, user)


@router.get("/users/me/listings")
async def my_listings(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(RentListing).where(RentListing.owner_id == user.id, RentListing.status != "deleted")
        .order_by(RentListing.created_at.desc())
    )).scalars().all()
    imgs = await images_for(db, "rent", [r.id for r in rows])
    return [{"id": r.id, "listing_type": "rent", "type": r.type, "title": r.title, "rent": r.rent,
             "area_bn": r.area.name_bn, "area_en": r.area.name_en, "status": r.status,
             "expired": r.expires_at < utcnow(), "expires_at": r.expires_at.isoformat(),
             "image": (imgs[r.id] or [None])[0]} for r in rows]


@router.get("/areas")
async def areas(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(Area).order_by(Area.parent_id.is_not(None), Area.name_en))).scalars().all()
    return [{"id": a.id, "name_bn": a.name_bn, "name_en": a.name_en, "parent_id": a.parent_id} for a in rows]


@router.post("/uploads/image", status_code=201)
async def upload_image(file: UploadFile = File(...), user: User = Depends(get_verified_user)):
    return {"url": await save_public_image(file)}


# ---------------------------------------------------------------- KYC
@router.get("/kyc")
async def kyc_status(user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(KycDocument).where(KycDocument.user_id == user.id))).scalars().all()
    roles = {r.role: r for r in user.roles}
    return {
        role: {
            "status": roles[role].kyc_status if role in roles else "none",
            "note": roles[role].review_note if role in roles else None,
            "required": required,
            "uploaded": sorted({d.doc_type for d in docs if d.role == role and d.status != "deleted"}),
        }
        for role, required in REQUIRED_DOCS.items()
    }


@router.post("/kyc/documents", status_code=201)
async def upload_kyc(role: ProviderRole = Form(...), doc_type: str = Form(...), file: UploadFile = File(...),
                     user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    if doc_type not in REQUIRED_DOCS[role]:
        raise AppError("invalid", 422, {"field": "doc_type"})
    key, content_type = await save_private_document(file)
    old = (await db.execute(select(KycDocument).where(
        KycDocument.user_id == user.id, KycDocument.role == role, KycDocument.doc_type == doc_type))).scalars().all()
    for d in old:  # replaced documents are deleted by the cleanup job
        d.status, d.delete_after = "replaced", utcnow()
    db.add(KycDocument(user_id=user.id, role=role, doc_type=doc_type, storage_key=key, content_type=content_type))
    await db.commit()
    return {"status": "uploaded"}


@router.post("/kyc/{role}/submit")
async def submit_kyc(role: ProviderRole, user: User = Depends(get_verified_user), db: AsyncSession = Depends(get_db)):
    docs = (await db.execute(select(KycDocument.doc_type).where(
        KycDocument.user_id == user.id, KycDocument.role == role, KycDocument.status == "pending"))).scalars().all()
    missing = [d for d in REQUIRED_DOCS[role] if d not in docs]
    if missing:
        raise AppError("invalid", 422, {"missing": missing})
    existing = next((r for r in user.roles if r.role == role), None)
    if existing is None:
        user.roles.append(UserRole(role=role, kyc_status="pending"))
    elif existing.kyc_status != "verified":
        existing.kyc_status, existing.review_note = "pending", None
    await notify_admins(db, "admin_review", f"KYC: {role}", "/admin/kyc")
    await db.commit()
    return {"status": "pending"}


# ---------------------------------------------------------------- notifications
@router.get("/notifications")
async def notifications(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(
        select(Notification).where(Notification.user_id == user.id).order_by(Notification.id.desc()).limit(50)
    )).scalars().all()
    unread = sum(1 for n in rows if not n.is_read)
    return {"unread": unread, "items": [
        {"id": n.id, "type": n.type, "title": n.title, "body": n.body, "link": n.link, "is_read": n.is_read,
         "created_at": n.created_at.isoformat()} for n in rows]}


@router.post("/notifications/read-all")
async def read_all(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    await db.execute(update(Notification).where(Notification.user_id == user.id).values(is_read=True))
    await db.commit()
    return {"status": "ok"}
