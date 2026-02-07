"""
Database management for SentinelPi.

Provides async SQLAlchemy engine, session factory, and database initialization.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from src.storage.models import Base
from src.utils.config import get_settings
from src.utils.logging import create_logger

log = create_logger("storage.database")

# Global engine and session factory
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    """
    Get the global async database engine.

    Creates the engine on first call.

    Returns:
        The async SQLAlchemy engine.
    """
    global _engine

    if _engine is None:
        settings = get_settings()
        db_url = settings.database.url

        # Ensure data directory exists
        db_path = Path(settings.database.path)
        if not db_path.is_absolute():
            from src.utils.config import PROJECT_ROOT
            db_path = PROJECT_ROOT / db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)

        log.info(f"Creating database engine: {db_path}")

        _engine = create_async_engine(
            db_url,
            echo=settings.database.echo,
            # SQLite-specific settings
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )

        # Enable SQLite optimizations
        @event.listens_for(_engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            # Enable foreign keys
            cursor.execute("PRAGMA foreign_keys=ON")
            # Use WAL mode for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL")
            # Increase cache size (negative = KB)
            cursor.execute("PRAGMA cache_size=-64000")  # 64MB
            # Synchronous mode: NORMAL is a good balance
            cursor.execute("PRAGMA synchronous=NORMAL")
            # Temp store in memory
            cursor.execute("PRAGMA temp_store=MEMORY")
            cursor.close()

    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Get the global session factory.

    Returns:
        An async session factory.
    """
    global _session_factory

    if _session_factory is None:
        engine = get_engine()
        _session_factory = async_sessionmaker(
            engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
        )

    return _session_factory


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session context manager.

    Yields:
        An async database session.

    Example:
        async with get_session() as session:
            result = await session.execute(select(Source))
            sources = result.scalars().all()
    """
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


_db_initialized: bool = False


async def init_database() -> None:
    """
    Initialize the database.

    Creates all tables if they don't exist.
    Skips if already initialized in this process.
    """
    global _db_initialized
    if _db_initialized:
        return

    engine = get_engine()

    log.info("Initializing database...")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    _db_initialized = True
    log.info("Database initialized successfully")


async def close_database() -> None:
    """
    Close the database connection.

    Should be called when shutting down the application.
    """
    global _engine, _session_factory, _db_initialized

    if _engine is not None:
        log.info("Closing database connection...")
        await _engine.dispose()
        _engine = None
        _session_factory = None
        _db_initialized = False
        log.info("Database connection closed")


async def vacuum_database() -> None:
    """
    Vacuum the SQLite database to reclaim space.

    Should be run periodically for maintenance.
    """
    engine = get_engine()

    log.info("Running VACUUM on database...")

    async with engine.begin() as conn:
        # VACUUM cannot run inside a transaction
        await conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))

    # Run VACUUM outside transaction
    raw_conn = await engine.raw_connection()
    try:
        await raw_conn.execute(text("VACUUM"))
        await raw_conn.commit()
    finally:
        await raw_conn.close()

    log.info("VACUUM completed")


async def get_database_stats() -> dict:
    """
    Get database statistics.

    Returns:
        Dictionary with database stats (size, table counts, etc.).
    """
    settings = get_settings()
    from src.utils.config import PROJECT_ROOT

    db_path = Path(settings.database.path)
    if not db_path.is_absolute():
        db_path = PROJECT_ROOT / db_path

    stats = {
        "path": str(db_path),
        "exists": db_path.exists(),
        "size_bytes": db_path.stat().st_size if db_path.exists() else 0,
        "size_mb": round(db_path.stat().st_size / (1024 * 1024), 2) if db_path.exists() else 0,
    }

    if db_path.exists():
        async with get_session() as session:
            # Count records in each table
            for table_name in ["sources", "items", "filters", "alerts", "reports"]:
                result = await session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                stats[f"{table_name}_count"] = result.scalar() or 0

    return stats
