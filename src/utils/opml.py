"""
OPML import/export utilities for SentinelPi.

Provides functions to export RSS sources to OPML format and import OPML files.
OPML (Outline Processor Markup Language) is a standard format for exchanging
RSS feed lists between applications.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.dom import minidom

from src.utils.logging import create_logger

log = create_logger("utils.opml")


@dataclass
class OPMLOutline:
    """Represents an OPML outline element (feed or folder)."""

    text: str
    title: str | None = None
    type: str | None = None
    xml_url: str | None = None
    html_url: str | None = None
    category: str | None = None
    description: str | None = None
    children: list["OPMLOutline"] | None = None

    @property
    def is_folder(self) -> bool:
        """Check if this outline is a folder (has children, no feed URL)."""
        return self.xml_url is None and self.children is not None

    @property
    def is_feed(self) -> bool:
        """Check if this outline is a feed (has XML URL)."""
        return self.xml_url is not None


@dataclass
class OPMLDocument:
    """Represents a complete OPML document."""

    title: str
    date_created: datetime | None = None
    date_modified: datetime | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    outlines: list[OPMLOutline] | None = None

    def get_all_feeds(self) -> list[OPMLOutline]:
        """Get all feed outlines (flattened, ignoring folder structure)."""
        feeds = []

        def collect_feeds(outlines: list[OPMLOutline] | None, parent_category: str | None = None):
            if not outlines:
                return
            for outline in outlines:
                if outline.is_feed:
                    # Inherit category from parent folder if not set
                    if not outline.category and parent_category:
                        outline.category = parent_category
                    feeds.append(outline)
                elif outline.is_folder:
                    # Use folder name as category
                    folder_category = outline.text or outline.title
                    collect_feeds(outline.children, folder_category)

        collect_feeds(self.outlines)
        return feeds


def export_sources_to_opml(
    sources: list[Any],
    title: str = "SentinelPi RSS Feeds",
    owner_name: str | None = None,
    group_by_category: bool = True,
) -> str:
    """
    Export sources to OPML format.

    Args:
        sources: List of Source model objects.
        title: Title for the OPML document.
        owner_name: Optional owner name.
        group_by_category: If True, group feeds by category in folders.

    Returns:
        OPML XML string.
    """
    # Create root element
    opml = ET.Element("opml", version="2.0")

    # Head section
    head = ET.SubElement(opml, "head")
    ET.SubElement(head, "title").text = title
    ET.SubElement(head, "dateCreated").text = datetime.now(timezone.utc).strftime(
        "%a, %d %b %Y %H:%M:%S %z"
    )
    if owner_name:
        ET.SubElement(head, "ownerName").text = owner_name
    ET.SubElement(head, "docs").text = "http://opml.org/spec2.opml"

    # Body section
    body = ET.SubElement(opml, "body")

    # Filter RSS sources only
    rss_sources = [s for s in sources if s.type.value == "rss"]

    if group_by_category:
        # Group sources by category
        categories: dict[str, list[Any]] = {}
        uncategorized: list[Any] = []

        for source in rss_sources:
            if source.category:
                if source.category not in categories:
                    categories[source.category] = []
                categories[source.category].append(source)
            else:
                uncategorized.append(source)

        # Create folder outlines for each category
        for category, cat_sources in sorted(categories.items()):
            folder = ET.SubElement(body, "outline", text=category, title=category)
            for source in cat_sources:
                _add_source_outline(folder, source)

        # Add uncategorized sources at root level
        for source in uncategorized:
            _add_source_outline(body, source)
    else:
        # Flat list, no folders
        for source in rss_sources:
            _add_source_outline(body, source)

    # Pretty print
    xml_str = ET.tostring(opml, encoding="unicode")
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding=None)

    # Remove extra blank lines and XML declaration line
    lines = pretty_xml.split("\n")
    # Skip XML declaration, keep the rest
    result_lines = [line for line in lines[1:] if line.strip()]

    # Add proper XML declaration
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + "\n".join(result_lines)


def _add_source_outline(parent: ET.Element, source: Any) -> ET.Element:
    """Add a source as an outline element."""
    attrs = {
        "text": source.name,
        "title": source.name,
        "type": "rss",
        "xmlUrl": source.url,
    }

    # Add HTML URL if available in config
    config = source.config or {}
    if config.get("html_url"):
        attrs["htmlUrl"] = config["html_url"]

    # Add description if available
    if config.get("description"):
        attrs["description"] = config["description"]

    # Add category as attribute (some readers use this)
    if source.category:
        attrs["category"] = source.category

    return ET.SubElement(parent, "outline", **attrs)


def parse_opml(content: str) -> OPMLDocument:
    """
    Parse an OPML string into an OPMLDocument.

    Args:
        content: OPML XML string.

    Returns:
        Parsed OPMLDocument.

    Raises:
        ValueError: If the content is not valid OPML.
    """
    try:
        root = ET.fromstring(content)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    if root.tag != "opml":
        raise ValueError(f"Root element must be 'opml', got '{root.tag}'")

    # Parse head
    head = root.find("head")
    title = ""
    date_created = None
    date_modified = None
    owner_name = None
    owner_email = None

    if head is not None:
        title_el = head.find("title")
        if title_el is not None and title_el.text:
            title = title_el.text

        date_created_el = head.find("dateCreated")
        if date_created_el is not None and date_created_el.text:
            date_created = _parse_rfc822_date(date_created_el.text)

        date_modified_el = head.find("dateModified")
        if date_modified_el is not None and date_modified_el.text:
            date_modified = _parse_rfc822_date(date_modified_el.text)

        owner_name_el = head.find("ownerName")
        if owner_name_el is not None:
            owner_name = owner_name_el.text

        owner_email_el = head.find("ownerEmail")
        if owner_email_el is not None:
            owner_email = owner_email_el.text

    # Parse body
    body = root.find("body")
    outlines = []

    if body is not None:
        for outline_el in body.findall("outline"):
            outline = _parse_outline(outline_el)
            if outline:
                outlines.append(outline)

    return OPMLDocument(
        title=title,
        date_created=date_created,
        date_modified=date_modified,
        owner_name=owner_name,
        owner_email=owner_email,
        outlines=outlines,
    )


def _parse_outline(element: ET.Element, parent_category: str | None = None) -> OPMLOutline | None:
    """Parse an outline element recursively."""
    text = element.get("text", "")
    title = element.get("title")
    outline_type = element.get("type")
    xml_url = element.get("xmlUrl")
    html_url = element.get("htmlUrl")
    category = element.get("category") or parent_category
    description = element.get("description")

    # Check for child outlines (folder)
    child_elements = element.findall("outline")
    children = None

    if child_elements:
        children = []
        # Use current text as category for children
        child_category = text or title or category
        for child_el in child_elements:
            child = _parse_outline(child_el, child_category)
            if child:
                children.append(child)

    # Skip empty outlines
    if not text and not title and not xml_url:
        return None

    return OPMLOutline(
        text=text,
        title=title,
        type=outline_type,
        xml_url=xml_url,
        html_url=html_url,
        category=category,
        description=description,
        children=children if children else None,
    )


def _parse_rfc822_date(date_str: str) -> datetime | None:
    """Parse an RFC 822 date string."""
    from email.utils import parsedate_to_datetime

    try:
        return parsedate_to_datetime(date_str)
    except (ValueError, TypeError):
        return None


def import_opml_file(file_path: str | Path) -> OPMLDocument:
    """
    Import an OPML file.

    Args:
        file_path: Path to the OPML file.

    Returns:
        Parsed OPMLDocument.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"OPML file not found: {path}")

    content = path.read_text(encoding="utf-8")
    return parse_opml(content)


def export_opml_file(
    sources: list[Any],
    file_path: str | Path,
    title: str = "SentinelPi RSS Feeds",
    owner_name: str | None = None,
    group_by_category: bool = True,
) -> Path:
    """
    Export sources to an OPML file.

    Args:
        sources: List of Source model objects.
        file_path: Path for the output file.
        title: Title for the OPML document.
        owner_name: Optional owner name.
        group_by_category: If True, group feeds by category in folders.

    Returns:
        Path to the created file.
    """
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    opml_content = export_sources_to_opml(
        sources=sources,
        title=title,
        owner_name=owner_name,
        group_by_category=group_by_category,
    )

    path.write_text(opml_content, encoding="utf-8")
    log.info(f"Exported {len([s for s in sources if s.type.value == 'rss'])} RSS sources to {path}")

    return path


async def import_opml_to_database(
    file_path: str | Path,
    enabled: bool = True,
    interval_minutes: int = 60,
    priority: int = 2,
    skip_duplicates: bool = True,
) -> dict[str, Any]:
    """
    Import OPML feeds into the database.

    Args:
        file_path: Path to the OPML file.
        enabled: Whether to enable imported sources.
        interval_minutes: Default collection interval.
        priority: Default priority (1=high, 2=normal, 3=low).
        skip_duplicates: If True, skip sources with same URL.

    Returns:
        Dict with import statistics.
    """
    import hashlib

    from sqlalchemy import select

    from src.storage.database import get_session, init_database
    from src.storage.models import Source, SourceType

    await init_database()

    # Parse OPML
    doc = import_opml_file(file_path)
    feeds = doc.get_all_feeds()

    stats = {
        "total": len(feeds),
        "imported": 0,
        "skipped": 0,
        "errors": [],
    }

    async with get_session() as session:
        # Get existing URLs for duplicate check
        existing_urls = set()
        if skip_duplicates:
            result = await session.execute(select(Source.url))
            existing_urls = {row[0] for row in result.all()}

        for feed in feeds:
            if not feed.xml_url:
                stats["skipped"] += 1
                continue

            # Check duplicate
            if skip_duplicates and feed.xml_url in existing_urls:
                stats["skipped"] += 1
                log.debug(f"Skipping duplicate: {feed.text}")
                continue

            try:
                # Generate deterministic ID
                source_key = f"{feed.text}:{feed.xml_url}"
                source_id = hashlib.sha256(source_key.encode()).hexdigest()[:32]

                # Check if ID exists
                result = await session.execute(
                    select(Source).where(Source.id == source_id)
                )
                if result.scalar_one_or_none():
                    stats["skipped"] += 1
                    continue

                # Create source
                source = Source()
                source.id = source_id
                source.name = feed.title or feed.text
                source.type = SourceType.RSS
                source.url = feed.xml_url
                source.enabled = enabled
                source.interval_minutes = interval_minutes
                source.priority = priority
                source.category = feed.category
                source.config = {}

                if feed.html_url:
                    source.config = {"html_url": feed.html_url}
                if feed.description:
                    config = source.config or {}
                    config["description"] = feed.description
                    source.config = config

                session.add(source)
                existing_urls.add(feed.xml_url)
                stats["imported"] += 1
                log.debug(f"Imported: {source.name}")

            except Exception as e:
                stats["errors"].append(f"{feed.text}: {str(e)}")
                log.warning(f"Failed to import {feed.text}: {e}")

        await session.commit()

    log.info(
        f"OPML import complete: {stats['imported']} imported, "
        f"{stats['skipped']} skipped, {len(stats['errors'])} errors"
    )

    return stats


async def export_database_to_opml(
    file_path: str | Path,
    title: str = "SentinelPi RSS Feeds",
    owner_name: str | None = None,
    group_by_category: bool = True,
    enabled_only: bool = False,
) -> dict[str, Any]:
    """
    Export database sources to an OPML file.

    Args:
        file_path: Path for the output file.
        title: Title for the OPML document.
        owner_name: Optional owner name.
        group_by_category: If True, group feeds by category in folders.
        enabled_only: If True, only export enabled sources.

    Returns:
        Dict with export statistics.
    """
    from sqlalchemy import select

    from src.storage.database import get_session, init_database
    from src.storage.models import Source, SourceType

    await init_database()

    async with get_session() as session:
        query = select(Source).where(Source.type == SourceType.RSS)
        if enabled_only:
            query = query.where(Source.enabled == True)
        query = query.order_by(Source.category, Source.name)

        result = await session.execute(query)
        sources = result.scalars().all()

    if not sources:
        return {"total": 0, "file_path": None, "message": "No RSS sources to export"}

    path = export_opml_file(
        sources=sources,
        file_path=file_path,
        title=title,
        owner_name=owner_name,
        group_by_category=group_by_category,
    )

    return {
        "total": len(sources),
        "file_path": str(path),
        "message": f"Exported {len(sources)} RSS sources to {path}",
    }
