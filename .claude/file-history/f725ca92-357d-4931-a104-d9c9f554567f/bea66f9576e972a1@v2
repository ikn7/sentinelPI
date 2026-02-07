"""
Mastodon collector for SentinelPi.

Uses Mastodon's public API for hashtag timelines and account statuses.
"""

from __future__ import annotations

import hashlib
import re
from typing import AsyncIterator
from urllib.parse import urlparse

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

log = create_logger("collectors.mastodon")


@register_collector
class MastodonCollector(BaseCollector):
    """
    Collector for Mastodon instances.

    Uses the public Mastodon API (no authentication required for public data).

    Configuration options (in source.config):
    - type: "hashtag", "account", or "timeline" (default: "hashtag")
    - hashtag: Hashtag to follow (without #)
    - account_id: Account ID to follow (for type=account)
    - limit: Number of statuses to fetch (default: 20, max: 40)
    - exclude_replies: Exclude replies (default: True)
    - exclude_reblogs: Exclude reblogs (default: True)
    - max_items: Maximum items to process (default: 50)

    Source URL should be the instance base URL (e.g. https://mastodon.social)
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.MASTODON

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """Collect statuses from Mastodon."""
        config_type = self.get_config("type", "hashtag")
        limit = min(self.get_config("limit", 20), 40)
        max_items = self.get_config("max_items", 50)

        instance_url = self.source.url.rstrip("/")

        if config_type == "hashtag":
            hashtag = self.get_config("hashtag", "")
            if not hashtag:
                raise CollectorError(
                    "No hashtag configured for Mastodon hashtag collector",
                    source_id=self.source.id,
                )
            api_url = f"{instance_url}/api/v1/timelines/tag/{hashtag}?limit={limit}"

        elif config_type == "account":
            account_id = self.get_config("account_id", "")
            if not account_id:
                raise CollectorError(
                    "No account_id configured for Mastodon account collector",
                    source_id=self.source.id,
                )
            exclude_replies = str(self.get_config("exclude_replies", True)).lower()
            exclude_reblogs = str(self.get_config("exclude_reblogs", True)).lower()
            api_url = (
                f"{instance_url}/api/v1/accounts/{account_id}/statuses"
                f"?limit={limit}&exclude_replies={exclude_replies}"
                f"&exclude_reblogs={exclude_reblogs}"
            )

        elif config_type == "timeline":
            api_url = f"{instance_url}/api/v1/timelines/public?limit={limit}&local=true"

        else:
            raise CollectorError(
                f"Unknown Mastodon config type: {config_type}",
                source_id=self.source.id,
            )

        self.log.debug(f"Fetching Mastodon API: {api_url}")

        try:
            response = await self.http.get(api_url)
            if not response.ok:
                raise CollectorError(
                    f"Mastodon API error: HTTP {response.status_code}",
                    source_id=self.source.id,
                )
        except CollectorError:
            raise
        except Exception as e:
            raise CollectorError(
                f"Failed to fetch Mastodon API: {e}",
                source_id=self.source.id,
                cause=e,
            )

        try:
            statuses = response.json()
        except Exception:
            raise CollectorError(
                "Failed to parse Mastodon API response as JSON",
                source_id=self.source.id,
            )

        if not isinstance(statuses, list):
            raise CollectorError(
                "Unexpected Mastodon API response format",
                source_id=self.source.id,
            )

        self.log.debug(f"Mastodon: {len(statuses)} statuses fetched")

        for status in statuses[:max_items]:
            try:
                item = self._parse_status(status, instance_url)
                yield item
            except Exception as e:
                self.log.warning(f"Failed to parse Mastodon status: {e}")
                continue

    def _parse_status(self, status: dict, instance_url: str) -> CollectedItem:
        """Parse a Mastodon status into a CollectedItem."""
        status_id = status.get("id", "")
        guid = f"mastodon:{instance_url}:{status_id}"

        # Content (HTML)
        content_html = status.get("content", "")
        content_text = clean_html(content_html) if content_html else ""

        # Build title from first line or truncated content
        title = content_text[:120] if content_text else "Sans contenu"
        if len(content_text) > 120:
            title = title[:117] + "..."

        # Spoiler text as title if present
        spoiler = status.get("spoiler_text", "")
        if spoiler:
            title = spoiler

        # URL
        url = status.get("url") or f"{instance_url}/web/statuses/{status_id}"

        # Author
        account = status.get("account", {})
        author = account.get("display_name") or account.get("username", "")
        acct = account.get("acct", "")

        # Published date
        published_at = None
        created_at_str = status.get("created_at")
        if created_at_str:
            published_at = parse_date(created_at_str)

        # Media attachments
        image_url = None
        media_urls = []
        for attachment in status.get("media_attachments", []):
            media_url = attachment.get("url")
            if media_url:
                media_urls.append(media_url)
                if not image_url and attachment.get("type") in ("image", "gifv"):
                    image_url = attachment.get("preview_url") or media_url

        # Tags
        tags = [tag.get("name", "") for tag in status.get("tags", []) if tag.get("name")]

        # Engagement metrics
        reblogs = status.get("reblogs_count", 0)
        favourites = status.get("favourites_count", 0)
        replies = status.get("replies_count", 0)

        # Language
        language = status.get("language")

        return CollectedItem(
            guid=guid,
            title=title,
            url=url,
            author=f"{author} (@{acct})" if acct else author,
            content=content_text,
            summary=content_text[:300] if content_text else None,
            published_at=published_at,
            image_url=image_url,
            media_urls=media_urls,
            language=language,
            extra={
                "platform": "mastodon",
                "instance": instance_url,
                "status_id": status_id,
                "account_id": account.get("id", ""),
                "acct": acct,
                "tags": tags,
                "reblogs_count": reblogs,
                "favourites_count": favourites,
                "replies_count": replies,
                "sensitive": status.get("sensitive", False),
                "visibility": status.get("visibility", "public"),
            },
        )
