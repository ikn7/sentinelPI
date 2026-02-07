"""
Custom collector for SentinelPi.

Generic collector for arbitrary JSON APIs and custom data sources.
"""

from __future__ import annotations

import hashlib
from typing import Any, AsyncIterator

from src.collectors.base import (
    BaseCollector,
    CollectedItem,
    CollectorError,
    register_collector,
)
from src.storage.models import SourceType
from src.utils.dates import parse_date
from src.utils.logging import create_logger
from src.utils.parsing import clean_html

log = create_logger("collectors.custom")


@register_collector
class CustomCollector(BaseCollector):
    """
    Generic collector for custom JSON APIs.

    Fetches a JSON endpoint and maps fields to CollectedItem using
    configurable JSON path mappings.

    Configuration options (in source.config):
    - method: HTTP method (default: GET)
    - headers: Dict of additional HTTP headers
    - body: Request body for POST requests (dict)
    - auth_token: Bearer token for Authorization header
    - api_key: API key (sent as X-API-Key header)
    - items_path: JSON path to the items list (default: "" = root is list)
    - mapping: Dict mapping CollectedItem fields to JSON keys
      - guid: JSON key for unique ID (default: "id")
      - title: JSON key for title (default: "title")
      - url: JSON key for URL (default: "url" or "link")
      - author: JSON key for author (default: "author")
      - content: JSON key for content (default: "content" or "body" or "text")
      - summary: JSON key for summary (default: "summary" or "description" or "excerpt")
      - published_at: JSON key for date (default: "published_at" or "date" or "created_at")
      - image_url: JSON key for image (default: "image_url" or "image" or "thumbnail")
    - max_items: Maximum items to process (default: 100)
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.CUSTOM

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """Collect items from the custom API."""
        method = self.get_config("method", "GET").upper()
        headers = self.get_config("headers", {})
        body = self.get_config("body")
        auth_token = self.get_config("auth_token")
        api_key = self.get_config("api_key")
        items_path = self.get_config("items_path", "")
        mapping = self.get_config("mapping", {})
        max_items = self.get_config("max_items", 100)

        # Auth headers
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"
        if api_key:
            headers["X-API-Key"] = api_key

        url = self.source.url
        self.log.debug(f"Fetching custom API: {method} {url}")

        try:
            if method == "POST":
                response = await self.http.post(url, json=body, headers=headers)
            else:
                response = await self.http.get(url, headers=headers)

            if not response.ok:
                raise CollectorError(
                    f"Custom API error: HTTP {response.status_code}",
                    source_id=self.source.id,
                )
        except CollectorError:
            raise
        except Exception as e:
            raise CollectorError(
                f"Failed to fetch custom API: {e}",
                source_id=self.source.id,
                cause=e,
            )

        try:
            data = response.json()
        except Exception:
            raise CollectorError(
                "Failed to parse custom API response as JSON",
                source_id=self.source.id,
            )

        # Navigate to items list
        items_list = data
        if items_path:
            for key in items_path.split("."):
                if isinstance(items_list, dict):
                    items_list = items_list.get(key, [])
                else:
                    break

        if not isinstance(items_list, list):
            raise CollectorError(
                f"Expected list at items_path '{items_path}', got {type(items_list).__name__}",
                source_id=self.source.id,
            )

        self.log.debug(f"Custom API: {len(items_list)} items found")

        for entry in items_list[:max_items]:
            try:
                item = self._parse_entry(entry, mapping)
                yield item
            except Exception as e:
                self.log.warning(f"Failed to parse custom entry: {e}")
                continue

    def _parse_entry(self, entry: dict, mapping: dict) -> CollectedItem:
        """Parse a JSON entry into a CollectedItem using field mapping."""

        def get_field(entry: dict, field: str, defaults: list[str]) -> Any:
            """Get a field value using mapping or defaults."""
            key = mapping.get(field)
            if key and key in entry:
                return entry[key]
            for default_key in defaults:
                if default_key in entry:
                    return entry[default_key]
            return None

        # GUID
        guid_val = get_field(entry, "guid", ["id", "guid", "uid", "_id"])
        if not guid_val:
            guid_val = hashlib.sha256(str(entry).encode()).hexdigest()[:32]
        guid = str(guid_val)

        # Title
        title = get_field(entry, "title", ["title", "name", "headline"]) or "Sans titre"
        title = str(title)

        # URL
        url_val = get_field(entry, "url", ["url", "link", "href"])
        url = str(url_val) if url_val else None

        # Author
        author_val = get_field(entry, "author", ["author", "creator", "by", "user"])
        if isinstance(author_val, dict):
            author = author_val.get("name") or author_val.get("username", "")
        else:
            author = str(author_val) if author_val else None

        # Content
        content_val = get_field(entry, "content", ["content", "body", "text", "html"])
        content = str(content_val) if content_val else None
        if content and "<" in content:
            content = clean_html(content)

        # Summary
        summary_val = get_field(entry, "summary", ["summary", "description", "excerpt", "abstract"])
        summary = str(summary_val) if summary_val else None

        # Published date
        date_val = get_field(entry, "published_at", ["published_at", "date", "created_at", "pubDate", "timestamp"])
        published_at = None
        if date_val:
            if isinstance(date_val, (int, float)):
                from datetime import datetime, timezone
                published_at = datetime.fromtimestamp(date_val, tz=timezone.utc)
            else:
                published_at = parse_date(str(date_val))

        # Image
        image_val = get_field(entry, "image_url", ["image_url", "image", "thumbnail", "cover", "og_image"])
        image_url = str(image_val) if image_val else None

        return CollectedItem(
            guid=guid,
            title=title,
            url=url,
            author=author,
            content=content,
            summary=summary,
            published_at=published_at,
            image_url=image_url,
            extra={"platform": "custom", "raw": {k: v for k, v in entry.items() if isinstance(v, (str, int, float, bool, type(None)))}},
        )
