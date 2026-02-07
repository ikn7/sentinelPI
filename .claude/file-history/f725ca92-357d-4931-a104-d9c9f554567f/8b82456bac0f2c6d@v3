"""Tests for the deduplication processor."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.collectors.base import CollectedItem
from src.processors.dedup import Deduplicator, DeduplicationResult


class TestDeduplicationResult:
    def test_initial_counts(self):
        result = DeduplicationResult()
        assert result.total_items == 0
        assert result.new_items == 0
        assert result.duplicate_by_guid == 0
        assert result.duplicate_by_hash == 0
        assert result.duplicates == 0

    def test_duplicates_property(self):
        result = DeduplicationResult()
        result.duplicate_by_guid = 3
        result.duplicate_by_hash = 2
        assert result.duplicates == 5

    def test_str_representation(self):
        result = DeduplicationResult()
        result.total_items = 10
        result.new_items = 7
        result.duplicate_by_guid = 2
        result.duplicate_by_hash = 1
        text = str(result)
        assert "10 total" in text
        assert "7 new" in text


class TestDeduplicator:
    def test_init(self):
        mock_session = MagicMock()
        with patch("src.processors.dedup.get_settings") as mock_settings:
            mock_settings.return_value.collection.dedup_window_days = 7
            dedup = Deduplicator(session=mock_session)
            assert dedup is not None
            assert dedup.session is mock_session

    def test_content_hash_consistency(self):
        item1 = CollectedItem(guid="g1", title="Same Title", content="Same Content")
        item2 = CollectedItem(guid="g2", title="Same Title", content="Same Content")
        assert item1.content_hash == item2.content_hash

    def test_content_hash_different(self):
        item1 = CollectedItem(guid="g1", title="Title A")
        item2 = CollectedItem(guid="g2", title="Title B")
        assert item1.content_hash != item2.content_hash
