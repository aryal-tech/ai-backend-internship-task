from contextlib import asynccontextmanager
from typing import AsyncIterator
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from .config import get_settings

_settings = get_settings()
_engine = create_async_engine(
    _settings.mysql_async_url, pool_pre_ping=True, future=True
)
_SessionLocal = async_sessionmaker(_engine, expire_on_commit=False, autoflush=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionLocal() as session:
        yield session
        
