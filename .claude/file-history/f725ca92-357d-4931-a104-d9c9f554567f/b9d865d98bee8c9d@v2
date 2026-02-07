"""
Date and time utilities for SentinelPi.

Provides date parsing, formatting, and timezone handling.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

from dateutil import parser as dateutil_parser
from dateutil.tz import gettz, tzutc

from src.utils.config import get_settings


def get_timezone():
    """
    Get the configured timezone.

    Returns:
        Timezone object.
    """
    settings = get_settings()
    tz = gettz(settings.app.timezone)
    return tz or tzutc()


def now() -> datetime:
    """
    Get the current datetime in UTC.

    Returns:
        Current UTC datetime.
    """
    return datetime.now(timezone.utc)


def now_local() -> datetime:
    """
    Get the current datetime in the configured timezone.

    Returns:
        Current local datetime.
    """
    return datetime.now(get_timezone())


def parse_date(
    date_string: str | None,
    default: datetime | None = None,
    fuzzy: bool = True,
) -> datetime | None:
    """
    Parse a date string into a datetime object.

    Handles many formats including ISO 8601, RSS, and natural language.

    Args:
        date_string: Date string to parse.
        default: Default value if parsing fails.
        fuzzy: Whether to allow fuzzy parsing.

    Returns:
        Parsed datetime or default.
    """
    if not date_string:
        return default

    try:
        # Use dateutil for flexible parsing
        parsed = dateutil_parser.parse(date_string, fuzzy=fuzzy)

        # Ensure timezone awareness (assume UTC if naive)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    except (ValueError, OverflowError, TypeError):
        return default


def parse_rss_date(date_string: str | None) -> datetime | None:
    """
    Parse an RSS/Atom date string.

    Handles RFC 822, RFC 3339, ISO 8601, and common variations.

    Args:
        date_string: Date string from RSS/Atom feed.

    Returns:
        Parsed datetime or None.
    """
    if not date_string:
        return None

    # Common RSS date formats
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",      # RFC 822
        "%a, %d %b %Y %H:%M:%S %Z",      # RFC 822 with timezone name
        "%Y-%m-%dT%H:%M:%S%z",           # ISO 8601
        "%Y-%m-%dT%H:%M:%SZ",            # ISO 8601 UTC
        "%Y-%m-%dT%H:%M:%S.%f%z",        # ISO 8601 with microseconds
        "%Y-%m-%dT%H:%M:%S.%fZ",         # ISO 8601 UTC with microseconds
        "%Y-%m-%d %H:%M:%S",             # Simple datetime
        "%Y-%m-%d",                       # Date only
    ]

    # Clean up the date string
    date_string = date_string.strip()

    # Try explicit formats first
    for fmt in formats:
        try:
            parsed = datetime.strptime(date_string, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue

    # Fall back to dateutil
    return parse_date(date_string)


def format_date(
    dt: datetime | None,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    local: bool = True,
) -> str:
    """
    Format a datetime as a string.

    Args:
        dt: Datetime to format.
        fmt: Format string.
        local: Whether to convert to local timezone.

    Returns:
        Formatted date string or empty string.
    """
    if dt is None:
        return ""

    if local:
        dt = to_local(dt)

    return dt.strftime(fmt)


def format_relative(dt: datetime | None) -> str:
    """
    Format a datetime as a relative time string (e.g., "2 hours ago").

    Args:
        dt: Datetime to format.

    Returns:
        Relative time string.
    """
    if dt is None:
        return ""

    current = now()

    # Ensure both are timezone-aware
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = current - dt
    seconds = diff.total_seconds()

    if seconds < 0:
        return "dans le futur"

    if seconds < 60:
        return "à l'instant"

    if seconds < 3600:
        minutes = int(seconds / 60)
        return f"il y a {minutes} min"

    if seconds < 86400:
        hours = int(seconds / 3600)
        return f"il y a {hours}h"

    if seconds < 604800:
        days = int(seconds / 86400)
        if days == 1:
            return "hier"
        return f"il y a {days} jours"

    if seconds < 2592000:
        weeks = int(seconds / 604800)
        return f"il y a {weeks} sem."

    if seconds < 31536000:
        months = int(seconds / 2592000)
        return f"il y a {months} mois"

    years = int(seconds / 31536000)
    return f"il y a {years} an{'s' if years > 1 else ''}"


def to_utc(dt: datetime) -> datetime:
    """
    Convert a datetime to UTC.

    Args:
        dt: Datetime to convert.

    Returns:
        UTC datetime.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def to_local(dt: datetime) -> datetime:
    """
    Convert a datetime to the configured local timezone.

    Args:
        dt: Datetime to convert.

    Returns:
        Local datetime.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(get_timezone())


def is_recent(dt: datetime | None, hours: int = 24) -> bool:
    """
    Check if a datetime is within the last N hours.

    Args:
        dt: Datetime to check.
        hours: Number of hours to consider "recent".

    Returns:
        True if recent, False otherwise.
    """
    if dt is None:
        return False

    current = now()

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    diff = current - dt
    return diff.total_seconds() < hours * 3600


def days_ago(days: int) -> datetime:
    """
    Get a datetime N days ago.

    Args:
        days: Number of days.

    Returns:
        Datetime N days ago.
    """
    from datetime import timedelta
    return now() - timedelta(days=days)


def start_of_day(dt: datetime | None = None) -> datetime:
    """
    Get the start of day (midnight) for a datetime.

    Args:
        dt: Datetime (defaults to now).

    Returns:
        Start of day datetime.
    """
    if dt is None:
        dt = now_local()

    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def end_of_day(dt: datetime | None = None) -> datetime:
    """
    Get the end of day (23:59:59) for a datetime.

    Args:
        dt: Datetime (defaults to now).

    Returns:
        End of day datetime.
    """
    if dt is None:
        dt = now_local()

    return dt.replace(hour=23, minute=59, second=59, microsecond=999999)
