"""
Reddit collector for SentinelPi.

Uses Reddit's RSS feeds for public subreddit access without API authentication.
"""

from __future__ import annotations

import re
from typing import AsyncIterator
from urllib.parse import urlencode, urlparse

from src.collectors.base import (
    BaseCollector,
    CollectedItem,
    CollectorError,
    register_collector,
)
from src.collectors.rss import RSSCollector
from src.storage.models import SourceType
from src.utils.logging import create_logger

log = create_logger("collectors.reddit")


@register_collector
class RedditCollector(BaseCollector):
    """
    Collector for Reddit subreddits.

    Uses Reddit's public RSS feeds which don't require authentication.
    For each subreddit, the collector fetches the RSS feed and parses it.

    Configuration options (in source.config):
    - sort: Sorting method - hot, new, top, rising (default: hot)
    - limit: Number of posts to fetch, max 100 (default: 25)
    - time: Time filter for 'top' sort - hour, day, week, month, year, all (default: day)
    - max_items: Maximum items to process (default: 100)

    Source URL should be:
    - https://www.reddit.com/r/subreddit
    - https://reddit.com/r/subreddit
    - r/subreddit (will be expanded)
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.REDDIT

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """
        Collect posts from the Reddit subreddit.

        Yields:
            CollectedItem objects for each post.
        """
        # Build RSS URL
        rss_url = self._build_rss_url()

        self.log.debug(f"Fetching Reddit RSS: {rss_url}")

        # Fetch the feed with Reddit-specific headers
        try:
            # Reddit requires a descriptive User-Agent
            headers = {
                "User-Agent": "SentinelPi/1.0 (RSS Reader; +https://github.com/sentinelpi)"
            }
            response = await self.http.get(rss_url, headers=headers)

            if not response.ok:
                raise CollectorError(
                    f"Failed to fetch Reddit feed: HTTP {response.status_code}",
                    source_id=self.source.id,
                )

        except Exception as e:
            raise CollectorError(
                f"Failed to fetch Reddit feed: {e}",
                source_id=self.source.id,
                cause=e if isinstance(e, Exception) else None,
            )

        # Parse using feedparser
        import feedparser

        feed = feedparser.parse(response.text)

        if feed.bozo and not feed.entries:
            raise CollectorError(
                f"Failed to parse Reddit feed",
                source_id=self.source.id,
            )

        max_items = self.get_config("max_items", 100)

        for entry in feed.entries[:max_items]:
            try:
                item = self._parse_entry(entry)
                yield item
            except Exception as e:
                self.log.warning(f"Failed to parse Reddit entry: {e}")
                continue

    def _build_rss_url(self) -> str:
        """Build the Reddit RSS URL from source configuration."""
        url = self.source.url

        # Extract subreddit name
        subreddit = self._extract_subreddit(url)

        if not subreddit:
            raise CollectorError(
                f"Could not extract subreddit from URL: {url}",
                source_id=self.source.id,
            )

        # Get configuration
        sort = self.get_config("sort", "hot")
        limit = min(self.get_config("limit", 25), 100)
        time_filter = self.get_config("time", "day")

        # Build RSS URL
        base_url = f"https://www.reddit.com/r/{subreddit}/{sort}.rss"

        params = {"limit": limit}
        if sort == "top":
            params["t"] = time_filter

        return f"{base_url}?{urlencode(params)}"

    def _extract_subreddit(self, url: str) -> str | None:
        """Extract subreddit name from URL."""
        # Handle short form: r/subreddit
        if url.startswith("r/"):
            return url[2:].split("/")[0]

        # Handle full URL
        parsed = urlparse(url)
        path = parsed.path

        # Match /r/subreddit or /r/subreddit/...
        match = re.match(r"/r/([^/]+)", path)
        if match:
            return match.group(1)

        return None

    def _parse_entry(self, entry) -> CollectedItem:
        """Parse a Reddit feed entry into a CollectedItem."""
        # Extract GUID
        guid = entry.get("id") or entry.get("link", "")

        # Extract title (remove subreddit prefix if present)
        title = entry.get("title", "Sans titre")

        # Extract URL (Reddit post link)
        url = entry.get("link")

        # Extract author (u/username format in feed)
        author = entry.get("author", "").replace("/u/", "u/")
        if author.startswith("u/"):
            author = author[2:]

        # Extract content (Reddit provides HTML in content)
        content = None
        summary = None

        content_list = entry.get("content", [])
        if content_list:
            content = content_list[0].get("value", "")

        # Reddit summary often contains useful preview
        if entry.get("summary"):
            summary = entry.get("summary")

        # Extract date
        from src.utils.dates import parse_rss_date

        published_at = None
        if entry.get("published"):
            published_at = parse_rss_date(entry.get("published"))
        elif entry.get("updated"):
            published_at = parse_rss_date(entry.get("updated"))

        # Try to extract thumbnail/image
        image_url = None
        media_urls = []

        # Check for media:thumbnail
        if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
            image_url = entry.media_thumbnail[0].get("url")

        # Check for media:content
        if hasattr(entry, "media_content"):
            for media in entry.media_content:
                media_url = media.get("url")
                if media_url:
                    media_urls.append(media_url)
                    if not image_url and media.get("medium") == "image":
                        image_url = media_url

        # Extract category (subreddit)
        categories = []
        if hasattr(entry, "tags"):
            categories = [tag.get("term") for tag in entry.tags if tag.get("term")]

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
                "platform": "reddit",
                "categories": categories,
            },
        )
