from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from backend.config.settings import get_settings


DATABASE_URL = get_settings().database_url


class Base(DeclarativeBase):
    pass


_engine: AsyncEngine | None = None
_session_local: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(DATABASE_URL, echo=False)
    return _engine


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _session_local
    if _session_local is None:
        _session_local = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_local


async def init_db() -> None:
    import backend.db.models  # noqa: F401 - registers models on Base.metadata

    async with get_engine().begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_sessionmaker()() as session:
        yield session
