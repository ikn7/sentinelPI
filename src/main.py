"""
SentinelPi - Main entry point.

Multi-source monitoring station for Raspberry Pi.
"""

from __future__ import annotations

import asyncio
import signal
import sys
from typing import NoReturn

from src.storage.database import close_database, init_database
from src.utils.config import get_settings
from src.utils.logging import create_logger, setup_logging

log = create_logger("main")

# Shutdown flag
_shutdown_event: asyncio.Event | None = None


def handle_shutdown(signum: int, frame) -> None:
    """Handle shutdown signals gracefully."""
    signal_name = signal.Signals(signum).name
    log.info(f"Received {signal_name}, initiating shutdown...")
    if _shutdown_event:
        _shutdown_event.set()


async def startup() -> None:
    """Initialize all components."""
    log.info("Starting SentinelPi...")

    # Initialize database
    await init_database()

    # Start scheduler
    settings = get_settings()
    if settings.scheduler.enabled:
        from src.scheduler import start_scheduler
        await start_scheduler()
        log.info("Scheduler started")

    log.info("SentinelPi started successfully")


async def shutdown() -> None:
    """Cleanup and shutdown all components."""
    log.info("Shutting down SentinelPi...")

    # Stop scheduler
    try:
        from src.scheduler import stop_scheduler
        await stop_scheduler()
        log.info("Scheduler stopped")
    except Exception as e:
        log.warning(f"Error stopping scheduler: {e}")

    # Close HTTP client
    try:
        from src.utils.http import close_http_client
        await close_http_client()
    except Exception as e:
        log.warning(f"Error closing HTTP client: {e}")

    # Close database
    await close_database()

    log.info("SentinelPi shutdown complete")


async def run() -> None:
    """Main run loop."""
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    # Register signal handlers
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, handle_shutdown)

    try:
        await startup()

        settings = get_settings()
        log.info(f"SentinelPi v{settings.app.version} is running")
        log.info(f"Timezone: {settings.app.timezone}")
        log.info("Press Ctrl+C to stop")

        # Wait for shutdown signal
        await _shutdown_event.wait()

    except Exception as e:
        log.exception(f"Fatal error: {e}")
        raise
    finally:
        await shutdown()


async def run_once() -> None:
    """Run a single collection cycle (for testing/cron)."""
    log.info("Running single collection cycle...")

    await init_database()

    try:
        from src.scheduler import get_scheduler
        scheduler = get_scheduler()
        await scheduler.run_now()
    finally:
        await close_database()

    log.info("Collection cycle complete")


def main() -> NoReturn:
    """Entry point for the application."""
    # Setup logging first
    setup_logging()

    settings = get_settings()
    log.info(f"Starting {settings.app.name} v{settings.app.version}")

    # Check for --once flag
    if "--once" in sys.argv:
        log.info("Running in single-shot mode")
        try:
            asyncio.run(run_once())
        except Exception as e:
            log.exception(f"Error: {e}")
            sys.exit(1)
        sys.exit(0)

    # Check for OPML commands
    if "--export-opml" in sys.argv:
        try:
            idx = sys.argv.index("--export-opml")
            output_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else "data/feeds.opml"
            from src.utils.opml import export_database_to_opml
            result = asyncio.run(export_database_to_opml(output_file))
            log.info(result["message"])
        except Exception as e:
            log.exception(f"Export error: {e}")
            sys.exit(1)
        sys.exit(0)

    if "--import-opml" in sys.argv:
        try:
            idx = sys.argv.index("--import-opml")
            input_file = sys.argv[idx + 1] if idx + 1 < len(sys.argv) else None
            if not input_file:
                log.error("Usage: sentinelpi --import-opml <file.opml>")
                sys.exit(1)
            from src.utils.opml import import_opml_to_database
            result = asyncio.run(import_opml_to_database(input_file))
            log.info(f"Imported: {result['imported']} | Skipped: {result['skipped']}")
            if result['errors']:
                for err in result['errors']:
                    log.warning(err)
        except Exception as e:
            log.exception(f"Import error: {e}")
            sys.exit(1)
        sys.exit(0)

    # Normal continuous mode
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        log.info("Interrupted by user")
    except Exception as e:
        log.exception(f"Application error: {e}")
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
