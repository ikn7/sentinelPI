"""
Webhook notification channel for SentinelPi.

Sends alerts to external HTTP endpoints.
"""

from __future__ import annotations

import json
from typing import Any

from src.alerting.dispatcher import AlertPayload, NotificationChannel
from src.utils.config import get_settings, load_alerts_config
from src.utils.http import HttpClient
from src.utils.logging import create_logger

log = create_logger("alerting.webhook")


class WebhookChannel(NotificationChannel):
    """
    Webhook notification channel.

    Sends alerts as JSON payloads to configured HTTP endpoints.
    Supports custom headers and payload templates.
    """

    def __init__(
        self,
        url: str | None = None,
        method: str = "POST",
        headers: dict[str, str] | None = None,
        timeout: int = 30,
        max_retries: int = 3,
        payload_template: str | None = None,
    ) -> None:
        """
        Initialize the webhook channel.

        Args:
            url: Webhook endpoint URL.
            method: HTTP method (POST, PUT).
            headers: Custom HTTP headers.
            timeout: Request timeout in seconds.
            max_retries: Maximum retry attempts.
            payload_template: Custom JSON payload template.
        """
        self._url = url
        self._method = method.upper()
        self._headers = headers or {}
        self._timeout = timeout
        self._max_retries = max_retries
        self._payload_template = payload_template
        self._enabled = False
        self._min_severity = "notice"

        self._http: HttpClient | None = None
        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from settings."""
        settings = get_settings()
        alerts_config = load_alerts_config()

        webhook_config = alerts_config.get("alerting", {}).get("channels", {}).get("webhook", {})

        if not self._url:
            self._url = settings.webhook_url or webhook_config.get("url")

        self._method = webhook_config.get("method", self._method).upper()
        self._timeout = webhook_config.get("timeout", self._timeout)
        self._max_retries = webhook_config.get("max_retries", self._max_retries)
        self._min_severity = webhook_config.get("min_severity", "notice")

        # Merge headers
        config_headers = webhook_config.get("headers", {})
        for key, value in config_headers.items():
            if key not in self._headers:
                # Resolve environment variables
                if isinstance(value, str) and value.startswith("${"):
                    import os
                    var_name = value[2:-1]
                    value = os.environ.get(var_name, "")
                self._headers[key] = value

        # Add auth token if configured
        webhook_token = settings.webhook_token
        if webhook_token and "Authorization" not in self._headers:
            self._headers["Authorization"] = f"Bearer {webhook_token}"

        if not self._payload_template:
            self._payload_template = webhook_config.get("payload_template")

        self._enabled = webhook_config.get("enabled", False) and bool(self._url)

        if self._enabled:
            log.info(f"Webhook channel enabled: {self._url}")
        else:
            log.debug("Webhook channel disabled")

    @property
    def name(self) -> str:
        return "webhook"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_http_client(self) -> HttpClient:
        """Get or create HTTP client."""
        if self._http is None:
            self._http = HttpClient(
                timeout=self._timeout,
                max_retries=self._max_retries,
            )
        return self._http

    def _format_payload(self, alert: AlertPayload) -> dict[str, Any]:
        """
        Format the webhook payload.

        Args:
            alert: The alert to format.

        Returns:
            Dictionary payload.
        """
        if self._payload_template:
            try:
                # Template is a JSON string with placeholders
                formatted = self._payload_template.format(
                    alert_id=alert.alert_id,
                    severity=alert.severity.value,
                    severity_label=alert.severity_label,
                    severity_emoji=alert.severity_emoji,
                    title=alert.title,
                    url=alert.url or "",
                    summary=alert.summary or "",
                    content=alert.content or "",
                    author=alert.author or "",
                    published_at=alert.published_at.isoformat() if alert.published_at else "",
                    source_id=alert.source_id,
                    source_name=alert.source_name,
                    source_category=alert.source_category or "",
                    filter_id=alert.filter_id or "",
                    filter_name=alert.filter_name or "",
                    matched_value=alert.matched_value or "",
                    created_at=alert.created_at.isoformat(),
                )
                return json.loads(formatted)
            except (KeyError, json.JSONDecodeError) as e:
                log.warning(f"Invalid payload template: {e}")

        # Default payload structure
        return {
            "type": "sentinelpi_alert",
            "version": "1.0",
            "alert": alert.to_dict(),
        }

    def _format_slack_payload(self, alert: AlertPayload) -> dict[str, Any]:
        """
        Format payload for Slack-compatible webhooks.

        Args:
            alert: The alert to format.

        Returns:
            Slack-formatted payload.
        """
        # Slack block format
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{alert.severity_emoji} {alert.severity_label}",
                    "emoji": True,
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{alert.title}*",
                }
            },
        ]

        # Add fields
        fields = []
        if alert.source_name:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Source:*\n{alert.source_name}",
            })
        if alert.published_at:
            fields.append({
                "type": "mrkdwn",
                "text": f"*Date:*\n{alert.published_at_relative}",
            })

        if fields:
            blocks.append({
                "type": "section",
                "fields": fields,
            })

        # Add summary
        if alert.summary:
            summary = alert.summary
            if len(summary) > 500:
                summary = summary[:500] + "..."
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": summary,
                }
            })

        # Add link button
        if alert.url:
            blocks.append({
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "🔗 Lire l'article",
                            "emoji": True,
                        },
                        "url": alert.url,
                    }
                ]
            })

        return {
            "blocks": blocks,
            "text": f"{alert.severity_emoji} {alert.title}",  # Fallback text
        }

    async def send(self, alert: AlertPayload) -> bool:
        """
        Send an alert via webhook.

        Args:
            alert: The alert to send.

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            log.debug("Webhook channel is disabled")
            return False

        payload = self._format_payload(alert)

        try:
            http = self._get_http_client()

            # Ensure Content-Type is set
            headers = self._headers.copy()
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"

            if self._method == "POST":
                response = await http.post(
                    self._url,
                    json=payload,
                    headers=headers,
                )
            else:
                # For other methods, use httpx directly
                response = await http._request(
                    self._method,
                    self._url,
                    json=payload,
                    headers=headers,
                    use_cache=False,
                )

            if response.ok:
                log.debug(f"Webhook sent: {alert.title[:50]}")
                return True
            else:
                log.warning(
                    f"Webhook returned {response.status_code}: {response.text[:200]}"
                )
                return False

        except Exception as e:
            log.error(f"Failed to send webhook: {e}")
            return False

    async def send_slack(self, alert: AlertPayload) -> bool:
        """
        Send an alert formatted for Slack.

        Args:
            alert: The alert to send.

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            return False

        payload = self._format_slack_payload(alert)

        try:
            http = self._get_http_client()

            response = await http.post(
                self._url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            return response.ok

        except Exception as e:
            log.error(f"Failed to send Slack webhook: {e}")
            return False


class DiscordWebhook(WebhookChannel):
    """
    Discord-specific webhook channel.

    Formats alerts for Discord's webhook format.
    """

    @property
    def name(self) -> str:
        return "discord"

    def _format_payload(self, alert: AlertPayload) -> dict[str, Any]:
        """Format payload for Discord."""
        # Discord embed colors (decimal)
        severity_colors = {
            "info": 3447003,      # Blue
            "notice": 3066993,    # Green-blue
            "warning": 16776960,  # Yellow
            "critical": 15158332, # Red
        }
        color = severity_colors.get(alert.severity.value, 9807270)

        embed = {
            "title": alert.title,
            "description": alert.summary or "",
            "color": color,
            "fields": [],
            "footer": {
                "text": "SentinelPi",
            },
        }

        if alert.url:
            embed["url"] = alert.url

        if alert.source_name:
            embed["fields"].append({
                "name": "📌 Source",
                "value": alert.source_name,
                "inline": True,
            })

        if alert.published_at:
            embed["fields"].append({
                "name": "🕐 Date",
                "value": alert.published_at_relative,
                "inline": True,
            })

        if alert.filter_name:
            embed["fields"].append({
                "name": "🎯 Filtre",
                "value": alert.filter_name,
                "inline": True,
            })

        if alert.image_url:
            embed["thumbnail"] = {"url": alert.image_url}

        return {
            "content": f"{alert.severity_emoji} **{alert.severity_label}**",
            "embeds": [embed],
        }


def create_webhook_channel() -> WebhookChannel:
    """Create and configure a webhook channel."""
    return WebhookChannel()
