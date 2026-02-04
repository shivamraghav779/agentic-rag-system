"""Database session management."""
from app.db.base import (
    engine,
    async_engine,
    SessionLocal,
    AsyncSessionLocal,
    Base,
)


def init_db():
    """Initialize database tables (sync, for legacy use)."""
    Base.metadata.create_all(bind=engine)


async def init_db_async():
    """Initialize database tables using async engine."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_db():
    """Dependency for getting sync database session (legacy)."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def async_get_db():
    """Dependency for getting async database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
