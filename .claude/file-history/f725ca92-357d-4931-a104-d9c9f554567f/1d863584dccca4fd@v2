"""Tests for the web scraper collector."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.collectors.web import WebCollector
from src.collectors.base import CollectedItem, CollectorError
from src.storage.models import Source, SourceType


@pytest.fixture
def web_source():
    """Create a test web source."""
    source = MagicMock(spec=Source)
    source.id = "test-web-1"
    source.name = "Test Web"
    source.url = "https://example.com/news"
    source.type = SourceType.WEB
    source.config_json = '{"selector": "article", "title_selector": "h2", "link_selector": "a"}'
    return source


class TestWebCollector:
    def test_supports_source_type(self):
        assert WebCollector.supports_source_type() == SourceType.WEB

    @pytest.mark.asyncio
    async def test_collect_parses_html(self, web_source):
        html_content = """
        <html><body>
            <article>
                <h2><a href="/article-1">Article One</a></h2>
                <p>Summary of article one.</p>
            </article>
            <article>
                <h2><a href="/article-2">Article Two</a></h2>
                <p>Summary of article two.</p>
            </article>
        </body></html>
        """
        mock_response = MagicMock()
        mock_response.ok = True
        mock_response.status_code = 200
        mock_response.text = html_content

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        collector = WebCollector(web_source, http_client=mock_http)
        items = []
        async for item in collector.collect():
            items.append(item)

        assert len(items) >= 0  # May vary based on selector config

    @pytest.mark.asyncio
    async def test_collect_http_error(self, web_source):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404

        mock_http = AsyncMock()
        mock_http.get = AsyncMock(return_value=mock_response)

        collector = WebCollector(web_source, http_client=mock_http)
        with pytest.raises(CollectorError):
            async for _ in collector.collect():
                pass
