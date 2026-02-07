"""
Base collector class for SentinelPi.

Provides the abstract interface and common functionality for all collectors.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, AsyncIterator

from src.storage.models import Source, SourceType
from src.utils.dates import now
from src.utils.http import HttpClient, get_http_client
from src.utils.logging import create_logger
from src.utils.parsing import content_hash

log = create_logger("collectors.base")


@dataclass
class CollectedItem:
    """
    Represents an item collected from a source.

    This is a transport object between collectors and the storage layer.
    """

    # Required fields
    guid: str
    title: str

    # Optional content
    url: str | None = None
    author: str | None = None
    content: str | None = None
    summary: str | None = None

    # Dates
    published_at: datetime | None = None
    collected_at: datetime = field(default_factory=now)

    # Media
    image_url: str | None = None
    media_urls: list[str] = field(default_factory=list)

    # Metadata
    language: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def content_hash(self) -> str:
        """Generate a hash of the item's content for deduplication."""
        # Combine title and content for hashing
        text = f"{self.title}\n{self.content or ''}"
        return content_hash(text)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "guid": self.guid,
            "title": self.title,
            "url": self.url,
            "author": self.author,
            "content": self.content,
            "summary": self.summary,
            "published_at": self.published_at,
            "collected_at": self.collected_at,
            "image_url": self.image_url,
            "media_urls": self.media_urls,
            "language": self.language,
            "content_hash": self.content_hash,
        }


@dataclass
class CollectionResult:
    """Result of a collection operation."""

    source_id: str
    source_name: str
    success: bool
    items_collected: int = 0
    items_new: int = 0
    error: str | None = None
    duration_ms: float = 0
    timestamp: datetime = field(default_factory=now)

    def __str__(self) -> str:
        if self.success:
            return (
                f"[{self.source_name}] Collected {self.items_collected} items "
                f"({self.items_new} new) in {self.duration_ms:.0f}ms"
            )
        return f"[{self.source_name}] Failed: {self.error}"


class BaseCollector(ABC):
    """
    Abstract base class for all collectors.

    Collectors are responsible for fetching data from external sources
    and converting it into CollectedItem objects.

    Subclasses must implement:
    - collect(): Async generator yielding CollectedItem objects
    - supports_source_type(): Class method returning supported SourceType

    Example:
        class RSSCollector(BaseCollector):
            @classmethod
            def supports_source_type(cls) -> SourceType:
                return SourceType.RSS

            async def collect(self) -> AsyncIterator[CollectedItem]:
                # Fetch and parse RSS feed
                for entry in feed.entries:
                    yield CollectedItem(
                        guid=entry.id,
                        title=entry.title,
                        ...
                    )
    """

    def __init__(
        self,
        source: Source,
        http_client: HttpClient | None = None,
    ) -> None:
        """
        Initialize the collector.

        Args:
            source: The source to collect from.
            http_client: HTTP client to use (uses global client if None).
        """
        self.source = source
        self.http = http_client or get_http_client()
        self.log = create_logger(
            f"collectors.{self.source.type.value}",
            source_id=self.source.id,
            source_name=self.source.name,
        )

    @classmethod
    @abstractmethod
    def supports_source_type(cls) -> SourceType:
        """
        Return the source type this collector supports.

        Returns:
            The SourceType enum value.
        """
        pass

    @abstractmethod
    async def collect(self) -> AsyncIterator[CollectedItem]:
        """
        Collect items from the source.

        Yields:
            CollectedItem objects.

        Raises:
            CollectorError: If collection fails.
        """
        pass
        # Make this an async generator
        if False:
            yield  # pragma: no cover

    async def validate(self) -> bool:
        """
        Validate that the source is accessible.

        Returns:
            True if the source is valid and accessible.
        """
        try:
            response = await self.http.head(self.source.url)
            return response.ok
        except Exception as e:
            self.log.warning(f"Validation failed: {e}")
            return False

    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value from the source config.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value or default.
        """
        config = self.source.config or {}
        return config.get(key, default)

    async def run(self) -> CollectionResult:
        """
        Run the collector and return results.

        This method handles timing, error catching, and result generation.

        Returns:
            CollectionResult with collection statistics.
        """
        import time

        start_time = time.monotonic()
        items_collected = 0
        items: list[CollectedItem] = []

        try:
            self.log.info(f"Starting collection from {self.source.url}")

            async for item in self.collect():
                items.append(item)
                items_collected += 1

            duration_ms = (time.monotonic() - start_time) * 1000

            self.log.info(
                f"Collected {items_collected} items in {duration_ms:.0f}ms"
            )

            return CollectionResult(
                source_id=self.source.id,
                source_name=self.source.name,
                success=True,
                items_collected=items_collected,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = (time.monotonic() - start_time) * 1000
            error_msg = str(e)

            self.log.error(f"Collection failed: {error_msg}")

            return CollectionResult(
                source_id=self.source.id,
                source_name=self.source.name,
                success=False,
                items_collected=items_collected,
                error=error_msg,
                duration_ms=duration_ms,
            )


class CollectorError(Exception):
    """Exception raised when a collector fails."""

    def __init__(
        self,
        message: str,
        source_id: str | None = None,
        cause: Exception | None = None,
    ) -> None:
        super().__init__(message)
        self.source_id = source_id
        self.cause = cause


# Collector registry
_collectors: dict[SourceType, type[BaseCollector]] = {}


def register_collector(collector_class: type[BaseCollector]) -> type[BaseCollector]:
    """
    Register a collector class for its source type.

    This is typically used as a decorator.

    Args:
        collector_class: The collector class to register.

    Returns:
        The collector class (unchanged).

    Example:
        @register_collector
        class RSSCollector(BaseCollector):
            ...
    """
    source_type = collector_class.supports_source_type()
    _collectors[source_type] = collector_class
    log.debug(f"Registered collector for {source_type.value}: {collector_class.__name__}")
    return collector_class


def get_collector_class(source_type: SourceType) -> type[BaseCollector] | None:
    """
    Get the collector class for a source type.

    Args:
        source_type: The source type.

    Returns:
        The collector class or None if not found.
    """
    return _collectors.get(source_type)


def create_collector(
    source: Source,
    http_client: HttpClient | None = None,
) -> BaseCollector:
    """
    Create a collector instance for a source.

    Args:
        source: The source to create a collector for.
        http_client: HTTP client to use.

    Returns:
        A collector instance.

    Raises:
        ValueError: If no collector is registered for the source type.
    """
    collector_class = get_collector_class(source.type)

    if collector_class is None:
        raise ValueError(f"No collector registered for source type: {source.type.value}")

    return collector_class(source, http_client)


def list_registered_collectors() -> dict[str, str]:
    """
    List all registered collectors.

    Returns:
        Dictionary mapping source type to collector class name.
    """
    return {
        source_type.value: collector_class.__name__
        for source_type, collector_class in _collectors.items()
    }
