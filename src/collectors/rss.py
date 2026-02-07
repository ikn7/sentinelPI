"""
RSS/Atom feed collector for SentinelPi.

Supports RSS 2.0, RSS 1.0, Atom, and common variations.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, AsyncIterator
from urllib.parse import urljoin, urlparse

import feedparser

from src.collectors.base import (
    BaseCollector,
    CollectedItem,
    CollectorError,
    register_collector,
)
from src.storage.models import SourceType
from src.utils.dates import parse_rss_date
from src.utils.logging import create_logger
from src.utils.parsing import clean_html, extract_text, parse_html

log = create_logger("collectors.rss")


@register_collector
class RSSCollector(BaseCollector):
    """
    Collector for RSS and Atom feeds.

    Supports:
    - RSS 2.0
    - RSS 1.0 (RDF)
    - Atom 1.0
    - Media RSS extensions
    - Dublin Core metadata

    Configuration options (in source.config):
    - max_items: Maximum number of items to collect (default: 100)
    - include_content: Whether to include full content (default: True)
    - strip_html: Whether to strip HTML from content (default: False)
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.RSS

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """
        Collect items from the RSS/Atom feed.

        Yields:
            CollectedItem objects for each feed entry.
        """
        # Fetch the feed
        try:
            response = await self.http.get(self.source.url)

            if not response.ok:
                raise CollectorError(
                    f"Failed to fetch feed: HTTP {response.status_code}",
                    source_id=self.source.id,
                )

            feed_content = response.text

        except Exception as e:
            raise CollectorError(
                f"Failed to fetch feed: {e}",
                source_id=self.source.id,
                cause=e if isinstance(e, Exception) else None,
            )

        # Parse the feed
        feed = feedparser.parse(feed_content)

        if feed.bozo and not feed.entries:
            # Feed has errors and no entries
            error_msg = str(feed.bozo_exception) if hasattr(feed, "bozo_exception") else "Unknown parse error"
            raise CollectorError(
                f"Failed to parse feed: {error_msg}",
                source_id=self.source.id,
            )

        # Get configuration
        max_items = self.get_config("max_items", 100)
        include_content = self.get_config("include_content", True)
        strip_html = self.get_config("strip_html", False)

        # Get feed metadata for fallbacks
        feed_title = feed.feed.get("title", "")
        feed_link = feed.feed.get("link", self.source.url)

        self.log.debug(
            f"Parsed feed: {feed_title} ({len(feed.entries)} entries)"
        )

        # Process entries
        for i, entry in enumerate(feed.entries[:max_items]):
            try:
                item = self._parse_entry(
                    entry,
                    feed_link=feed_link,
                    include_content=include_content,
                    strip_html=strip_html,
                )
                yield item

            except Exception as e:
                self.log.warning(
                    f"Failed to parse entry {i}: {e}"
                )
                continue

    def _parse_entry(
        self,
        entry: Any,
        feed_link: str,
        include_content: bool,
        strip_html: bool,
    ) -> CollectedItem:
        """
        Parse a feed entry into a CollectedItem.

        Args:
            entry: feedparser entry object.
            feed_link: Base URL of the feed.
            include_content: Whether to include content.
            strip_html: Whether to strip HTML from content.

        Returns:
            CollectedItem object.
        """
        # Extract GUID (unique identifier)
        guid = self._extract_guid(entry)

        # Extract title
        title = entry.get("title", "Sans titre")
        if strip_html:
            title = clean_html(title)

        # Extract URL
        url = self._extract_link(entry, feed_link)

        # Extract author
        author = self._extract_author(entry)

        # Extract content
        content = None
        summary = None

        if include_content:
            content = self._extract_content(entry, strip_html)
            summary = self._extract_summary(entry, strip_html)

            # If no summary, create one from content
            if not summary and content:
                summary = content[:500] + "..." if len(content) > 500 else content

        # Extract date
        published_at = self._extract_date(entry)

        # Extract media
        image_url = self._extract_image(entry)
        media_urls = self._extract_media(entry)

        # Extract language
        language = entry.get("language") or entry.get("dc_language")

        return CollectedItem(
            guid=guid,
            title=title,
            url=url,
            author=author,
            content=content,
            summary=summary,
            published_at=published_at,
            image_url=image_url,
            media_urls=media_urls,
            language=language,
            extra={
                "feed_entry_id": entry.get("id"),
                "tags": self._extract_tags(entry),
            },
        )

    def _extract_guid(self, entry: Any) -> str:
        """Extract or generate a unique identifier for the entry."""
        # Try standard fields
        guid = entry.get("id") or entry.get("guid") or entry.get("link")

        if guid:
            return str(guid)

        # Generate from title + link
        title = entry.get("title", "")
        link = entry.get("link", "")
        unique_str = f"{title}:{link}"

        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]

    def _extract_link(self, entry: Any, feed_link: str) -> str | None:
        """Extract the entry link."""
        # Try standard link field
        link = entry.get("link")

        if link:
            # Resolve relative URLs
            if not urlparse(link).netloc:
                link = urljoin(feed_link, link)
            return link

        # Try links array (Atom)
        links = entry.get("links", [])
        for link_obj in links:
            if link_obj.get("rel") in ("alternate", None):
                href = link_obj.get("href")
                if href:
                    if not urlparse(href).netloc:
                        href = urljoin(feed_link, href)
                    return href

        return None

    def _extract_author(self, entry: Any) -> str | None:
        """Extract the author name."""
        # Try standard author field
        author = entry.get("author")
        if author:
            return author

        # Try author_detail (Atom)
        author_detail = entry.get("author_detail")
        if author_detail:
            return author_detail.get("name")

        # Try authors array
        authors = entry.get("authors", [])
        if authors:
            names = [a.get("name") for a in authors if a.get("name")]
            if names:
                return ", ".join(names)

        # Try Dublin Core creator
        return entry.get("dc_creator")

    def _extract_content(self, entry: Any, strip_html: bool) -> str | None:
        """Extract the full content."""
        # Try content array (preferred, usually full content)
        content_list = entry.get("content", [])
        if content_list:
            # Prefer HTML content
            for content_obj in content_list:
                if content_obj.get("type") in ("text/html", "html"):
                    value = content_obj.get("value", "")
                    return clean_html(value) if strip_html else value

            # Fall back to first content
            value = content_list[0].get("value", "")
            return clean_html(value) if strip_html else value

        # Try summary (RSS description)
        summary = entry.get("summary")
        if summary:
            return clean_html(summary) if strip_html else summary

        # Try description
        description = entry.get("description")
        if description:
            return clean_html(description) if strip_html else description

        return None

    def _extract_summary(self, entry: Any, strip_html: bool) -> str | None:
        """Extract a summary/description."""
        # Try summary field
        summary = entry.get("summary")
        if summary:
            text = clean_html(summary) if strip_html else summary
            # Limit summary length
            if len(text) > 1000:
                text = text[:1000] + "..."
            return text

        # Try description
        description = entry.get("description")
        if description:
            text = clean_html(description) if strip_html else description
            if len(text) > 1000:
                text = text[:1000] + "..."
            return text

        return None

    def _extract_date(self, entry: Any) -> datetime | None:
        """Extract the publication date."""
        # Try various date fields
        date_fields = [
            "published",
            "pubDate",
            "updated",
            "created",
            "dc_date",
            "date",
        ]

        for field in date_fields:
            date_str = entry.get(field)
            if date_str:
                parsed = parse_rss_date(date_str)
                if parsed:
                    return parsed

        # Try parsed versions (feedparser normalizes these)
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            from datetime import timezone
            import time
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)

        if hasattr(entry, "updated_parsed") and entry.updated_parsed:
            from datetime import timezone
            return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

        return None

    def _extract_image(self, entry: Any) -> str | None:
        """Extract the main image URL."""
        # Try media:thumbnail
        media_thumbnail = entry.get("media_thumbnail", [])
        if media_thumbnail:
            return media_thumbnail[0].get("url")

        # Try media:content with image type
        media_content = entry.get("media_content", [])
        for media in media_content:
            medium = media.get("medium")
            url = media.get("url")
            if medium == "image" and url:
                return url

        # Try enclosures
        enclosures = entry.get("enclosures", [])
        for enclosure in enclosures:
            enc_type = enclosure.get("type", "")
            if enc_type.startswith("image/"):
                return enclosure.get("url")

        # Try to find image in content
        content = entry.get("summary") or entry.get("description", "")
        if content and "<img" in content:
            soup = parse_html(content, parser="html.parser")
            img = soup.find("img", src=True)
            if img:
                return img["src"]

        return None

    def _extract_media(self, entry: Any) -> list[str]:
        """Extract all media URLs."""
        media_urls = []

        # Media content
        media_content = entry.get("media_content", [])
        for media in media_content:
            url = media.get("url")
            if url:
                media_urls.append(url)

        # Enclosures
        enclosures = entry.get("enclosures", [])
        for enclosure in enclosures:
            url = enclosure.get("url")
            if url:
                media_urls.append(url)

        return list(set(media_urls))  # Remove duplicates

    def _extract_tags(self, entry: Any) -> list[str]:
        """Extract tags/categories."""
        tags = []

        # Tags array
        tag_list = entry.get("tags", [])
        for tag in tag_list:
            term = tag.get("term")
            if term:
                tags.append(term)

        # Categories
        categories = entry.get("categories", [])
        if isinstance(categories, list):
            for cat in categories:
                if isinstance(cat, str):
                    tags.append(cat)
                elif isinstance(cat, dict):
                    term = cat.get("term")
                    if term:
                        tags.append(term)

        return list(set(tags))  # Remove duplicates
