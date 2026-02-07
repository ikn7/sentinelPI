"""
Logging configuration for SentinelPi.

Uses loguru for structured, colorized logging with rotation and retention.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from src.utils.config import Settings


# Remove default handler
logger.remove()

# Flag to track if logging has been configured
_configured = False


def setup_logging(settings: Settings | None = None) -> None:
    """
    Configure logging based on settings.

    Args:
        settings: Application settings. If None, uses default configuration.
    """
    global _configured

    if _configured:
        return

    # Import here to avoid circular imports
    if settings is None:
        from src.utils.config import get_settings
        settings = get_settings()

    log_config = settings.logging

    # Ensure log directory exists
    log_path = log_config.file_path
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Console handler (stderr)
    logger.add(
        sys.stderr,
        level=log_config.level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level:<8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
               "<level>{message}</level>",
        colorize=log_config.colorize,
        backtrace=True,
        diagnose=True,
    )

    # File handler with rotation
    logger.add(
        str(log_path),
        level=log_config.level,
        format=log_config.format,
        rotation=log_config.rotation,
        retention=log_config.retention,
        compression="gz",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
    )

    _configured = True
    logger.info(f"Logging configured: level={log_config.level}, file={log_path}")


def get_logger(name: str) -> "logger":
    """
    Get a logger instance for a specific module.

    Args:
        name: The name of the module (typically __name__).

    Returns:
        A logger instance bound with the module name.
    """
    return logger.bind(name=name)


class LoggerAdapter:
    """
    Adapter to provide a logger with a consistent interface.

    Allows binding context to all log messages from a component.
    """

    def __init__(self, name: str, **context: str | int | float):
        """
        Initialize the logger adapter.

        Args:
            name: The name of the component.
            **context: Additional context to bind to all messages.
        """
        self._logger = logger.bind(name=name, **context)

    def debug(self, message: str, **kwargs: str | int | float) -> None:
        """Log a debug message."""
        self._logger.debug(message, **kwargs)

    def info(self, message: str, **kwargs: str | int | float) -> None:
        """Log an info message."""
        self._logger.info(message, **kwargs)

    def warning(self, message: str, **kwargs: str | int | float) -> None:
        """Log a warning message."""
        self._logger.warning(message, **kwargs)

    def error(self, message: str, **kwargs: str | int | float) -> None:
        """Log an error message."""
        self._logger.error(message, **kwargs)

    def critical(self, message: str, **kwargs: str | int | float) -> None:
        """Log a critical message."""
        self._logger.critical(message, **kwargs)

    def exception(self, message: str, **kwargs: str | int | float) -> None:
        """Log an exception with traceback."""
        self._logger.exception(message, **kwargs)

    def bind(self, **kwargs: str | int | float) -> "LoggerAdapter":
        """Return a new adapter with additional context bound."""
        return LoggerAdapter(
            name=self._logger._options.get("name", ""),
            **{**self._logger._options, **kwargs}
        )


def create_logger(name: str, **context: str | int | float) -> LoggerAdapter:
    """
    Create a logger adapter for a component.

    Args:
        name: The name of the component.
        **context: Additional context to bind to all messages.

    Returns:
        A LoggerAdapter instance.

    Example:
        >>> log = create_logger("collectors.rss", source_id="feed-123")
        >>> log.info("Starting collection")
        2024-01-15 10:30:00 | INFO     | collectors.rss | Starting collection
    """
    return LoggerAdapter(name, **context)


# ==================================================
# Specialized loggers
# ==================================================

def log_collector_event(
    collector_type: str,
    source_name: str,
    event: str,
    **details: str | int | float | None,
) -> None:
    """
    Log a collector event with structured context.

    Args:
        collector_type: Type of collector (rss, web, etc.).
        source_name: Name of the source being collected.
        event: Description of the event.
        **details: Additional event details.
    """
    logger.bind(
        component="collector",
        collector_type=collector_type,
        source_name=source_name,
    ).info(f"{event}", **details)


def log_alert_event(
    channel: str,
    severity: str,
    event: str,
    **details: str | int | float | None,
) -> None:
    """
    Log an alert event with structured context.

    Args:
        channel: Alert channel (telegram, email, etc.).
        severity: Alert severity level.
        event: Description of the event.
        **details: Additional event details.
    """
    logger.bind(
        component="alerting",
        channel=channel,
        severity=severity,
    ).info(f"{event}", **details)


def log_processing_event(
    processor: str,
    event: str,
    **details: str | int | float | None,
) -> None:
    """
    Log a processing event with structured context.

    Args:
        processor: Processor name (dedup, filter, etc.).
        event: Description of the event.
        **details: Additional event details.
    """
    logger.bind(
        component="processor",
        processor=processor,
    ).info(f"{event}", **details)
