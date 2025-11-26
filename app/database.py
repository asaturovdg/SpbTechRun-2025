from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from .config.config import settings

# Async SQLAlchemy engine used by the application.
# 
# `echo` is controlled by settings.database_echo so that
# developers can toggle SQL logging via environment (DB_ECHO).
engine = create_async_engine(
    settings.database_url_async,
    echo=settings.database_echo,
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
