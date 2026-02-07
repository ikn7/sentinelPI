"""Tests for the Mastodon collector."""

from __future__ import annotations

import json
import pytest
from unittest.mock import AsyncMock, MagicMock

from src.collectors.mastodon import MastodonCollector
from src.collectors.base import CollectedItem, CollectorError
from src.storage.models import Source, SourceType


@pytest.fixture
def mastodon_source():
    """Create a test Mastodon source."""
    source = MagicMock(spec=Source)
    source.id = "test-mastodon-1"
    source.name = "Mastodon #test"
    source.url = "https://mastodon.social"
    source.type = SourceType.MASTODON
    config = {"type": "hashtag", "hashtag": "test", "limit": 5}
    source.config_json = json.dumps(config)
    source.config = config
    return source


@pytest.fixture
def mastodon_api_response():
    """Sample Mastodon API response."""
    return [
        {
            "id": "12345",
            "content": "<p>Hello world! #test</p>",
            "url": "https://mastodon.social/@user/12345",
            "created_at": "2026-01-15T10:00:00.000Z",
            "account": {
                "id": "111",
                "username": "testuser",
                "display_name": "Test User",
                "acct": "testuser",
            },
            "media_attachments": [],
            "tags": [{"name": "test"}],
            "reblogs_count": 5,
            "favourites_count": 10,
            "replies_count": 2,
            "sensitive": False,
            "visibility": "public",
            "language": "en",
        }
    ]


class TestMastodonCollector:
    def test_supports_source_type(self):
        assert MastodonCollector.supports_source_type() == SourceType.MASTODON

    @pytest.mark.asyncio
    async def test_collect_hashtag(self, mastodon_source, mastodon_api_response):
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.json.return_value = mastodon_api_response

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        collector = MastodonCollector(mastodon_source, http_client=mock_http)
        items = []
        async for item in collector.collect():
            items.append(item)

        assert len(items) == 1
        assert "Hello world" in items[0].title or "Hello world" in (items[0].content or "")
        assert items[0].extra.get("platform") == "mastodon"
        assert items[0].extra.get("status_id") == "12345"

        # Verify API URL
        call_args = mock_http.get.call_args
        assert "timelines/tag/test" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_collect_no_hashtag_raises(self, mastodon_source):
        config = {"type": "hashtag", "hashtag": ""}
        mastodon_source.config_json = json.dumps(config)
        mastodon_source.config = config

        mock_http = AsyncMock()
        collector = MastodonCollector(mastodon_source, http_client=mock_http)

        with pytest.raises(CollectorError):
            async for _ in collector.collect():
                pass

    @pytest.mark.asyncio
    async def test_collect_api_error(self, mastodon_source):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 500

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        collector = MastodonCollector(mastodon_source, http_client=mock_http)
        with pytest.raises(CollectorError):
            async for _ in collector.collect():
                pass
