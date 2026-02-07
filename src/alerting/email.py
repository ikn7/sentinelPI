"""
Email notification channel for SentinelPi.

Sends alerts via SMTP email.
"""

from __future__ import annotations

import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from src.alerting.dispatcher import AlertPayload, NotificationChannel
from src.utils.config import get_settings, load_alerts_config
from src.utils.logging import create_logger

log = create_logger("alerting.email")


class EmailChannel(NotificationChannel):
    """
    Email notification channel.

    Sends alerts via SMTP with HTML formatting.
    """

    def __init__(
        self,
        smtp_host: str | None = None,
        smtp_port: int | None = None,
        use_tls: bool = True,
        username: str | None = None,
        password: str | None = None,
        from_address: str | None = None,
        from_name: str = "SentinelPi",
        to_addresses: list[str] | None = None,
        subject_template: str | None = None,
    ) -> None:
        """
        Initialize the email channel.

        Args:
            smtp_host: SMTP server hostname.
            smtp_port: SMTP server port.
            use_tls: Whether to use TLS.
            username: SMTP username.
            password: SMTP password.
            from_address: Sender email address.
            from_name: Sender display name.
            to_addresses: List of recipient addresses.
            subject_template: Email subject template.
        """
        self._smtp_host = smtp_host
        self._smtp_port = smtp_port
        self._use_tls = use_tls
        self._username = username
        self._password = password
        self._from_address = from_address
        self._from_name = from_name
        self._to_addresses = to_addresses or []
        self._subject_template = subject_template
        self._enabled = False
        self._min_severity = "warning"
        self._include_full_content = True

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from settings."""
        settings = get_settings()
        alerts_config = load_alerts_config()

        email_config = alerts_config.get("alerting", {}).get("channels", {}).get("email", {})

        if not self._smtp_host:
            self._smtp_host = email_config.get("smtp_host", "smtp.gmail.com")
        if not self._smtp_port:
            self._smtp_port = email_config.get("smtp_port", 587)
        if not self._username:
            self._username = settings.email_user or email_config.get("username")
        if not self._password:
            self._password = settings.email_password or email_config.get("password")
        if not self._from_address:
            self._from_address = email_config.get("from_address") or self._username
        if not self._to_addresses:
            self._to_addresses = email_config.get("to_addresses", [])
        if not self._subject_template:
            self._subject_template = email_config.get(
                "subject_template",
                "[SentinelPi] {severity_emoji} {severity}: {title}"
            )

        self._from_name = email_config.get("from_name", "SentinelPi")
        self._use_tls = email_config.get("use_tls", True)
        self._min_severity = email_config.get("min_severity", "warning")
        self._include_full_content = email_config.get("include_full_content", True)

        self._enabled = (
            email_config.get("enabled", False)
            and bool(self._smtp_host)
            and bool(self._username)
            and bool(self._password)
            and len(self._to_addresses) > 0
        )

        if self._enabled:
            log.info(f"Email channel enabled: {len(self._to_addresses)} recipients")
        else:
            log.debug("Email channel disabled: missing configuration")

    @property
    def name(self) -> str:
        return "email"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _format_subject(self, alert: AlertPayload) -> str:
        """Format the email subject."""
        try:
            title = alert.title
            if len(title) > 60:
                title = title[:57] + "..."

            return self._subject_template.format(
                severity=alert.severity_label,
                severity_emoji=alert.severity_emoji,
                title=title,
                source_name=alert.source_name,
            )
        except KeyError:
            return f"[SentinelPi] {alert.severity_emoji} {alert.title[:60]}"

    def _format_html_body(self, alert: AlertPayload) -> str:
        """Format the HTML email body."""
        # Severity colors
        severity_colors = {
            "info": "#17a2b8",
            "notice": "#007bff",
            "warning": "#ffc107",
            "critical": "#dc3545",
        }
        color = severity_colors.get(alert.severity.value, "#6c757d")

        html_parts = [
            '<!DOCTYPE html>',
            '<html><head><meta charset="utf-8"></head>',
            '<body style="font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', Roboto, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px;">',

            # Header
            f'<div style="background: {color}; color: white; padding: 15px 20px; border-radius: 8px 8px 0 0;">',
            f'<h2 style="margin: 0;">{alert.severity_emoji} {alert.severity_label}</h2>',
            '</div>',

            # Content
            '<div style="border: 1px solid #ddd; border-top: none; padding: 20px; border-radius: 0 0 8px 8px;">',

            # Title
            f'<h3 style="margin-top: 0; color: #333;">{self._escape_html(alert.title)}</h3>',

            # Metadata
            '<table style="width: 100%; border-collapse: collapse; margin-bottom: 15px;">',
        ]

        if alert.source_name:
            html_parts.append(
                f'<tr><td style="padding: 5px 0; color: #666;">📌 Source:</td>'
                f'<td style="padding: 5px 0;">{self._escape_html(alert.source_name)}</td></tr>'
            )

        if alert.author:
            html_parts.append(
                f'<tr><td style="padding: 5px 0; color: #666;">✍️ Auteur:</td>'
                f'<td style="padding: 5px 0;">{self._escape_html(alert.author)}</td></tr>'
            )

        if alert.published_at:
            html_parts.append(
                f'<tr><td style="padding: 5px 0; color: #666;">🕐 Date:</td>'
                f'<td style="padding: 5px 0;">{alert.published_at_formatted} ({alert.published_at_relative})</td></tr>'
            )

        if alert.filter_name:
            html_parts.append(
                f'<tr><td style="padding: 5px 0; color: #666;">🎯 Filtre:</td>'
                f'<td style="padding: 5px 0;">{self._escape_html(alert.filter_name)}</td></tr>'
            )

        html_parts.append('</table>')

        # Summary/Content
        if alert.summary or (self._include_full_content and alert.content):
            content = alert.content if self._include_full_content else alert.summary
            if content:
                if len(content) > 2000:
                    content = content[:2000] + "..."
                html_parts.append(
                    f'<div style="background: #f8f9fa; padding: 15px; border-radius: 4px; margin: 15px 0;">'
                    f'{self._escape_html(content)}</div>'
                )

        # Link button
        if alert.url:
            html_parts.append(
                f'<a href="{alert.url}" style="display: inline-block; background: {color}; '
                f'color: white; padding: 10px 20px; text-decoration: none; border-radius: 4px; '
                f'margin-top: 10px;">🔗 Lire l\'article</a>'
            )

        # Footer
        html_parts.extend([
            '</div>',
            '<div style="text-align: center; margin-top: 20px; color: #999; font-size: 12px;">',
            '<p>Envoyé par SentinelPi - Station de veille automatisée</p>',
            '</div>',
            '</body></html>',
        ])

        return '\n'.join(html_parts)

    def _format_text_body(self, alert: AlertPayload) -> str:
        """Format the plain text email body."""
        lines = [
            f"{alert.severity_emoji} {alert.severity_label}",
            "=" * 50,
            "",
            alert.title,
            "",
        ]

        if alert.source_name:
            lines.append(f"Source: {alert.source_name}")
        if alert.author:
            lines.append(f"Auteur: {alert.author}")
        if alert.published_at:
            lines.append(f"Date: {alert.published_at_formatted}")
        if alert.filter_name:
            lines.append(f"Filtre: {alert.filter_name}")

        lines.append("")

        if alert.summary:
            lines.append(alert.summary)
            lines.append("")

        if alert.url:
            lines.append(f"Lien: {alert.url}")
            lines.append("")

        lines.extend([
            "-" * 50,
            "SentinelPi - Station de veille automatisée",
        ])

        return "\n".join(lines)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("\n", "<br>")
        )

    async def send(self, alert: AlertPayload) -> bool:
        """
        Send an alert via email.

        Args:
            alert: The alert to send.

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            log.debug("Email channel is disabled")
            return False

        # Create message
        msg = MIMEMultipart("alternative")
        msg["Subject"] = self._format_subject(alert)
        msg["From"] = f"{self._from_name} <{self._from_address}>"
        msg["To"] = ", ".join(self._to_addresses)

        # Attach both plain text and HTML versions
        text_body = self._format_text_body(alert)
        html_body = self._format_html_body(alert)

        msg.attach(MIMEText(text_body, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Send in a thread pool to not block
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self._send_smtp, msg)
            log.debug(f"Email sent: {alert.title[:50]}")
            return True

        except Exception as e:
            log.error(f"Failed to send email: {e}")
            return False

    def _send_smtp(self, msg: MIMEMultipart) -> None:
        """Send email via SMTP (blocking)."""
        if self._use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                server.starttls(context=context)
                server.login(self._username, self._password)
                server.sendmail(
                    self._from_address,
                    self._to_addresses,
                    msg.as_string(),
                )
        else:
            with smtplib.SMTP(self._smtp_host, self._smtp_port) as server:
                if self._username and self._password:
                    server.login(self._username, self._password)
                server.sendmail(
                    self._from_address,
                    self._to_addresses,
                    msg.as_string(),
                )


def create_email_channel() -> EmailChannel:
    """Create and configure an email channel."""
    return EmailChannel()
