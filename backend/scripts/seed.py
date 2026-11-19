"""Adds Dhaka areas and default settings. Safe to run more than once.

    python -m scripts.seed
"""
import asyncio

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Area, Setting
from app.services.settings_store import DEFAULTS

AREAS: dict[tuple[str, str], list[tuple[str, str]]] = {
    ("মিরপুর", "Mirpur"): [("মিরপুর-১", "Mirpur-1"), ("মিরপুর-২", "Mirpur-2"), ("মিরপুর-১০", "Mirpur-10"),
                           ("মিরপুর-১১", "Mirpur-11"), ("মিরপুর-১২", "Mirpur-12"), ("পল্লবী", "Pallabi"),
                           ("কাজীপাড়া", "Kazipara"), ("শেওড়াপাড়া", "Shewrapara")],
    ("মোহাম্মদপুর", "Mohammadpur"): [("শ্যামলী", "Shyamoli"), ("আদাবর", "Adabor"), ("লালমাটিয়া", "Lalmatia")],
    ("ধানমন্ডি", "Dhanmondi"): [("জিগাতলা", "Jigatola"), ("কলাবাগান", "Kalabagan")],
    ("উত্তরা", "Uttara"): [("উত্তরা সেক্টর ৪", "Uttara Sector 4"), ("উত্তরা সেক্টর ৭", "Uttara Sector 7"), ("উত্তরা সেক্টর ১০", "Uttara Sector 10")],
    ("গুলশান", "Gulshan"): [("গুলশান-১", "Gulshan-1"), ("গুলশান-২", "Gulshan-2"), ("বনানী", "Banani"), ("বারিধারা", "Baridhara")],
    ("বাড্ডা", "Badda"): [("মেরুল বাড্ডা", "Merul Badda"), ("আফতাবনগর", "Aftabnagar")],
    ("বসুন্ধরা", "Bashundhara"): [],
    ("খিলগাঁও", "Khilgaon"): [("মালিবাগ", "Malibagh"), ("রামপুরা", "Rampura")],
    ("তেজগাঁও", "Tejgaon"): [("ফার্মগেট", "Farmgate"), ("কারওয়ান বাজার", "Karwan Bazar")],
    ("মগবাজার", "Moghbazar"): [],
    ("ওয়ারী", "Wari"): [("পুরান ঢাকা", "Old Dhaka")],
}


async def main() -> None:
    async with SessionLocal() as db:
        existing = {a.name_en for a in (await db.execute(select(Area))).scalars().all()}
        for (bn, en), children in AREAS.items():
            parent = (await db.execute(select(Area).where(Area.name_en == en))).scalar_one_or_none()
            if parent is None:
                parent = Area(name_bn=bn, name_en=en)
                db.add(parent)
                await db.flush()
            for cbn, cen in children:
                if cen not in existing:
                    db.add(Area(name_bn=cbn, name_en=cen, parent_id=parent.id))
        for key, value in DEFAULTS.items():
            if await db.get(Setting, key) is None:
                db.add(Setting(key=key, value=value))
        await db.commit()
    print("Seed done.")


if __name__ == "__main__":
    asyncio.run(main())
