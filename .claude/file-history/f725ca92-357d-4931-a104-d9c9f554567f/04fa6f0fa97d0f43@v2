"""
Pytest configuration and fixtures for SentinelPi tests.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.storage.models import Base


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def config_dir(temp_dir: Path) -> Path:
    """Create a temporary config directory."""
    config_path = temp_dir / "config"
    config_path.mkdir()
    return config_path


@pytest.fixture
def data_dir(temp_dir: Path) -> Path:
    """Create a temporary data directory."""
    data_path = temp_dir / "data"
    data_path.mkdir()
    return data_path


@pytest_asyncio.fixture
async def db_engine(temp_dir: Path):
    """Create a test database engine."""
    db_path = temp_dir / "test.db"
    engine = create_async_engine(
        f"sqlite+aiosqlite:///{db_path}",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    factory = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with factory() as session:
        yield session
        await session.rollback()


@pytest.fixture
def sample_source_data() -> dict:
    """Sample source data for testing."""
    return {
        "name": "Test RSS Feed",
        "type": "rss",
        "url": "https://example.com/feed.xml",
        "enabled": True,
        "interval_minutes": 60,
        "priority": 2,
        "category": "test",
        "tags": ["test", "example"],
    }


@pytest.fixture
def sample_item_data() -> dict:
    """Sample item data for testing."""
    return {
        "guid": "test-guid-123",
        "content_hash": "abc123def456",
        "title": "Test Article Title",
        "url": "https://example.com/article",
        "author": "Test Author",
        "content": "This is the full content of the test article.",
        "summary": "This is a summary.",
    }


@pytest.fixture
def sample_filter_data() -> dict:
    """Sample filter data for testing."""
    return {
        "name": "Test Filter",
        "description": "A test filter",
        "action": "highlight",
        "conditions": {
            "type": "keywords",
            "field": "all",
            "operator": "contains",
            "value": ["test", "example"],
        },
        "score_modifier": 10.0,
        "enabled": True,
        "priority": 100,
    }
