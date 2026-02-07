"""
Tests for OPML import/export functionality.
"""

from __future__ import annotations

import pytest
from src.utils.opml import (
    export_sources_to_opml,
    parse_opml,
    OPMLDocument,
    OPMLOutline,
)


class MockSource:
    """Mock Source model for testing."""

    def __init__(self, name: str, url: str, category: str | None = None):
        self.name = name
        self.url = url
        self.category = category
        self.config = {}

        class MockType:
            value = "rss"

        self.type = MockType()


class TestOPMLExport:
    """Tests for OPML export functionality."""

    def test_export_empty_sources(self):
        """Test exporting empty source list."""
        result = export_sources_to_opml([])
        assert '<?xml version="1.0"' in result
        assert '<opml version="2.0">' in result
        assert '<body>' in result

    def test_export_single_source(self):
        """Test exporting a single RSS source."""
        sources = [MockSource("Test Feed", "https://example.com/feed.xml")]
        result = export_sources_to_opml(sources)

        assert "Test Feed" in result
        assert "https://example.com/feed.xml" in result
        assert 'type="rss"' in result

    def test_export_with_categories(self):
        """Test exporting sources grouped by category."""
        sources = [
            MockSource("Feed 1", "https://example.com/1.xml", "tech"),
            MockSource("Feed 2", "https://example.com/2.xml", "tech"),
            MockSource("Feed 3", "https://example.com/3.xml", "news"),
        ]
        result = export_sources_to_opml(sources, group_by_category=True)

        # Should have category folders
        assert 'text="tech"' in result
        assert 'text="news"' in result

    def test_export_without_categories(self):
        """Test exporting sources without grouping."""
        sources = [
            MockSource("Feed 1", "https://example.com/1.xml", "tech"),
            MockSource("Feed 2", "https://example.com/2.xml", "news"),
        ]
        result = export_sources_to_opml(sources, group_by_category=False)

        # Should be flat list
        assert "Feed 1" in result
        assert "Feed 2" in result


class TestOPMLParse:
    """Tests for OPML parsing functionality."""

    def test_parse_simple_opml(self):
        """Test parsing a simple OPML document."""
        opml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head>
                <title>My Feeds</title>
            </head>
            <body>
                <outline text="Tech Feed" title="Tech Feed" type="rss"
                         xmlUrl="https://example.com/feed.xml"/>
            </body>
        </opml>
        """
        doc = parse_opml(opml_content)

        assert doc.title == "My Feeds"
        assert len(doc.outlines) == 1
        assert doc.outlines[0].text == "Tech Feed"
        assert doc.outlines[0].xml_url == "https://example.com/feed.xml"
        assert doc.outlines[0].is_feed

    def test_parse_opml_with_folders(self):
        """Test parsing OPML with folder structure."""
        opml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head>
                <title>My Feeds</title>
            </head>
            <body>
                <outline text="Tech" title="Tech">
                    <outline text="Feed 1" type="rss" xmlUrl="https://example.com/1.xml"/>
                    <outline text="Feed 2" type="rss" xmlUrl="https://example.com/2.xml"/>
                </outline>
                <outline text="News" title="News">
                    <outline text="Feed 3" type="rss" xmlUrl="https://example.com/3.xml"/>
                </outline>
            </body>
        </opml>
        """
        doc = parse_opml(opml_content)

        assert len(doc.outlines) == 2
        assert doc.outlines[0].is_folder
        assert len(doc.outlines[0].children) == 2
        assert doc.outlines[1].is_folder
        assert len(doc.outlines[1].children) == 1

    def test_get_all_feeds(self):
        """Test extracting all feeds from nested structure."""
        opml_content = """<?xml version="1.0" encoding="UTF-8"?>
        <opml version="2.0">
            <head><title>Test</title></head>
            <body>
                <outline text="Category">
                    <outline text="Feed 1" type="rss" xmlUrl="https://example.com/1.xml"/>
                </outline>
                <outline text="Feed 2" type="rss" xmlUrl="https://example.com/2.xml"/>
            </body>
        </opml>
        """
        doc = parse_opml(opml_content)
        feeds = doc.get_all_feeds()

        assert len(feeds) == 2
        # First feed should inherit category from parent folder
        assert feeds[0].category == "Category"
        # Second feed is at root level
        assert feeds[1].xml_url == "https://example.com/2.xml"

    def test_parse_invalid_xml(self):
        """Test parsing invalid XML raises error."""
        with pytest.raises(ValueError, match="Invalid XML"):
            parse_opml("not valid xml")

    def test_parse_non_opml(self):
        """Test parsing non-OPML XML raises error."""
        with pytest.raises(ValueError, match="Root element must be 'opml'"):
            parse_opml("<html><body>Not OPML</body></html>")


class TestOPMLRoundtrip:
    """Test export then import preserves data."""

    def test_roundtrip(self):
        """Test that export then import preserves feed data."""
        sources = [
            MockSource("Feed A", "https://a.com/feed.xml", "tech"),
            MockSource("Feed B", "https://b.com/rss", "news"),
            MockSource("Feed C", "https://c.com/atom.xml"),
        ]

        # Export
        opml_str = export_sources_to_opml(sources, group_by_category=True)

        # Parse back
        doc = parse_opml(opml_str)
        feeds = doc.get_all_feeds()

        # Verify
        assert len(feeds) == 3
        feed_urls = {f.xml_url for f in feeds}
        assert "https://a.com/feed.xml" in feed_urls
        assert "https://b.com/rss" in feed_urls
        assert "https://c.com/atom.xml" in feed_urls
