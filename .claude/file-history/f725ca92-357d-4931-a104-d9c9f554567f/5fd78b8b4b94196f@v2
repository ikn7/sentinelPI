"""
Parsing utilities for SentinelPi.

Provides HTML/XML parsing, text extraction, and content cleaning.
"""

from __future__ import annotations

import hashlib
import html
import re
from typing import Any
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup, Tag


def parse_html(content: str, parser: str = "lxml") -> BeautifulSoup:
    """
    Parse HTML content into a BeautifulSoup object.

    Args:
        content: HTML string to parse.
        parser: Parser to use (lxml, html.parser, html5lib).

    Returns:
        BeautifulSoup object.
    """
    return BeautifulSoup(content, parser)


def extract_text(element: Tag | BeautifulSoup | None, strip: bool = True) -> str:
    """
    Extract text content from an HTML element.

    Args:
        element: BeautifulSoup element.
        strip: Whether to strip whitespace.

    Returns:
        Extracted text string.
    """
    if element is None:
        return ""

    text = element.get_text(separator=" ")

    if strip:
        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_attribute(
    element: Tag | BeautifulSoup | None,
    attribute: str,
    default: str = "",
) -> str:
    """
    Extract an attribute value from an HTML element.

    Args:
        element: BeautifulSoup element.
        attribute: Attribute name to extract.
        default: Default value if attribute not found.

    Returns:
        Attribute value or default.
    """
    if element is None:
        return default

    value = element.get(attribute)

    if value is None:
        return default

    if isinstance(value, list):
        return " ".join(value)

    return str(value)


def find_element(
    soup: BeautifulSoup | Tag,
    selector: str,
) -> Tag | None:
    """
    Find an element using a CSS selector.

    Args:
        soup: BeautifulSoup object or Tag.
        selector: CSS selector string.

    Returns:
        First matching element or None.
    """
    try:
        return soup.select_one(selector)
    except Exception:
        return None


def find_elements(
    soup: BeautifulSoup | Tag,
    selector: str,
) -> list[Tag]:
    """
    Find all elements matching a CSS selector.

    Args:
        soup: BeautifulSoup object or Tag.
        selector: CSS selector string.

    Returns:
        List of matching elements.
    """
    try:
        return soup.select(selector)
    except Exception:
        return []


def clean_html(content: str) -> str:
    """
    Remove HTML tags and decode entities.

    Args:
        content: HTML string.

    Returns:
        Clean text string.
    """
    if not content:
        return ""

    # Parse and extract text
    soup = parse_html(content, parser="html.parser")

    # Remove script and style elements
    for element in soup(["script", "style", "noscript"]):
        element.decompose()

    # Get text
    text = soup.get_text(separator=" ")

    # Decode HTML entities
    text = html.unescape(text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def extract_links(soup: BeautifulSoup | Tag, base_url: str = "") -> list[dict[str, str]]:
    """
    Extract all links from HTML.

    Args:
        soup: BeautifulSoup object or Tag.
        base_url: Base URL for resolving relative links.

    Returns:
        List of dicts with 'url' and 'text' keys.
    """
    links = []

    for a in soup.find_all("a", href=True):
        url = a["href"]

        # Resolve relative URLs
        if base_url and not urlparse(url).netloc:
            url = urljoin(base_url, url)

        text = extract_text(a)

        links.append({"url": url, "text": text})

    return links


def extract_images(soup: BeautifulSoup | Tag, base_url: str = "") -> list[str]:
    """
    Extract all image URLs from HTML.

    Args:
        soup: BeautifulSoup object or Tag.
        base_url: Base URL for resolving relative links.

    Returns:
        List of image URLs.
    """
    images = []

    for img in soup.find_all("img", src=True):
        url = img["src"]

        # Resolve relative URLs
        if base_url and not urlparse(url).netloc:
            url = urljoin(base_url, url)

        images.append(url)

    return images


def extract_meta(soup: BeautifulSoup) -> dict[str, str]:
    """
    Extract metadata from HTML head.

    Args:
        soup: BeautifulSoup object.

    Returns:
        Dictionary of meta tags (name/property -> content).
    """
    meta = {}

    for tag in soup.find_all("meta"):
        name = tag.get("name") or tag.get("property")
        content = tag.get("content")

        if name and content:
            meta[name] = content

    # Also get title
    title_tag = soup.find("title")
    if title_tag:
        meta["title"] = extract_text(title_tag)

    return meta


def content_hash(content: str) -> str:
    """
    Generate a hash of content for deduplication.

    Args:
        content: Content string to hash.

    Returns:
        SHA-256 hash string (64 characters).
    """
    # Normalize content before hashing
    normalized = re.sub(r"\s+", " ", content.lower().strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length.

    Args:
        text: Text to truncate.
        max_length: Maximum length.
        suffix: Suffix to add if truncated.

    Returns:
        Truncated text.
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)].rsplit(" ", 1)[0] + suffix


def normalize_url(url: str) -> str:
    """
    Normalize a URL for comparison.

    Args:
        url: URL string.

    Returns:
        Normalized URL.
    """
    parsed = urlparse(url)

    # Lowercase scheme and host
    scheme = parsed.scheme.lower()
    netloc = parsed.netloc.lower()

    # Remove trailing slash from path
    path = parsed.path.rstrip("/") or "/"

    # Sort query parameters
    query = parsed.query

    # Reconstruct
    if query:
        return f"{scheme}://{netloc}{path}?{query}"
    return f"{scheme}://{netloc}{path}"


def extract_domain(url: str) -> str:
    """
    Extract the domain from a URL.

    Args:
        url: URL string.

    Returns:
        Domain string.
    """
    parsed = urlparse(url)
    return parsed.netloc.lower()
