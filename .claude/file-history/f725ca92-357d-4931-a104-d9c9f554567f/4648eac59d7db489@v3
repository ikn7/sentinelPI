"""
Alert dispatcher for SentinelPi.

Routes alerts to appropriate notification channels based on configuration.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Sequence

from src.collectors.base import CollectedItem
from src.processors.filter import FilterMatch
from src.storage.models import Alert, AlertSeverity, Item, Source
from src.utils.config import get_settings, load_alerts_config
from src.utils.dates import now, format_date, format_relative
from src.utils.logging import create_logger, log_alert_event

log = create_logger("alerting.dispatcher")


class NotificationChannel(ABC):
    """Abstract base class for notification channels."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Channel name identifier."""
        pass

    @property
    @abstractmethod
    def enabled(self) -> bool:
        """Whether the channel is enabled."""
        pass

    @abstractmethod
    async def send(self, alert: "AlertPayload") -> bool:
        """
        Send an alert through this channel.

        Args:
            alert: The alert payload to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        pass

    async def send_batch(self, alerts: Sequence["AlertPayload"]) -> list[bool]:
        """
        Send multiple alerts.

        Default implementation sends one by one.

        Args:
            alerts: Alert payloads to send.

        Returns:
            List of success booleans.
        """
        results = []
        for alert in alerts:
            try:
                success = await self.send(alert)
                results.append(success)
            except Exception as e:
                log.error(f"Failed to send alert via {self.name}: {e}")
                results.append(False)
        return results


@dataclass
class AlertPayload:
    """
    Payload for alert notifications.

    Contains all information needed to send an alert.
    """

    # Alert metadata
    alert_id: str
    severity: AlertSeverity
    created_at: datetime = field(default_factory=now)

    # Item information
    item_guid: str = ""
    title: str = ""
    url: str | None = None
    summary: str | None = None
    content: str | None = None
    author: str | None = None
    published_at: datetime | None = None
    image_url: str | None = None

    # Source information
    source_id: str = ""
    source_name: str = ""
    source_category: str | None = None

    # Filter information
    filter_id: str | None = None
    filter_name: str | None = None
    matched_value: str | None = None

    # Tags
    tags: list[str] = field(default_factory=list)

    @property
    def severity_emoji(self) -> str:
        """Get emoji for severity level."""
        emojis = {
            AlertSeverity.INFO: "ℹ️",
            AlertSeverity.NOTICE: "📢",
            AlertSeverity.WARNING: "⚠️",
            AlertSeverity.CRITICAL: "🚨",
        }
        return emojis.get(self.severity, "🔔")

    @property
    def severity_label(self) -> str:
        """Get human-readable severity label."""
        return self.severity.value.upper()

    @property
    def published_at_formatted(self) -> str:
        """Get formatted publication date."""
        if self.published_at:
            return format_date(self.published_at, "%d/%m/%Y %H:%M")
        return ""

    @property
    def published_at_relative(self) -> str:
        """Get relative publication time."""
        if self.published_at:
            return format_relative(self.published_at)
        return ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "alert_id": self.alert_id,
            "severity": self.severity.value,
            "severity_emoji": self.severity_emoji,
            "created_at": self.created_at.isoformat(),
            "item_guid": self.item_guid,
            "title": self.title,
            "url": self.url,
            "summary": self.summary,
            "author": self.author,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "image_url": self.image_url,
            "source_id": self.source_id,
            "source_name": self.source_name,
            "source_category": self.source_category,
            "filter_id": self.filter_id,
            "filter_name": self.filter_name,
            "matched_value": self.matched_value,
            "tags": self.tags,
        }

    @classmethod
    def from_filter_match(
        cls,
        item: CollectedItem,
        match: FilterMatch,
        source: Source | None = None,
    ) -> "AlertPayload":
        """
        Create an AlertPayload from a filter match.

        Args:
            item: The matched item.
            match: The filter match result.
            source: The item's source (optional).

        Returns:
            AlertPayload instance.
        """
        import uuid

        severity = AlertSeverity.NOTICE
        if match.action_params:
            severity_str = match.action_params.get("severity", "notice")
            try:
                severity = AlertSeverity(severity_str)
            except ValueError:
                pass

        return cls(
            alert_id=str(uuid.uuid4()),
            severity=severity,
            item_guid=item.guid,
            title=item.title,
            url=item.url,
            summary=item.summary,
            content=item.content,
            author=item.author,
            published_at=item.published_at,
            image_url=item.image_url,
            source_id=source.id if source else item.extra.get("source_id", ""),
            source_name=source.name if source else item.extra.get("source_name", ""),
            source_category=source.category if source else None,
            filter_id=match.filter_id,
            filter_name=match.filter_name,
            matched_value=match.matched_value,
            tags=item.extra.get("tags", []),
        )


@dataclass
class AggregatedAlert:
    """An aggregated alert summary."""

    count: int
    severity: AlertSeverity
    alerts: list[AlertPayload]
    period_start: datetime
    period_end: datetime

    @property
    def title(self) -> str:
        """Generate aggregated title."""
        return f"{self.count} nouvelles alertes"

    @property
    def summary(self) -> str:
        """Generate aggregated summary."""
        sources = set(a.source_name for a in self.alerts if a.source_name)
        return f"De {len(sources)} source(s): {', '.join(list(sources)[:5])}"


class AlertAggregator:
    """
    Aggregates alerts to prevent notification spam.

    Groups alerts within a time window and sends summaries.
    """

    def __init__(
        self,
        window_minutes: int = 15,
        max_alerts_per_window: int = 10,
    ) -> None:
        """
        Initialize the aggregator.

        Args:
            window_minutes: Time window for aggregation.
            max_alerts_per_window: Threshold to trigger aggregation.
        """
        self.window_minutes = window_minutes
        self.max_alerts = max_alerts_per_window
        self._pending: list[AlertPayload] = []
        self._window_start: datetime | None = None

    def add(self, alert: AlertPayload) -> list[AlertPayload] | AggregatedAlert | None:
        """
        Add an alert to the aggregator.

        Returns:
            - List of individual alerts if below threshold
            - AggregatedAlert if threshold exceeded
            - None if still collecting
        """
        current = now()

        # Start new window if needed
        if self._window_start is None:
            self._window_start = current

        # Check if window expired
        window_end = self._window_start + timedelta(minutes=self.window_minutes)
        if current > window_end:
            # Flush current window and start new one
            result = self._flush()
            self._window_start = current
            self._pending = [alert]
            return result

        self._pending.append(alert)

        # Check if threshold exceeded
        if len(self._pending) >= self.max_alerts:
            return self._flush()

        return None

    def _flush(self) -> list[AlertPayload] | AggregatedAlert | None:
        """Flush pending alerts."""
        if not self._pending:
            return None

        alerts = self._pending.copy()
        self._pending = []

        if len(alerts) <= 3:
            # Send individually
            return alerts

        # Aggregate
        severities = [a.severity for a in alerts]
        max_severity = max(severities, key=lambda s: list(AlertSeverity).index(s))
        return AggregatedAlert(
            count=len(alerts),
            severity=max_severity,
            alerts=alerts,
            period_start=self._window_start or now(),
            period_end=now(),
        )

    def flush_all(self) -> list[AlertPayload] | AggregatedAlert | None:
        """Force flush all pending alerts."""
        result = self._flush()
        self._window_start = None
        return result


class AlertDispatcher:
    """
    Main alert dispatcher.

    Routes alerts to configured notification channels.
    """

    def __init__(self) -> None:
        """Initialize the dispatcher."""
        self._channels: dict[str, NotificationChannel] = {}
        self._aggregator: AlertAggregator | None = None
        self._config: dict[str, Any] = {}
        self._quiet_hours_start: str | None = None
        self._quiet_hours_end: str | None = None
        self._quiet_hours_bypass_critical: bool = True

        self._load_config()

    def _load_config(self) -> None:
        """Load alerting configuration."""
        self._config = load_alerts_config()
        alerting = self._config.get("alerting", {})

        # Setup aggregation
        agg_config = alerting.get("aggregation", {})
        if agg_config.get("enabled", True):
            self._aggregator = AlertAggregator(
                window_minutes=agg_config.get("window_minutes", 15),
                max_alerts_per_window=agg_config.get("max_alerts_per_window", 10),
            )

        # Setup quiet hours
        quiet_config = alerting.get("quiet_hours", {})
        if quiet_config.get("enabled", False):
            self._quiet_hours_start = quiet_config.get("start")
            self._quiet_hours_end = quiet_config.get("end")
            self._quiet_hours_bypass_critical = quiet_config.get("bypass_for_critical", True)

        log.info("Alert dispatcher initialized")

    def register_channel(self, channel: NotificationChannel) -> None:
        """
        Register a notification channel.

        Args:
            channel: The channel to register.
        """
        self._channels[channel.name] = channel
        log.debug(f"Registered channel: {channel.name}")

    def get_channel(self, name: str) -> NotificationChannel | None:
        """Get a channel by name."""
        return self._channels.get(name)

    def _is_quiet_hours(self) -> bool:
        """Check if currently in quiet hours."""
        if not self._quiet_hours_start or not self._quiet_hours_end:
            return False

        current = now()
        current_time = current.strftime("%H:%M")

        start = self._quiet_hours_start
        end = self._quiet_hours_end

        # Handle overnight quiet hours (e.g., 22:00 - 07:00)
        if start > end:
            return current_time >= start or current_time < end
        else:
            return start <= current_time < end

    def _get_channels_for_alert(
        self,
        alert: AlertPayload,
    ) -> list[NotificationChannel]:
        """
        Determine which channels should receive an alert.

        Args:
            alert: The alert to route.

        Returns:
            List of channels to send to.
        """
        alerting = self._config.get("alerting", {})
        channels_config = alerting.get("channels", {})
        rules = alerting.get("rules", [])

        # Check quiet hours
        if self._is_quiet_hours():
            if alert.severity != AlertSeverity.CRITICAL or not self._quiet_hours_bypass_critical:
                log.debug(f"Alert suppressed due to quiet hours: {alert.title[:50]}")
                return []

        selected_channels: set[str] = set()

        # Apply routing rules
        for rule in rules:
            rule_category = rule.get("category")
            rule_tags = rule.get("tags", [])
            rule_min_severity = rule.get("min_severity", "info")
            rule_channels = rule.get("channels", [])

            # Check if rule applies
            applies = False

            if rule_category and alert.source_category == rule_category:
                applies = True
            elif rule_tags and any(tag in alert.tags for tag in rule_tags):
                applies = True

            if applies:
                # Check severity
                severity_order = [s.value for s in AlertSeverity]
                if severity_order.index(alert.severity.value) >= severity_order.index(rule_min_severity):
                    selected_channels.update(rule_channels)

        # If no rules matched, use default channels based on severity
        if not selected_channels:
            for channel_name, channel_config in channels_config.items():
                if not channel_config.get("enabled", False):
                    continue

                min_severity = channel_config.get("min_severity", "info")
                severity_order = [s.value for s in AlertSeverity]

                if severity_order.index(alert.severity.value) >= severity_order.index(min_severity):
                    selected_channels.add(channel_name)

        # Return actual channel objects
        result = []
        for name in selected_channels:
            channel = self._channels.get(name)
            if channel and channel.enabled:
                result.append(channel)

        return result

    async def dispatch(self, alert: AlertPayload) -> dict[str, bool]:
        """
        Dispatch an alert to appropriate channels.

        Args:
            alert: The alert to dispatch.

        Returns:
            Dictionary mapping channel name to success status.
        """
        results: dict[str, bool] = {}

        # Apply aggregation if enabled
        if self._aggregator:
            agg_result = self._aggregator.add(alert)
            if agg_result is None:
                # Still collecting, don't send yet
                log.debug(f"Alert queued for aggregation: {alert.title[:50]}")
                return {"aggregated": True}

            if isinstance(agg_result, AggregatedAlert):
                # Send aggregated summary
                return await self._dispatch_aggregated(agg_result)
            else:
                # Send individual alerts
                for individual_alert in agg_result:
                    individual_results = await self._dispatch_single(individual_alert)
                    results.update(individual_results)
                return results

        # No aggregation, dispatch directly
        return await self._dispatch_single(alert)

    async def _dispatch_single(self, alert: AlertPayload) -> dict[str, bool]:
        """Dispatch a single alert."""
        results: dict[str, bool] = {}
        channels = self._get_channels_for_alert(alert)

        if not channels:
            log.debug(f"No channels for alert: {alert.title[:50]}")
            return results

        # Send to all channels concurrently
        tasks = []
        channel_names = []

        for channel in channels:
            tasks.append(channel.send(alert))
            channel_names.append(channel.name)

        if tasks:
            send_results = await asyncio.gather(*tasks, return_exceptions=True)

            for channel_name, result in zip(channel_names, send_results):
                if isinstance(result, Exception):
                    log.error(f"Channel {channel_name} failed: {result}")
                    results[channel_name] = False
                else:
                    results[channel_name] = result

                log_alert_event(
                    channel=channel_name,
                    severity=alert.severity.value,
                    event="Alert sent" if results.get(channel_name) else "Alert failed",
                    title=alert.title[:50],
                )

        return results

    async def _dispatch_aggregated(self, aggregated: AggregatedAlert) -> dict[str, bool]:
        """Dispatch an aggregated alert summary."""
        # Create a summary alert payload
        summary_alert = AlertPayload(
            alert_id=f"agg-{now().timestamp()}",
            severity=aggregated.severity,
            title=aggregated.title,
            summary=aggregated.summary,
        )

        log.info(f"Dispatching aggregated alert: {aggregated.count} alerts")
        return await self._dispatch_single(summary_alert)

    async def flush(self) -> dict[str, bool]:
        """Flush any pending aggregated alerts."""
        if not self._aggregator:
            return {}

        result = self._aggregator.flush_all()
        if result is None:
            return {}

        if isinstance(result, AggregatedAlert):
            return await self._dispatch_aggregated(result)
        else:
            results: dict[str, bool] = {}
            for alert in result:
                individual_results = await self._dispatch_single(alert)
                results.update(individual_results)
            return results


# Global dispatcher instance
_dispatcher: AlertDispatcher | None = None


def get_dispatcher() -> AlertDispatcher:
    """Get the global alert dispatcher."""
    global _dispatcher
    if _dispatcher is None:
        _dispatcher = AlertDispatcher()
    return _dispatcher
