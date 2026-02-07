"""Tests for the YouTube collector."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collectors.youtube import YouTubeCollector
from src.collectors.base import CollectedItem, CollectorError
from src.storage.models import Source, SourceType


@pytest.fixture
def youtube_source():
    """Create a test YouTube source."""
    source = MagicMock(spec=Source)
    source.id = "test-yt-1"
    source.name = "Test YouTube"
    source.url = "https://www.youtube.com/feeds/videos.xml?channel_id=UCtest123"
    source.type = SourceType.YOUTUBE
    source.config_json = '{"max_items": 5}'
    return source


class TestYouTubeCollector:
    def test_supports_source_type(self):
        assert YouTubeCollector.supports_source_type() == SourceType.YOUTUBE

    def test_extract_channel_id_from_rss_url(self, youtube_source):
        collector = YouTubeCollector(youtube_source)
        channel_id = collector._extract_channel_id(
            "https://www.youtube.com/feeds/videos.xml?channel_id=UCtest123"
        )
        assert channel_id == "UCtest123"

    def test_extract_channel_id_from_channel_url(self, youtube_source):
        collector = YouTubeCollector(youtube_source)
        channel_id = collector._extract_channel_id(
            "https://www.youtube.com/channel/UCtest123"
        )
        assert channel_id == "UCtest123"

    def test_extract_channel_id_returns_none_for_handle(self, youtube_source):
        collector = YouTubeCollector(youtube_source)
        channel_id = collector._extract_channel_id(
            "https://www.youtube.com/@testchannel"
        )
        assert channel_id is None

    @pytest.mark.asyncio
    async def test_collect_parses_feed(self, youtube_source):
        atom_xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom"
              xmlns:yt="http://www.youtube.com/xml/schemas/2015">
            <title>Test Channel</title>
            <link rel="alternate" href="https://www.youtube.com/channel/UCtest123"/>
            <entry>
                <id>yt:video:abc123</id>
                <yt:videoId>abc123</yt:videoId>
                <title>Test Video</title>
                <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
                <author><name>Test Channel</name></author>
                <published>2026-01-01T00:00:00+00:00</published>
                <summary>Video description</summary>
            </entry>
        </feed>
        """
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = atom_xml

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        collector = YouTubeCollector(youtube_source, http_client=mock_http)
        items = []
        async for item in collector.collect():
            items.append(item)

        assert len(items) == 1
        assert items[0].title == "Test Video"
        assert items[0].extra.get("platform") == "youtube"
