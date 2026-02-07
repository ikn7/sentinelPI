"""
Web page scraper collector for SentinelPi.

Scrapes structured content from web pages using CSS selectors.
"""

from __future__ import annotations

import hashlib
from typing import AsyncIterator
from urllib.parse import urljoin, urlparse

from src.collectors.base import (
    BaseCollector,
    CollectedItem,
    CollectorError,
    register_collector,
)
from src.storage.models import SourceType
from src.utils.dates import parse_date
from src.utils.logging import create_logger
from src.utils.parsing import (
    clean_html,
    extract_attribute,
    extract_images,
    extract_text,
    find_element,
    find_elements,
    parse_html,
)

log = create_logger("collectors.web")


@register_collector
class WebCollector(BaseCollector):
    """
    Collector for web pages using CSS selectors.

    Scrapes structured content from web pages by configuring CSS selectors
    for different parts of the content (articles, titles, links, etc.).

    Configuration options (in source.config):
    - selector: CSS selector for item containers (required)
    - title_selector: Selector for title within item (default: "h2, h3, .title")
    - link_selector: Selector for link (default: "a")
    - link_attribute: Attribute containing the URL (default: "href")
    - content_selector: Selector for content/description (optional)
    - date_selector: Selector for date (optional)
    - date_format: strptime format for parsing dates (optional)
    - date_attribute: Attribute containing date (default: text content)
    - author_selector: Selector for author (optional)
    - image_selector: Selector for image (default: "img")
    - image_attribute: Attribute containing image URL (default: "src")
    - max_items: Maximum items to collect (default: 50)
    - strip_html: Whether to strip HTML from content (default: True)
    - follow_links: Whether to follow links for full content (default: False)

    Example configuration:
    ```yaml
    config:
      selector: "article.news-item"
      title_selector: "h2.title"
      link_selector: "a.read-more"
      content_selector: ".excerpt"
      date_selector: ".date"
      date_format: "%d/%m/%Y"
    ```
    """

    @classmethod
    def supports_source_type(cls) -> SourceType:
        return SourceType.WEB

    async def collect(self) -> AsyncIterator[CollectedItem]:
        """
        Collect items from the web page.

        Yields:
            CollectedItem objects for each found item.
        """
        # Validate configuration
        selector = self.get_config("selector")
        if not selector:
            raise CollectorError(
                "Web collector requires 'selector' in config",
                source_id=self.source.id,
            )

        # Fetch the page
        try:
            response = await self.http.get(self.source.url)

            if not response.ok:
                raise CollectorError(
                    f"Failed to fetch page: HTTP {response.status_code}",
                    source_id=self.source.id,
                )

        except Exception as e:
            raise CollectorError(
                f"Failed to fetch page: {e}",
                source_id=self.source.id,
                cause=e if isinstance(e, Exception) else None,
            )

        # Parse HTML
        soup = parse_html(response.text)
        base_url = str(response.url)

        # Find item containers
        items = find_elements(soup, selector)

        if not items:
            self.log.warning(f"No items found with selector: {selector}")
            return

        max_items = self.get_config("max_items", 50)
        follow_links = self.get_config("follow_links", False)

        self.log.debug(f"Found {len(items)} items on page")

        for i, item_element in enumerate(items[:max_items]):
            try:
                item = await self._parse_item(
                    item_element,
                    base_url,
                    index=i,
                    follow_links=follow_links,
                )
                if item:
                    yield item
            except Exception as e:
                self.log.warning(f"Failed to parse item {i}: {e}")
                continue

    async def _parse_item(
        self,
        element,
        base_url: str,
        index: int,
        follow_links: bool,
    ) -> CollectedItem | None:
        """Parse an HTML element into a CollectedItem."""
        strip_html = self.get_config("strip_html", True)

        # Extract title
        title = self._extract_field(
            element,
            self.get_config("title_selector", "h2, h3, .title, [class*='title']"),
            strip_html=True,
        )

        if not title:
            self.log.debug(f"Item {index}: no title found, skipping")
            return None

        # Extract link
        link_selector = self.get_config("link_selector", "a")
        link_attr = self.get_config("link_attribute", "href")
        url = self._extract_link(element, link_selector, link_attr, base_url)

        # Generate GUID
        guid = self._generate_guid(url, title, index)

        # Extract content/description
        content = None
        content_selector = self.get_config("content_selector")
        if content_selector:
            content = self._extract_field(
                element,
                content_selector,
                strip_html=strip_html,
            )

        # Extract date
        published_at = None
        date_selector = self.get_config("date_selector")
        if date_selector:
            date_str = self._extract_field(
                element,
                date_selector,
                attribute=self.get_config("date_attribute"),
                strip_html=True,
            )
            if date_str:
                date_format = self.get_config("date_format")
                if date_format:
                    try:
                        from datetime import datetime
                        published_at = datetime.strptime(date_str.strip(), date_format)
                    except ValueError:
                        published_at = parse_date(date_str)
                else:
                    published_at = parse_date(date_str)

        # Extract author
        author = None
        author_selector = self.get_config("author_selector")
        if author_selector:
            author = self._extract_field(
                element,
                author_selector,
                strip_html=True,
            )

        # Extract image
        image_url = None
        image_selector = self.get_config("image_selector", "img")
        image_attr = self.get_config("image_attribute", "src")
        image_url = self._extract_image(element, image_selector, image_attr, base_url)

        # Follow link for full content if configured
        full_content = None
        if follow_links and url:
            full_content = await self._fetch_full_content(url)
            if full_content and not content:
                content = full_content

        # Create summary from content
        summary = None
        if content:
            if len(content) > 500:
                summary = content[:500] + "..."
            else:
                summary = content

        return CollectedItem(
            guid=guid,
            title=title,
            url=url,
            author=author,
            content=content,
            summary=summary,
            published_at=published_at,
            image_url=image_url,
            extra={
                "source_type": "web_scrape",
                "base_url": base_url,
            },
        )

    def _extract_field(
        self,
        element,
        selector: str,
        attribute: str | None = None,
        strip_html: bool = True,
    ) -> str | None:
        """Extract a field from an element using a selector."""
        found = find_element(element, selector)
        if not found:
            return None

        if attribute:
            return extract_attribute(found, attribute)

        text = extract_text(found, strip=True)
        if strip_html:
            text = clean_html(text) if "<" in text else text

        return text if text else None

    def _extract_link(
        self,
        element,
        selector: str,
        attribute: str,
        base_url: str,
    ) -> str | None:
        """Extract and resolve a link URL."""
        found = find_element(element, selector)
        if not found:
            # Try the element itself if it's a link
            if element.name == "a":
                found = element
            else:
                return None

        url = extract_attribute(found, attribute)
        if not url:
            return None

        # Resolve relative URLs
        if not urlparse(url).netloc:
            url = urljoin(base_url, url)

        return url

    def _extract_image(
        self,
        element,
        selector: str,
        attribute: str,
        base_url: str,
    ) -> str | None:
        """Extract and resolve an image URL."""
        found = find_element(element, selector)
        if not found:
            return None

        # Try multiple attributes for images
        for attr in [attribute, "data-src", "data-lazy-src", "srcset"]:
            url = extract_attribute(found, attr)
            if url:
                # Handle srcset (take first URL)
                if attr == "srcset":
                    url = url.split(",")[0].split()[0]

                # Resolve relative URLs
                if not urlparse(url).netloc:
                    url = urljoin(base_url, url)

                return url

        return None

    def _generate_guid(
        self,
        url: str | None,
        title: str,
        index: int,
    ) -> str:
        """Generate a unique identifier for the item."""
        if url:
            return hashlib.sha256(url.encode()).hexdigest()[:32]

        # Fall back to title + source URL + index
        unique_str = f"{self.source.url}:{title}:{index}"
        return hashlib.sha256(unique_str.encode()).hexdigest()[:32]

    async def _fetch_full_content(self, url: str) -> str | None:
        """Fetch the full content from a linked page."""
        try:
            response = await self.http.get(url)

            if not response.ok:
                return None

            soup = parse_html(response.text)

            # Try common content selectors
            content_selectors = [
                "article",
                ".article-content",
                ".post-content",
                ".entry-content",
                ".content",
                "main",
            ]

            for selector in content_selectors:
                content_elem = find_element(soup, selector)
                if content_elem:
                    # Remove unwanted elements
                    for unwanted in content_elem.select(
                        "script, style, nav, header, footer, aside, .ads, .comments"
                    ):
                        unwanted.decompose()

                    text = extract_text(content_elem)
                    if text and len(text) > 100:
                        return text

            return None

        except Exception as e:
            self.log.debug(f"Failed to fetch full content from {url}: {e}")
            return None
