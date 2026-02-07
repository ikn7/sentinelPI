"""Tests for the desktop notification channel."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.alerting.desktop import DesktopChannel
from src.alerting.dispatcher import AlertPayload
from src.storage.models import AlertSeverity


class TestDesktopChannel:
    def test_name(self):
        with patch("src.alerting.desktop.load_alerts_config", return_value={}):
            channel = DesktopChannel()
            assert channel.name == "desktop"

    def test_disabled_by_default(self):
        with patch("src.alerting.desktop.load_alerts_config", return_value={}):
            channel = DesktopChannel()
            assert not channel.enabled

    def test_enabled_with_config(self):
        config = {
            "alerting": {
                "channels": {
                    "desktop": {"enabled": True}
                }
            }
        }
        with patch("src.alerting.desktop.load_alerts_config", return_value=config):
            with patch("shutil.which", return_value="/usr/bin/notify-send"):
                channel = DesktopChannel()
                assert channel.enabled

    def test_disabled_without_notify_send(self):
        config = {
            "alerting": {
                "channels": {
                    "desktop": {"enabled": True}
                }
            }
        }
        with patch("src.alerting.desktop.load_alerts_config", return_value=config):
            with patch("shutil.which", return_value=None):
                channel = DesktopChannel()
                assert not channel.enabled

    @pytest.mark.asyncio
    async def test_send_when_disabled(self):
        with patch("src.alerting.desktop.load_alerts_config", return_value={}):
            channel = DesktopChannel()
            alert = AlertPayload(
                alert_id="test-1",
                severity=AlertSeverity.INFO,
                title="Test Alert",
            )
            result = await channel.send(alert)
            assert result is False
