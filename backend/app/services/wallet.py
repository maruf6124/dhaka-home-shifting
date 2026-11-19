"""Diamond wallet. Every change happens inside the caller's DB transaction,
locks the wallet row (SELECT ... FOR UPDATE on MySQL) and writes a ledger row.
Bonus diamonds are spent before paid ones.
"""
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError
from app.models import DiamondTransaction, Wallet


@dataclass
class Spend:
    paid: int
    bonus: int


async def lock_wallet(db: AsyncSession, user_id: int) -> Wallet:
    wallet = (
        await db.execute(select(Wallet).where(Wallet.user_id == user_id).with_for_update())
    ).scalar_one_or_none()
    if wallet is None:
        wallet = Wallet(user_id=user_id, paid_balance=0, bonus_balance=0)
        db.add(wallet)
        await db.flush()
    return wallet


async def balance(db: AsyncSession, user_id: int) -> tuple[int, int]:
    wallet = await db.get(Wallet, user_id)
    if wallet is None:
        return 0, 0
    return wallet.paid_balance, wallet.bonus_balance


async def spend(db: AsyncSession, user_id: int, amount: int, kind: str, ref_type: str, ref_id: int | None, note: str | None = None) -> Spend:
    wallet = await lock_wallet(db, user_id)
    if wallet.paid_balance + wallet.bonus_balance < amount:
        raise AppError("insufficient_balance", 402)
    from_bonus = min(wallet.bonus_balance, amount)
    from_paid = amount - from_bonus
    wallet.bonus_balance -= from_bonus
    wallet.paid_balance -= from_paid
    db.add(DiamondTransaction(
        user_id=user_id, amount=-amount, paid_delta=-from_paid, bonus_delta=-from_bonus, kind=kind,
        ref_type=ref_type, ref_id=ref_id, balance_after=wallet.paid_balance + wallet.bonus_balance, note=note,
    ))
    return Spend(paid=from_paid, bonus=from_bonus)


async def credit(db: AsyncSession, user_id: int, paid: int = 0, bonus: int = 0, kind: str = "purchase",
                 ref_type: str | None = None, ref_id: int | None = None, note: str | None = None) -> None:
    if paid < 0 or bonus < 0 or paid + bonus == 0:
        raise AppError("invalid")
    wallet = await lock_wallet(db, user_id)
    wallet.paid_balance += paid
    wallet.bonus_balance += bonus
    db.add(DiamondTransaction(
        user_id=user_id, amount=paid + bonus, paid_delta=paid, bonus_delta=bonus, kind=kind,
        ref_type=ref_type, ref_id=ref_id, balance_after=wallet.paid_balance + wallet.bonus_balance, note=note,
    ))
