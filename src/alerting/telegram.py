"""
Telegram notification channel for SentinelPi.

Sends alerts via Telegram bot.
"""

from __future__ import annotations

import asyncio
import html
from typing import Any

from src.alerting.dispatcher import AlertPayload, NotificationChannel
from src.utils.config import get_settings, load_alerts_config
from src.utils.logging import create_logger

log = create_logger("alerting.telegram")

# Telegram message length limit
MAX_MESSAGE_LENGTH = 4096


class TelegramChannel(NotificationChannel):
    """
    Telegram notification channel.

    Sends alerts to a Telegram chat via bot API.
    Supports Markdown formatting.
    """

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
        disable_web_preview: bool = False,
        silent: bool = False,
        format_template: str | None = None,
    ) -> None:
        """
        Initialize the Telegram channel.

        Args:
            bot_token: Telegram bot token.
            chat_id: Target chat ID.
            disable_web_preview: Disable link previews.
            silent: Send without notification sound.
            format_template: Custom message format template.
        """
        self._bot_token = bot_token
        self._chat_id = chat_id
        self._disable_web_preview = disable_web_preview
        self._silent = silent
        self._format_template = format_template
        self._enabled = False
        self._min_severity = "notice"

        self._load_config()

    def _load_config(self) -> None:
        """Load configuration from settings."""
        settings = get_settings()
        alerts_config = load_alerts_config()

        telegram_config = alerts_config.get("alerting", {}).get("channels", {}).get("telegram", {})

        if not self._bot_token:
            self._bot_token = settings.telegram_bot_token or telegram_config.get("bot_token")
        if not self._chat_id:
            self._chat_id = settings.telegram_chat_id or telegram_config.get("chat_id")

        self._enabled = telegram_config.get("enabled", False) and bool(self._bot_token and self._chat_id)
        self._disable_web_preview = telegram_config.get("disable_web_preview", self._disable_web_preview)
        self._silent = telegram_config.get("silent", self._silent)
        self._min_severity = telegram_config.get("min_severity", "notice")

        if not self._format_template:
            self._format_template = telegram_config.get("format")

        if self._enabled:
            log.info("Telegram channel enabled")
        else:
            if not self._bot_token:
                log.debug("Telegram disabled: no bot token")
            elif not self._chat_id:
                log.debug("Telegram disabled: no chat ID")

    @property
    def name(self) -> str:
        return "telegram"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _format_message(self, alert: AlertPayload) -> str:
        """
        Format the alert message for Telegram.

        Args:
            alert: The alert to format.

        Returns:
            Formatted message string (Markdown).
        """
        if self._format_template:
            try:
                return self._format_template.format(
                    severity=alert.severity_label,
                    severity_emoji=alert.severity_emoji,
                    title=self._escape_markdown(alert.title),
                    url=alert.url or "",
                    summary=self._escape_markdown(alert.summary or ""),
                    source_name=self._escape_markdown(alert.source_name),
                    published_at=alert.published_at_formatted,
                    author=self._escape_markdown(alert.author or ""),
                    filter_name=self._escape_markdown(alert.filter_name or ""),
                    matched_value=self._escape_markdown(alert.matched_value or ""),
                )
            except KeyError as e:
                log.warning(f"Invalid format template key: {e}")

        # Default format
        lines = [
            f"{alert.severity_emoji} *{alert.severity_label}*",
            "",
            f"📰 *{self._escape_markdown(alert.title)}*",
        ]

        if alert.source_name:
            lines.append(f"📌 Source: {self._escape_markdown(alert.source_name)}")

        if alert.published_at:
            lines.append(f"🕐 {alert.published_at_relative}")

        if alert.summary:
            lines.append("")
            summary = alert.summary
            if len(summary) > 500:
                summary = summary[:500] + "..."
            lines.append(self._escape_markdown(summary))

        if alert.filter_name:
            lines.append("")
            lines.append(f"🎯 Filtre: {self._escape_markdown(alert.filter_name)}")

        if alert.url:
            lines.append("")
            lines.append(f"🔗 [Lire l'article]({alert.url})")

        message = "\n".join(lines)

        # Truncate if too long
        if len(message) > MAX_MESSAGE_LENGTH:
            message = message[:MAX_MESSAGE_LENGTH - 100] + "\n\n_(message tronqué)_"

        return message

    def _escape_markdown(self, text: str) -> str:
        """Escape special Markdown characters."""
        if not text:
            return ""
        # Escape Markdown special characters
        for char in ["_", "*", "[", "]", "(", ")", "~", "`", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"]:
            text = text.replace(char, f"\\{char}")
        return text

    async def send(self, alert: AlertPayload) -> bool:
        """
        Send an alert via Telegram.

        Args:
            alert: The alert to send.

        Returns:
            True if sent successfully.
        """
        if not self._enabled:
            log.debug("Telegram channel is disabled")
            return False

        message = self._format_message(alert)

        try:
            # Use python-telegram-bot library
            from telegram import Bot
            from telegram.constants import ParseMode

            bot = Bot(token=self._bot_token)

            await bot.send_message(
                chat_id=self._chat_id,
                text=message,
                parse_mode=ParseMode.MARKDOWN,
                disable_web_page_preview=self._disable_web_preview,
                disable_notification=self._silent,
            )

            log.debug(f"Telegram message sent: {alert.title[:50]}")
            return True

        except ImportError:
            log.error("python-telegram-bot library not installed")
            return False
        except Exception as e:
            log.error(f"Failed to send Telegram message: {e}")
            return False

    async def send_batch(self, alerts: list[AlertPayload]) -> list[bool]:
        """
        Send multiple alerts with rate limiting.

        Telegram has rate limits, so we add delays between messages.
        """
        results = []

        for i, alert in enumerate(alerts):
            success = await self.send(alert)
            results.append(success)

            # Rate limit: max 30 messages per second to same chat
            if i < len(alerts) - 1:
                await asyncio.sleep(0.1)

        return results


class TelegramBotManager:
    """
    Manager for Telegram bot interactions.

    Handles bot commands and interactive features.
    """

    def __init__(self, bot_token: str) -> None:
        """Initialize the bot manager."""
        self._token = bot_token
        self._running = False

    async def start(self) -> None:
        """Start the bot (for receiving commands)."""
        try:
            from telegram import Update
            from telegram.ext import Application, CommandHandler, ContextTypes

            app = Application.builder().token(self._token).build()

            # Add command handlers
            app.add_handler(CommandHandler("start", self._cmd_start))
            app.add_handler(CommandHandler("status", self._cmd_status))
            app.add_handler(CommandHandler("sources", self._cmd_sources))
            app.add_handler(CommandHandler("help", self._cmd_help))

            self._running = True
            log.info("Telegram bot started")

            await app.run_polling()

        except ImportError:
            log.error("python-telegram-bot library not installed")
        except Exception as e:
            log.error(f"Failed to start Telegram bot: {e}")

    async def stop(self) -> None:
        """Stop the bot."""
        self._running = False
        log.info("Telegram bot stopped")

    async def _cmd_start(self, update, context) -> None:
        """Handle /start command."""
        await update.message.reply_text(
            "🛡️ *SentinelPi Bot*\n\n"
            "Je vous enverrai des alertes de veille.\n\n"
            "Commandes disponibles:\n"
            "/status - État du système\n"
            "/sources - Liste des sources\n"
            "/help - Aide",
            parse_mode="Markdown",
        )

    async def _cmd_status(self, update, context) -> None:
        """Handle /status command."""
        # TODO: Get actual status from system
        await update.message.reply_text(
            "✅ *Statut SentinelPi*\n\n"
            "🟢 Système: En ligne\n"
            "📊 Sources: --\n"
            "📰 Items (24h): --\n"
            "🔔 Alertes (24h): --",
            parse_mode="Markdown",
        )

    async def _cmd_sources(self, update, context) -> None:
        """Handle /sources command."""
        await update.message.reply_text(
            "📋 *Sources configurées*\n\n"
            "Utilisez le dashboard web pour gérer les sources.",
            parse_mode="Markdown",
        )

    async def _cmd_help(self, update, context) -> None:
        """Handle /help command."""
        await update.message.reply_text(
            "🆘 *Aide SentinelPi*\n\n"
            "Ce bot envoie des alertes de veille automatiques.\n\n"
            "Les alertes sont envoyées selon vos filtres configurés.\n"
            "Gérez la configuration via le dashboard web.",
            parse_mode="Markdown",
        )


def create_telegram_channel() -> TelegramChannel:
    """Create and configure a Telegram channel."""
    return TelegramChannel()
