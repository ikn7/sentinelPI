"""
YouTube collector for SentinelPi.

Uses YouTube's public RSS feeds for channel videos.
"""

from __future__ import annotations

import re
from typing import AsyncIterator
from urllib.parse import parse_qs, urlparse

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

log = create_logger("collectors.youtube")


@register_collector
class YouTubeCollector(BaseCollector):
    """
    Collector for YouTube channel videos.

    Uses YouTube's public RSS feeds which don't require API authentication.

    Source URL formats:
    - https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID
    - https://www.youtube.com/channel/CHANNEL_ID
    - https://www.youtube.com/@handle
    - https://www.youtube.com/c/channel_name
    - Direct RSS URL

    Configuration options (in source.config):
    - max_items: Maximum items to process (default: 50)
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.YOUTUBE

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """
        Collect videos from the YouTube channel.

        Yields:
            CollectedItem objects for each video.
        """
        # Build RSS URL
        rss_url = await self._get_rss_url()

        self.log.debug(f"Fetching YouTube RSS: {rss_url}")

        # Fetch the feed
        try:
            response = await self.http.get(rss_url)

            if not response.ok:
                raise CollectorError(
                    f"Failed to fetch YouTube feed: HTTP {response.status_code}",
                    source_id=self.source.id,
                )

        except Exception as e:
            raise CollectorError(
                f"Failed to fetch YouTube feed: {e}",
                source_id=self.source.id,
                cause=e if isinstance(e, Exception) else None,
            )

        # Parse the feed
        feed = feedparser.parse(response.text)

        if feed.bozo and not feed.entries:
            raise CollectorError(
                f"Failed to parse YouTube feed",
                source_id=self.source.id,
            )

        max_items = self.get_config("max_items", 50)

        # Get channel info
        channel_name = feed.feed.get("title", "")
        channel_url = feed.feed.get("link", "")

        self.log.debug(f"YouTube channel: {channel_name} ({len(feed.entries)} videos)")

        for entry in feed.entries[:max_items]:
            try:
                item = self._parse_entry(entry, channel_name, channel_url)
                yield item
            except Exception as e:
                self.log.warning(f"Failed to parse YouTube entry: {e}")
                continue

    async def _get_rss_url(self) -> str:
        """Get the RSS URL for the YouTube channel."""
        url = self.source.url

        # Already an RSS URL
        if "feeds/videos.xml" in url:
            return url

        # Extract channel ID from URL
        channel_id = self._extract_channel_id(url)

        if channel_id:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        # For @handle or /c/ URLs, we need to fetch the page to get the channel ID
        channel_id = await self._resolve_channel_id(url)

        if channel_id:
            return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

        raise CollectorError(
            f"Could not determine YouTube channel ID from URL: {url}",
            source_id=self.source.id,
        )

    def _extract_channel_id(self, url: str) -> str | None:
        """Extract channel ID from URL if directly available."""
        parsed = urlparse(url)

        # RSS URL with channel_id parameter
        if "channel_id" in parsed.query:
            params = parse_qs(parsed.query)
            channel_ids = params.get("channel_id", [])
            if channel_ids:
                return channel_ids[0]

        # /channel/CHANNEL_ID format
        match = re.match(r"/channel/([a-zA-Z0-9_-]+)", parsed.path)
        if match:
            return match.group(1)

        return None

    async def _resolve_channel_id(self, url: str) -> str | None:
        """Resolve channel ID by fetching the channel page."""
        try:
            response = await self.http.get(url)

            if not response.ok:
                return None

            # Look for channel ID in the page
            # YouTube embeds it in various places

            # Try meta tag
            match = re.search(
                r'<meta\s+itemprop="channelId"\s+content="([^"]+)"',
                response.text,
            )
            if match:
                return match.group(1)

            # Try canonical URL
            match = re.search(
                r'<link\s+rel="canonical"\s+href="https://www\.youtube\.com/channel/([^"]+)"',
                response.text,
            )
            if match:
                return match.group(1)

            # Try browse ID in JSON
            match = re.search(r'"browseId":"(UC[a-zA-Z0-9_-]+)"', response.text)
            if match:
                return match.group(1)

            return None

        except Exception as e:
            self.log.warning(f"Failed to resolve channel ID: {e}")
            return None

    def _parse_entry(
        self,
        entry,
        channel_name: str,
        channel_url: str,
    ) -> CollectedItem:
        """Parse a YouTube feed entry into a CollectedItem."""
        # Extract video ID
        video_id = entry.get("yt_videoid", "")

        # GUID
        guid = entry.get("id") or f"youtube:{video_id}"

        # Title
        title = entry.get("title", "Sans titre")

        # URL
        url = entry.get("link") or f"https://www.youtube.com/watch?v={video_id}"

        # Author (channel name)
        author = entry.get("author", channel_name)

        # Description/summary
        content = None
        summary = None

        if entry.get("summary"):
            content = entry.get("summary")
            # Create a shorter summary
            if len(content) > 500:
                summary = content[:500] + "..."
            else:
                summary = content

        # Publication date
        published_at = None
        if entry.get("published"):
            published_at = parse_rss_date(entry.get("published"))

        # Thumbnail
        image_url = None
        media_urls = []

        # YouTube provides thumbnails via media:group/media:thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            thumbnails = entry.media_thumbnail
            # Get the highest quality thumbnail
            if thumbnails:
                image_url = thumbnails[-1].get("url")  # Last is usually highest quality

        # Also add standard YouTube thumbnail URLs
        if video_id:
            # Standard thumbnail URLs
            media_urls.extend([
                f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg",
                f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg",
            ])
            if not image_url:
                image_url = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

        # Video URL as media
        if video_id:
            media_urls.append(f"https://www.youtube.com/watch?v={video_id}")

        # Views count (if available)
        views = None
        if hasattr(entry, "media_statistics"):
            views = entry.media_statistics.get("views")

        # Duration (if available in media:content)
        duration = None
        if hasattr(entry, "media_content") and entry.media_content:
            for media in entry.media_content:
                if media.get("duration"):
                    duration = int(media.get("duration"))
                    break

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
            extra={
                "platform": "youtube",
                "video_id": video_id,
                "channel_name": channel_name,
                "channel_url": channel_url,
                "views": views,
                "duration_seconds": duration,
            },
        )
