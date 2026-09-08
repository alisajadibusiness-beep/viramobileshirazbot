from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings


class Base(DeclarativeBase):
    pass


def normalize_database_url(url: str) -> str:
    """
    Normalize database URLs for SQLAlchemy async drivers.
    """
    if url.startswith("postgres://"):
        return url.replace(
            "postgres://",
            "postgresql+asyncpg://",
            1,
        )

    if url.startswith("postgresql://"):
        return url.replace(
            "postgresql://",
            "postgresql+asyncpg://",
            1,
        )

    return url


DATABASE_URL = normalize_database_url(settings.database_url)


engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide an async database session.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db() -> None:
    """
    Import all SQLAlchemy models before create_all()
    so their tables are registered in Base.metadata.
    """

    # Main VIRA MOBILE models
    from app.database import models

    # Smart Pricing / AI purchase expert models
    from app.services.smart_pricing import models as smart_pricing_models

    # Keep imports alive and explicitly registered.
    _ = (
        models,
        smart_pricing_models,
    )

    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """
    Close the database engine.
    """
    await engine.dispose()
