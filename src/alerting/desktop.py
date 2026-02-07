"""
Desktop notification channel for SentinelPi.

Sends alerts as desktop notifications using the notify-send command (Linux).
"""

from __future__ import annotations

import asyncio
import shutil
from typing import Any

from src.alerting.dispatcher import AlertPayload, NotificationChannel
from src.utils.config import load_alerts_config
from src.utils.logging import create_logger

log = create_logger("alerting.desktop")


class DesktopChannel(NotificationChannel):
    """
    Desktop notification channel.

    Uses notify-send on Linux (libnotify) for desktop notifications.
    Falls back to a basic terminal bell if notify-send is not available.
    """

    def __init__(self) -> None:
        self._enabled = False
        self._urgency_map = {
            "info": "low",
            "notice": "normal",
            "warning": "normal",
            "critical": "critical",
        }
        self._icon = "dialog-information"
        self._timeout_ms = 10000
        self._has_notify_send = shutil.which("notify-send") is not None

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from alerts config."""
        alerts_config = load_alerts_config()
        desktop_config = alerts_config.get("alerting", {}).get("channels", {}).get("desktop", {})

        self._enabled = desktop_config.get("enabled", False)
        self._icon = desktop_config.get("icon", "dialog-information")
        self._timeout_ms = desktop_config.get("timeout_ms", 10000)

        if self._enabled and not self._has_notify_send:
            log.warning("Desktop notifications enabled but notify-send not found")
            self._enabled = False

        if self._enabled:
            log.info("Desktop notification channel enabled")

    @property
    def name(self) -> str:
        return "desktop"

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def send(self, alert: AlertPayload) -> bool:
        """Send a desktop notification."""
        if not self._enabled:
            return False

        severity = alert.severity.value
        urgency = self._urgency_map.get(severity, "normal")

        title = f"{alert.severity_emoji} SentinelPi - {alert.severity_label}"
        body = alert.title
        if alert.source_name:
            body += f"\n{alert.source_name}"
        if alert.summary:
            summary = alert.summary[:200]
            body += f"\n{summary}"

        try:
            cmd = [
                "notify-send",
                "--urgency", urgency,
                "--expire-time", str(self._timeout_ms),
                "--icon", self._icon,
                "--app-name", "SentinelPi",
                title,
                body,
            ]
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()

            log.debug(f"Desktop notification sent: {alert.title[:50]}")
            return proc.returncode == 0

        except Exception as e:
            log.error(f"Failed to send desktop notification: {e}")
            return False


def create_desktop_channel() -> DesktopChannel:
    """Create and configure a desktop notification channel."""
    return DesktopChannel()
