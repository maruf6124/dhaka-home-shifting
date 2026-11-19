"""Creates the first admin from the command line (never through the public API).

    python -m scripts.create_admin --name "Admin" --email admin@example.com --phone 01700000000
"""
import argparse
import asyncio
import getpass

from sqlalchemy import select

from app.core.database import SessionLocal, utcnow
from app.core.security import hash_password
from app.models import User, UserRole
from app.schemas import normalize_phone
from app.services.wallet import lock_wallet


async def main(name: str, email: str, phone: str, password: str) -> None:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email.lower()))).scalar_one_or_none()
        if user is None:
            user = User(name=name, email=email.lower(), phone=normalize_phone(phone), password_hash=hash_password(password),
                        email_verified_at=utcnow(), welcome_bonus_given=True)
            user.roles.append(UserRole(role="client", kyc_status="verified"))
            db.add(user)
            await db.flush()
        if not any(r.role == "admin" for r in user.roles):
            user.roles.append(UserRole(role="admin", kyc_status="verified"))
        await lock_wallet(db, user.id)
        await db.commit()
        print(f"Admin ready: {user.email} (id {user.id})")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--name", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--phone", required=True)
    p.add_argument("--password")
    a = p.parse_args()
    pw = a.password or getpass.getpass("Password (min 8): ")
    if len(pw) < 8:
        raise SystemExit("Password must be at least 8 characters")
    asyncio.run(main(a.name, a.email, a.phone, pw))
