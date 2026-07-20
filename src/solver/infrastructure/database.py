"""SQLAlchemy database engine and session management."""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from solver.config import get_settings


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


def create_engine(database_url: str | None = None):
    """Create an async SQLAlchemy engine."""
    url = database_url or get_settings().database_url
    return create_async_engine(url, echo=False)


def create_session_factory(engine=None):
    """Create an async session factory."""
    if engine is None:
        engine = create_engine()
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


# Module-level instances (can be overridden in tests)
_engine = None
_session_factory = None


def get_engine():
    """Get or create the module-level engine."""
    global _engine
    if _engine is None:
        _engine = create_engine()
    return _engine


def get_session_factory():
    """Get or create the module-level session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = create_session_factory(get_engine())
    return _session_factory


async def get_session() -> AsyncSession:
    """Dependency that provides an async database session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


def reset_engine():
    """Reset the global engine and session factory (useful for testing)."""
    global _engine, _session_factory
    _engine = None
    _session_factory = None
