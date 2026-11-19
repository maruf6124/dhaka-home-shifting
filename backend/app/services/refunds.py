from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Unlock
from app.services.wallet import credit


async def refund_unlock(db: AsyncSession, unlock: Unlock, reason: str) -> bool:
    """Gives the diamonds back to the same buckets (paid/bonus) they came from.
    Returns False if it was already refunded."""
    if unlock.refunded:
        return False
    unlock.refunded = True
    unlock.refund_reason = reason
    if unlock.paid_part + unlock.bonus_part == 0:
        return True
    await credit(db, unlock.user_id, paid=unlock.paid_part, bonus=unlock.bonus_part, kind="refund",
                 ref_type="unlock", ref_id=unlock.id, note=reason)
    return True
