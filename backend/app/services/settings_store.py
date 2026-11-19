"""Business rules that the admin can change without touching code."""
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Setting

DEFAULTS: dict = {
    "packages": [
        {"key": "starter", "diamonds": 10, "price": 50, "active": True},
        {"key": "popular", "diamonds": 25, "price": 100, "active": True},
        {"key": "value", "diamonds": 60, "price": 200, "active": True},
        {"key": "provider", "diamonds": 150, "price": 400, "active": True},
    ],
    "costs": {"rent": 1, "truck": 1, "sell": 1, "donate": 1, "cleaning": 1, "quote": 1},
    "welcome_bonus": 5,
    "free_bonus_max": 3,
    "free_bonus_cooldown_days": 30,
    "report_hide_threshold": 3,
    "rent_expiry_days": 30,
    "other_expiry_days": 15,
    "no_reply_refund_hours": 48,
    "delete_refund_hours": 24,
    "warnings_before_ban": 3,
    "payment_numbers": {"bkash": "01XXXXXXXXX", "nagad": "01XXXXXXXXX"},
}


async def get_setting(db: AsyncSession, key: str):
    row = await db.get(Setting, key)
    return row.value if row is not None else DEFAULTS[key]


async def get_all(db: AsyncSession) -> dict:
    rows = (await db.execute(select(Setting))).scalars().all()
    data = dict(DEFAULTS)
    data.update({r.key: r.value for r in rows})
    return data


async def set_setting(db: AsyncSession, key: str, value) -> None:
    if key not in DEFAULTS:
        raise KeyError(key)
    row = await db.get(Setting, key)
    if row is None:
        db.add(Setting(key=key, value=value))
    else:
        row.value = value
