"""
SentinelPi alerting module.

Provides notification channels and alert dispatching.
"""

from src.alerting.dispatcher import (
    AlertAggregator,
    AlertDispatcher,
    AlertPayload,
    AggregatedAlert,
    NotificationChannel,
    get_dispatcher,
)
from src.alerting.telegram import (
    TelegramChannel,
    TelegramBotManager,
    create_telegram_channel,
)
from src.alerting.email import (
    EmailChannel,
    create_email_channel,
)
from src.alerting.webhook import (
    WebhookChannel,
    DiscordWebhook,
    create_webhook_channel,
)
from src.alerting.desktop import (
    DesktopChannel,
    create_desktop_channel,
)

__all__ = [
    # Dispatcher
    "AlertAggregator",
    "AlertDispatcher",
    "AlertPayload",
    "AggregatedAlert",
    "NotificationChannel",
    "get_dispatcher",
    # Telegram
    "TelegramChannel",
    "TelegramBotManager",
    "create_telegram_channel",
    # Email
    "EmailChannel",
    "create_email_channel",
    # Webhook
    "WebhookChannel",
    "DiscordWebhook",
    "create_webhook_channel",
    # Desktop
    "DesktopChannel",
    "create_desktop_channel",
]


def setup_channels() -> AlertDispatcher:
    """
    Setup all notification channels and return configured dispatcher.

    Returns:
        Configured AlertDispatcher with all channels registered.
    """
    dispatcher = get_dispatcher()

    # Register Telegram channel
    telegram = create_telegram_channel()
    if telegram.enabled:
        dispatcher.register_channel(telegram)

    # Register Email channel
    email = create_email_channel()
    if email.enabled:
        dispatcher.register_channel(email)

    # Register Webhook channel
    webhook = create_webhook_channel()
    if webhook.enabled:
        dispatcher.register_channel(webhook)

    # Register Desktop channel
    desktop = create_desktop_channel()
    if desktop.enabled:
        dispatcher.register_channel(desktop)

    return dispatcher
