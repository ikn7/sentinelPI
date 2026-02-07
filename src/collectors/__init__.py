"""
SentinelPi collectors module.

This module provides collectors for various data sources.
Import this module to register all available collectors.
"""

from src.collectors.base import (
    BaseCollector,
    CollectedItem,
    CollectionResult,
    CollectorError,
    create_collector,
    get_collector_class,
    list_registered_collectors,
    register_collector,
)

# Import collectors to trigger registration
from src.collectors.rss import RSSCollector
from src.collectors.reddit import RedditCollector
from src.collectors.youtube import YouTubeCollector
from src.collectors.web import WebCollector
from src.collectors.mastodon import MastodonCollector
from src.collectors.custom import CustomCollector

__all__ = [
    # Base classes
    "BaseCollector",
    "CollectedItem",
    "CollectionResult",
    "CollectorError",
    # Registry functions
    "create_collector",
    "get_collector_class",
    "list_registered_collectors",
    "register_collector",
    # Collector classes
    "RSSCollector",
    "RedditCollector",
    "YouTubeCollector",
    "WebCollector",
    "MastodonCollector",
    "CustomCollector",
]
