from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Notification, User, UserRole

# (bangla, english) titles per notification type
TEXT = {
    "unlocked": ("কেউ আপনার পোস্ট আনলক করেছেন", "Someone unlocked your post"),
    "new_message": ("নতুন মেসেজ", "New message"),
    "kyc_approved": ("আপনার রোল ভেরিফাইড হয়েছে", "Your role is verified"),
    "kyc_rejected": ("KYC রিজেক্ট হয়েছে", "KYC was rejected"),
    "topup_approved": ("ডায়মন্ড যোগ হয়েছে", "Diamonds added"),
    "topup_rejected": ("রিচার্জ রিজেক্ট হয়েছে", "Top-up was rejected"),
    "bonus_approved": ("ফ্রি বোনাস ডায়মন্ড পেয়েছেন", "You received free bonus diamonds"),
    "bonus_rejected": ("ফ্রি বোনাস রিকোয়েস্ট রিজেক্ট হয়েছে", "Free bonus request was rejected"),
    "gift": ("আপনাকে ডায়মন্ড গিফট করা হয়েছে", "You were gifted diamonds"),
    "refund": ("ডায়মন্ড ফেরত পেয়েছেন", "Diamond refunded"),
    "report_hidden": ("আপনার পোস্ট সাময়িক লুকানো হয়েছে", "Your post was hidden for review"),
    "post_removed": ("রিপোর্টের কারণে পোস্ট বন্ধ হয়েছে", "Your post was removed after reports"),
    "admin_review": ("নতুন রিপোর্ট যাচাই করুন", "New report needs review"),
    "already_rented_report": ("কেউ জানিয়েছেন বাসাটি আগেই ভাড়া হয়েছে", "Someone says your home is already rented"),
}


async def notify(db: AsyncSession, user: User | int, type_: str, body: str = "", link: str | None = None) -> None:
    if isinstance(user, int):
        user = await db.get(User, user)
        if user is None:
            return
    bn, en = TEXT.get(type_, (type_, type_))
    db.add(Notification(user_id=user.id, type=type_, title=en if user.language == "en" else bn, body=body, link=link))


async def notify_admins(db: AsyncSession, type_: str, body: str = "", link: str | None = None) -> None:
    admin_ids = (await db.execute(select(UserRole.user_id).where(UserRole.role == "admin"))).scalars().all()
    for uid in admin_ids:
        await notify(db, uid, type_, body, link)
