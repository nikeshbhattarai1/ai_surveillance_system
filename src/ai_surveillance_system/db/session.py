from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import DeclarativeBase

from ai_surveillance_system.core.config import get_settings
from ai_surveillance_system.core.logger import get_logger

settings = get_settings()
logger = get_logger(__name__)

# Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG
)

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Base class for all ORM models
class Base(DeclarativeBase):
    pass

# FastAPI Dependencies: one session per request
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields a DB session scoped to the request.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

# Called at app startup
async def init_db() -> None:
    """
    Creates all tables if they don't already exist. 
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized")


# Called at app shutdown
async def close_db() -> None:
    """
    Disposes the connection pool cleanly on shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")
