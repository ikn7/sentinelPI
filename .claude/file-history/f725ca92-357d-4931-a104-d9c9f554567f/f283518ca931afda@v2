"""
Tests for the RSS collector.
"""

from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.collectors.base import CollectedItem, CollectorError
from src.collectors.rss import RSSCollector
from src.storage.models import Source, SourceType


# Sample RSS feed for testing
SAMPLE_RSS_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:media="http://search.yahoo.com/mrss/">
  <channel>
    <title>Test Feed</title>
    <link>https://example.com</link>
    <description>A test RSS feed</description>
    <language>en</language>
    <lastBuildDate>Mon, 01 Jan 2024 12:00:00 +0000</lastBuildDate>
    <atom:link href="https://example.com/feed.xml" rel="self" type="application/rss+xml"/>

    <item>
      <title>Test Article 1</title>
      <link>https://example.com/article-1</link>
      <guid>https://example.com/article-1</guid>
      <pubDate>Mon, 01 Jan 2024 10:00:00 +0000</pubDate>
      <author>John Doe</author>
      <description><![CDATA[<p>This is the first test article.</p>]]></description>
      <category>Technology</category>
      <category>News</category>
      <media:thumbnail url="https://example.com/images/thumb1.jpg"/>
    </item>

    <item>
      <title>Test Article 2</title>
      <link>https://example.com/article-2</link>
      <guid isPermaLink="true">https://example.com/article-2</guid>
      <pubDate>Sun, 31 Dec 2023 15:30:00 +0000</pubDate>
      <description>This is the second test article with plain text.</description>
      <category>Science</category>
    </item>

    <item>
      <title>Article Without GUID</title>
      <link>https://example.com/article-3</link>
      <pubDate>Sat, 30 Dec 2023 08:00:00 +0000</pubDate>
      <description>An article without an explicit GUID.</description>
    </item>
  </channel>
</rss>
"""

SAMPLE_ATOM_FEED = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Test Atom Feed</title>
  <link href="https://example.com"/>
  <link href="https://example.com/feed.atom" rel="self"/>
  <id>urn:uuid:test-feed-id</id>
  <updated>2024-01-01T12:00:00Z</updated>

  <entry>
    <title>Atom Entry 1</title>
    <link href="https://example.com/entry-1"/>
    <id>urn:uuid:entry-1-id</id>
    <published>2024-01-01T10:00:00Z</published>
    <updated>2024-01-01T11:00:00Z</updated>
    <author>
      <name>Jane Smith</name>
    </author>
    <content type="html"><![CDATA[<p>Full content of entry 1.</p>]]></content>
    <summary>Summary of entry 1.</summary>
  </entry>
</feed>
"""


@pytest.fixture
def mock_source():
    """Create a mock Source object."""
    source = MagicMock(spec=Source)
    source.id = "test-source-id"
    source.name = "Test RSS Feed"
    source.type = SourceType.RSS
    source.url = "https://example.com/feed.xml"
    source.config = {}
    return source


@pytest.fixture
def mock_http_client():
    """Create a mock HTTP client."""
    client = AsyncMock()
    return client


class TestRSSCollector:
    """Tests for RSSCollector."""

    def test_supports_source_type(self):
        """Test that collector supports RSS source type."""
        assert RSSCollector.supports_source_type() == SourceType.RSS

    @pytest.mark.asyncio
    async def test_collect_rss_feed(self, mock_source, mock_http_client):
        """Test collecting from a standard RSS 2.0 feed."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = SAMPLE_RSS_FEED
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Create collector and collect
        collector = RSSCollector(mock_source, mock_http_client)
        items = []
        async for item in collector.collect():
            items.append(item)

        # Verify
        assert len(items) == 3

        # Check first item
        assert items[0].title == "Test Article 1"
        assert items[0].url == "https://example.com/article-1"
        assert items[0].guid == "https://example.com/article-1"
        assert items[0].author == "John Doe"
        assert items[0].published_at is not None
        assert items[0].image_url == "https://example.com/images/thumb1.jpg"

        # Check that content was extracted
        assert "first test article" in items[0].content.lower()

        # Check tags in extra
        assert "Technology" in items[0].extra.get("tags", [])

    @pytest.mark.asyncio
    async def test_collect_atom_feed(self, mock_source, mock_http_client):
        """Test collecting from an Atom feed."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = SAMPLE_ATOM_FEED
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Create collector and collect
        collector = RSSCollector(mock_source, mock_http_client)
        items = []
        async for item in collector.collect():
            items.append(item)

        # Verify
        assert len(items) == 1

        item = items[0]
        assert item.title == "Atom Entry 1"
        assert item.url == "https://example.com/entry-1"
        assert item.author == "Jane Smith"
        assert item.summary == "Summary of entry 1."
        assert "Full content" in item.content

    @pytest.mark.asyncio
    async def test_collect_http_error(self, mock_source, mock_http_client):
        """Test handling of HTTP errors."""
        # Setup mock response with error
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Create collector
        collector = RSSCollector(mock_source, mock_http_client)

        # Should raise CollectorError
        with pytest.raises(CollectorError) as exc_info:
            async for _ in collector.collect():
                pass

        assert "HTTP 404" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_collect_with_max_items(self, mock_source, mock_http_client):
        """Test max_items configuration."""
        # Setup
        mock_source.config = {"max_items": 2}
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = SAMPLE_RSS_FEED
        mock_http_client.get = AsyncMock(return_value=mock_response)

        # Collect
        collector = RSSCollector(mock_source, mock_http_client)
        items = []
        async for item in collector.collect():
            items.append(item)

        # Should only get 2 items
        assert len(items) == 2

    @pytest.mark.asyncio
    async def test_collect_with_strip_html(self, mock_source, mock_http_client):
        """Test strip_html configuration."""
        mock_source.config = {"strip_html": True}
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = SAMPLE_RSS_FEED
        mock_http_client.get = AsyncMock(return_value=mock_response)

        collector = RSSCollector(mock_source, mock_http_client)
        items = []
        async for item in collector.collect():
            items.append(item)

        # Content should not contain HTML tags
        assert "<p>" not in (items[0].content or "")

    def test_collected_item_hash(self):
        """Test that CollectedItem generates consistent hashes."""
        item1 = CollectedItem(
            guid="test-guid",
            title="Test Title",
            content="Test content",
        )

        item2 = CollectedItem(
            guid="different-guid",
            title="Test Title",
            content="Test content",
        )

        # Same content should have same hash
        assert item1.content_hash == item2.content_hash

        item3 = CollectedItem(
            guid="test-guid",
            title="Different Title",
            content="Different content",
        )

        # Different content should have different hash
        assert item1.content_hash != item3.content_hash

    @pytest.mark.asyncio
    async def test_run_returns_result(self, mock_source, mock_http_client):
        """Test that run() returns a CollectionResult."""
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.text = SAMPLE_RSS_FEED
        mock_http_client.get = AsyncMock(return_value=mock_response)

        collector = RSSCollector(mock_source, mock_http_client)
        result = await collector.run()

        assert result.success is True
        assert result.items_collected == 3
        assert result.source_id == mock_source.id
        assert result.source_name == mock_source.name
        assert result.duration_ms > 0
        assert result.error is None

    @pytest.mark.asyncio
    async def test_run_handles_error(self, mock_source, mock_http_client):
        """Test that run() handles errors gracefully."""
        mock_http_client.get = AsyncMock(side_effect=Exception("Network error"))

        collector = RSSCollector(mock_source, mock_http_client)
        result = await collector.run()

        assert result.success is False
        assert "Network error" in result.error
        assert result.items_collected == 0
