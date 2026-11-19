from collections.abc import AsyncIterator
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

settings = get_settings()

_engine_kwargs: dict = {"pool_pre_ping": True}
if not settings.is_sqlite:
    # Free MySQL tiers allow few connections and close idle ones.
    _engine_kwargs.update(pool_size=settings.db_pool_size, max_overflow=2, pool_recycle=280)

engine = create_async_engine(settings.database_url, **_engine_kwargs)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    """Naive UTC datetime (MySQL DATETIME has no time zone)."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
