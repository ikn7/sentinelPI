"""
Deduplication processor for SentinelPi.

Identifies and filters out duplicate items based on GUID and content hash.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors.base import CollectedItem
from src.storage.models import Item
from src.utils.config import get_settings
from src.utils.logging import create_logger

log = create_logger("processors.dedup")


class DeduplicationResult:
    """Result of deduplication processing."""

    def __init__(self) -> None:
        self.total_items: int = 0
        self.new_items: int = 0
        self.duplicate_by_guid: int = 0
        self.duplicate_by_hash: int = 0

    @property
    def duplicates(self) -> int:
        """Total number of duplicates found."""
        return self.duplicate_by_guid + self.duplicate_by_hash

    def __str__(self) -> str:
        return (
            f"Dedup: {self.total_items} total, {self.new_items} new, "
            f"{self.duplicates} duplicates (guid:{self.duplicate_by_guid}, hash:{self.duplicate_by_hash})"
        )


class Deduplicator:
    """
    Deduplication processor.

    Filters out items that have already been collected based on:
    1. GUID match (exact same item)
    2. Content hash match (same content, different source/GUID)

    Uses a configurable time window to limit the scope of deduplication checks.
    """

    def __init__(
        self,
        session: AsyncSession,
        source_id: str | None = None,
        window_days: int | None = None,
    ) -> None:
        """
        Initialize the deduplicator.

        Args:
            session: Database session for checking existing items.
            source_id: Optional source ID to scope deduplication.
            window_days: Number of days to look back for duplicates.
        """
        self.session = session
        self.source_id = source_id

        settings = get_settings()
        self.window_days = window_days or settings.collection.dedup_window_days

        # Cache for batch operations
        self._guid_cache: set[str] = set()
        self._hash_cache: set[str] = set()
        self._cache_loaded = False

    async def _load_cache(self) -> None:
        """Load existing GUIDs and hashes into memory cache."""
        if self._cache_loaded:
            return

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=self.window_days)

        # Build query for existing items
        query = select(Item.guid, Item.content_hash).where(
            Item.collected_at >= cutoff_date
        )

        if self.source_id:
            query = query.where(Item.source_id == self.source_id)

        result = await self.session.execute(query)
        rows = result.all()

        for guid, content_hash in rows:
            self._guid_cache.add(guid)
            if content_hash:
                self._hash_cache.add(content_hash)

        self._cache_loaded = True
        log.debug(
            f"Loaded dedup cache: {len(self._guid_cache)} GUIDs, "
            f"{len(self._hash_cache)} hashes"
        )

    async def is_duplicate(self, item: CollectedItem) -> tuple[bool, str | None]:
        """
        Check if an item is a duplicate.

        Args:
            item: The collected item to check.

        Returns:
            Tuple of (is_duplicate, reason).
            reason is None if not duplicate, otherwise 'guid' or 'hash'.
        """
        await self._load_cache()

        # Check GUID first (faster, more reliable)
        if item.guid in self._guid_cache:
            return True, "guid"

        # Check content hash
        content_hash = item.content_hash
        if content_hash in self._hash_cache:
            return True, "hash"

        return False, None

    async def filter_duplicates(
        self,
        items: Sequence[CollectedItem],
    ) -> tuple[list[CollectedItem], DeduplicationResult]:
        """
        Filter out duplicate items from a sequence.

        Args:
            items: Sequence of collected items.

        Returns:
            Tuple of (new_items, result).
        """
        await self._load_cache()

        result = DeduplicationResult()
        result.total_items = len(items)

        new_items: list[CollectedItem] = []
        seen_guids: set[str] = set()
        seen_hashes: set[str] = set()

        for item in items:
            # Check against database cache
            if item.guid in self._guid_cache:
                result.duplicate_by_guid += 1
                continue

            content_hash = item.content_hash
            if content_hash in self._hash_cache:
                result.duplicate_by_hash += 1
                continue

            # Check against items in this batch (prevent intra-batch duplicates)
            if item.guid in seen_guids:
                result.duplicate_by_guid += 1
                continue

            if content_hash in seen_hashes:
                result.duplicate_by_hash += 1
                continue

            # Item is new
            new_items.append(item)
            seen_guids.add(item.guid)
            seen_hashes.add(content_hash)

            # Add to cache for subsequent checks
            self._guid_cache.add(item.guid)
            self._hash_cache.add(content_hash)

        result.new_items = len(new_items)

        log.info(str(result))
        return new_items, result

    async def check_batch(
        self,
        items: Sequence[CollectedItem],
    ) -> dict[str, bool]:
        """
        Check a batch of items for duplicates.

        Args:
            items: Sequence of collected items.

        Returns:
            Dictionary mapping item GUID to is_duplicate boolean.
        """
        await self._load_cache()

        results: dict[str, bool] = {}

        for item in items:
            is_dup, _ = await self.is_duplicate(item)
            results[item.guid] = is_dup

        return results

    def mark_as_seen(self, item: CollectedItem) -> None:
        """
        Mark an item as seen (add to cache).

        Call this after successfully storing an item.

        Args:
            item: The item that was stored.
        """
        self._guid_cache.add(item.guid)
        self._hash_cache.add(item.content_hash)

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._guid_cache.clear()
        self._hash_cache.clear()
        self._cache_loaded = False


async def deduplicate_items(
    session: AsyncSession,
    items: Sequence[CollectedItem],
    source_id: str | None = None,
) -> tuple[list[CollectedItem], DeduplicationResult]:
    """
    Convenience function to deduplicate items.

    Args:
        session: Database session.
        items: Items to deduplicate.
        source_id: Optional source ID to scope deduplication.

    Returns:
        Tuple of (new_items, result).
    """
    deduplicator = Deduplicator(session, source_id=source_id)
    return await deduplicator.filter_duplicates(items)
