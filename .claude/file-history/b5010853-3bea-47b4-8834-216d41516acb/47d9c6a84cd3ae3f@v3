"""
Job scheduler for SentinelPi.

Orchestrates periodic collection, processing, and maintenance tasks.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Coroutine

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.collectors import create_collector, CollectedItem, CollectionResult
from src.processors import (
    Deduplicator,
    FilterEngine,
    Scorer,
    Enricher,
    load_filters_from_config,
    get_preference_learner,
)
from src.alerting import AlertPayload, get_dispatcher, setup_channels
from src.storage.database import get_session, init_database
from src.storage.models import Source, Item, Alert, AlertSeverity, ItemStatus
from src.utils.config import get_settings, load_sources_config
from src.utils.dates import now
from src.utils.logging import create_logger, log_collector_event

log = create_logger("scheduler.jobs")


class CollectionJob:
    """
    Handles collection from a single source.

    Includes fetching, deduplication, filtering, scoring, and storage.
    """

    def __init__(self, source: Source) -> None:
        self.source = source
        self.log = create_logger(
            "scheduler.collection",
            source_id=source.id,
            source_name=source.name,
        )

    async def run(self) -> CollectionResult:
        """
        Run the collection job for this source.

        Returns:
            CollectionResult with statistics.
        """
        self.log.info(f"Starting collection: {self.source.name}")

        result = CollectionResult(
            source_id=self.source.id,
            source_name=self.source.name,
            success=False,
        )

        try:
            # Create collector
            collector = create_collector(self.source)

            # Collect items
            collected_items: list[CollectedItem] = []
            async for item in collector.collect():
                item.extra["source_id"] = self.source.id
                item.extra["source_name"] = self.source.name
                collected_items.append(item)

            result.items_collected = len(collected_items)

            if not collected_items:
                self.log.info("No items collected")
                result.success = True
                return result

            # Process items
            async with get_session() as session:
                # Deduplication
                deduplicator = Deduplicator(session, source_id=self.source.id)
                new_items, dedup_result = await deduplicator.filter_duplicates(collected_items)

                result.items_new = len(new_items)

                if not new_items:
                    self.log.info("All items were duplicates")
                    result.success = True
                    await self._update_source_status(session, success=True)
                    return result

                # Load filters and process
                filters = load_filters_from_config()
                filter_engine = FilterEngine(filters)
                enricher = Enricher()
                scorer = Scorer()
                learner = get_preference_learner()

                # Process each new item
                items_to_store: list[Item] = []
                alerts_to_send: list[AlertPayload] = []

                for collected_item in new_items:
                    # Filter
                    filter_result = filter_engine.process_item(
                        collected_item,
                        source_category=self.source.category,
                    )

                    # Skip excluded items
                    if filter_result.excluded:
                        continue

                    # Enrich
                    enrichment = enricher.enrich(collected_item)

                    # Score (base scoring)
                    scored = scorer.score_item(
                        collected_item,
                        filter_result=filter_result,
                        source_priority=self.source.priority,
                    )

                    # Add preference score
                    preference_score = await learner.compute_preference_score(
                        keywords=enrichment.keywords,
                        source_id=self.source.id,
                        category=self.source.category,
                        author=collected_item.author,
                        session=session,
                    )
                    total_score = scored.score + preference_score

                    # Create Item model
                    item = self._create_item_model(
                        collected_item,
                        filter_result,
                        enrichment,
                        total_score,
                    )
                    items_to_store.append(item)

                    # Create alerts
                    for alert_match in filter_result.alerts:
                        alert_payload = AlertPayload.from_filter_match(
                            collected_item,
                            alert_match,
                            self.source,
                        )
                        alerts_to_send.append(alert_payload)

                # Store items
                for item in items_to_store:
                    session.add(item)

                await session.flush()

                # Update source status
                await self._update_source_status(session, success=True)

                # Commit
                await session.commit()

                self.log.info(
                    f"Stored {len(items_to_store)} items, "
                    f"{len(alerts_to_send)} alerts to send"
                )

            # Dispatch alerts (outside transaction)
            if alerts_to_send:
                dispatcher = get_dispatcher()
                for alert in alerts_to_send:
                    try:
                        await dispatcher.dispatch(alert)
                    except Exception as e:
                        self.log.error(f"Failed to dispatch alert: {e}")

            result.success = True
            log_collector_event(
                collector_type=self.source.type.value,
                source_name=self.source.name,
                event="Collection completed",
                items_collected=result.items_collected,
                items_new=result.items_new,
            )

        except Exception as e:
            self.log.exception(f"Collection failed: {e}")
            result.error = str(e)

            # Update source error status
            try:
                async with get_session() as session:
                    await self._update_source_status(session, success=False, error=str(e))
                    await session.commit()
            except Exception:
                pass

        return result

    def _create_item_model(
        self,
        collected: CollectedItem,
        filter_result: Any,
        enrichment: Any,
        score: float,
    ) -> Item:
        """Create an Item model from collected data."""
        import uuid

        item = Item()
        item.id = str(uuid.uuid4())
        item.source_id = self.source.id
        item.guid = collected.guid
        item.content_hash = collected.content_hash
        item.title = collected.title
        item.url = collected.url
        item.author = collected.author
        item.content = collected.content
        item.summary = collected.summary or enrichment.summary
        item.image_url = collected.image_url
        item.media_urls = collected.media_urls
        item.published_at = collected.published_at
        item.collected_at = collected.collected_at
        item.language = enrichment.language or collected.language
        item.keywords = enrichment.keywords
        item.sentiment = enrichment.sentiment
        item.sentiment_score = enrichment.sentiment_score
        item.relevance_score = score
        item.matched_filters = filter_result.matched_filter_ids
        item.status = ItemStatus.NEW

        if filter_result.highlighted:
            item.starred = True

        if filter_result.tags:
            item.user_tags = filter_result.tags

        return item

    async def _update_source_status(
        self,
        session: AsyncSession,
        success: bool,
        error: str | None = None,
    ) -> None:
        """Update source status after collection."""
        current_time = now()

        stmt = (
            update(Source)
            .where(Source.id == self.source.id)
            .values(
                last_check=current_time,
                last_success=current_time if success else Source.last_success,
                last_error=error if not success else None,
                consecutive_errors=(
                    0 if success
                    else Source.consecutive_errors + 1
                ),
            )
        )
        await session.execute(stmt)


class Scheduler:
    """
    Main scheduler for SentinelPi.

    Manages all periodic jobs including:
    - Source collection
    - Daily/weekly reports
    - Database maintenance
    """

    def __init__(self) -> None:
        self._scheduler = AsyncIOScheduler()
        self._running = False
        self._collection_semaphore: asyncio.Semaphore | None = None

        settings = get_settings()
        self._max_concurrent = settings.collection.max_concurrent_collectors
        self._check_interval = settings.scheduler.check_interval_seconds

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        log.info("Starting scheduler...")

        # Initialize
        await init_database()
        setup_channels()

        self._collection_semaphore = asyncio.Semaphore(self._max_concurrent)

        # Schedule jobs
        await self._schedule_collection_jobs()
        self._schedule_maintenance_jobs()
        self._schedule_report_jobs()
        self._schedule_learning_jobs()

        # Start scheduler
        self._scheduler.start()
        self._running = True

        log.info("Scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self._running:
            return

        log.info("Stopping scheduler...")

        self._scheduler.shutdown(wait=True)
        self._running = False

        # Flush any pending alerts
        dispatcher = get_dispatcher()
        await dispatcher.flush()

        log.info("Scheduler stopped")

    async def _schedule_collection_jobs(self) -> None:
        """Schedule collection jobs for all sources."""
        sources_config = load_sources_config()
        sources_list = sources_config.get("sources", [])

        async with get_session() as session:
            # Sync sources from config to database
            for source_config in sources_list:
                await self._sync_source(session, source_config)

            await session.commit()

            # Load all enabled sources
            result = await session.execute(
                select(Source).where(Source.enabled == True)
            )
            sources = result.scalars().all()

        # Schedule each source
        for source in sources:
            self._schedule_source_collection(source)

        log.info(f"Scheduled {len(sources)} collection jobs")

    async def _sync_source(self, session: AsyncSession, config: dict) -> None:
        """Sync a source from config to database."""
        import hashlib
        import uuid

        # Generate deterministic ID from name + URL
        source_key = f"{config.get('name', '')}:{config.get('url', '')}"
        source_id = hashlib.sha256(source_key.encode()).hexdigest()[:32]

        # Check if exists
        result = await session.execute(
            select(Source).where(Source.id == source_id)
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update
            existing.name = config.get("name", existing.name)
            existing.url = config.get("url", existing.url)
            existing.enabled = config.get("enabled", True)
            existing.interval_minutes = config.get("interval_minutes", 60)
            existing.priority = config.get("priority", 2)
            existing.category = config.get("category")
            existing.tags = config.get("tags", [])
            existing.config = config.get("config", {})
        else:
            # Create
            from src.storage.models import SourceType

            source = Source()
            source.id = source_id
            source.name = config.get("name", "Unnamed")
            source.type = SourceType(config.get("type", "rss"))
            source.url = config.get("url", "")
            source.enabled = config.get("enabled", True)
            source.interval_minutes = config.get("interval_minutes", 60)
            source.priority = config.get("priority", 2)
            source.category = config.get("category")
            source.tags = config.get("tags", [])
            source.config = config.get("config", {})
            session.add(source)

    def _schedule_source_collection(self, source: Source) -> None:
        """Schedule collection for a single source."""
        job_id = f"collect_{source.id}"

        # Remove existing job if any
        if self._scheduler.get_job(job_id):
            self._scheduler.remove_job(job_id)

        # Schedule new job
        self._scheduler.add_job(
            self._run_collection_job,
            trigger=IntervalTrigger(minutes=source.interval_minutes),
            id=job_id,
            args=[source.id],
            name=f"Collect: {source.name}",
            max_instances=1,
            coalesce=True,
        )

        log.debug(f"Scheduled collection for {source.name} every {source.interval_minutes}min")

    async def _run_collection_job(self, source_id: str) -> None:
        """Run a collection job with concurrency control."""
        async with self._collection_semaphore:
            # Reload source from database
            async with get_session() as session:
                result = await session.execute(
                    select(Source).where(Source.id == source_id)
                )
                source = result.scalar_one_or_none()

            if not source or not source.enabled:
                return

            job = CollectionJob(source)
            await job.run()

    def _schedule_maintenance_jobs(self) -> None:
        """Schedule maintenance jobs."""
        settings = get_settings()

        if settings.maintenance.cleanup_enabled:
            cleanup_time = settings.maintenance.cleanup_time
            hour, minute = map(int, cleanup_time.split(":"))

            self._scheduler.add_job(
                self._run_cleanup_job,
                trigger=CronTrigger(hour=hour, minute=minute),
                id="maintenance_cleanup",
                name="Database cleanup",
            )
            log.debug(f"Scheduled cleanup at {cleanup_time}")

        if settings.maintenance.vacuum_enabled:
            # Weekly vacuum on Sunday at 4 AM
            self._scheduler.add_job(
                self._run_vacuum_job,
                trigger=CronTrigger(day_of_week="sun", hour=4),
                id="maintenance_vacuum",
                name="Database vacuum",
            )
            log.debug("Scheduled weekly vacuum")

    async def _run_cleanup_job(self) -> None:
        """Clean up old items from database."""
        settings = get_settings()
        retention_days = settings.maintenance.retention_days

        log.info(f"Running cleanup (retention: {retention_days} days)")

        cutoff = now() - timedelta(days=retention_days)

        async with get_session() as session:
            # Delete old items (cascades to alerts)
            from sqlalchemy import delete

            result = await session.execute(
                delete(Item).where(
                    Item.collected_at < cutoff,
                    Item.starred == False,  # Préserve les items favoris
                )
            )
            deleted = result.rowcount

            await session.commit()

        log.info(f"Cleanup completed: {deleted} items deleted")

    async def _run_vacuum_job(self) -> None:
        """Vacuum the database."""
        from src.storage.database import vacuum_database

        log.info("Running database vacuum")
        await vacuum_database()
        log.info("Vacuum completed")

    def _schedule_report_jobs(self) -> None:
        """Schedule report generation jobs."""
        settings = get_settings()

        # Daily report
        daily_time = settings.scheduler.daily_report_time
        hour, minute = map(int, daily_time.split(":"))

        self._scheduler.add_job(
            self._run_daily_report,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="report_daily",
            name="Daily report",
        )

        # Weekly report
        weekly_day = settings.scheduler.weekly_report_day
        weekly_time = settings.scheduler.weekly_report_time
        w_hour, w_minute = map(int, weekly_time.split(":"))

        self._scheduler.add_job(
            self._run_weekly_report,
            trigger=CronTrigger(day_of_week=weekly_day, hour=w_hour, minute=w_minute),
            id="report_weekly",
            name="Weekly report",
        )

        log.debug(f"Scheduled daily report at {daily_time}")
        log.debug(f"Scheduled weekly report on day {weekly_day} at {weekly_time}")

    async def _run_daily_report(self) -> None:
        """Generate daily report."""
        log.info("Generating daily report")
        try:
            from src.reporting.generator import generate_daily_report
            html_path, pdf_path = await generate_daily_report()
            log.info(f"Daily report generated: {html_path}")

            # Send report via configured alert channels
            await self._send_report_notification(
                title="Rapport quotidien SentinelPi",
                file_path=html_path,
                report_type="daily",
            )
        except Exception as e:
            log.error(f"Failed to generate daily report: {e}")

    async def _run_weekly_report(self) -> None:
        """Generate weekly report."""
        log.info("Generating weekly report")
        try:
            from src.reporting.generator import generate_weekly_report
            html_path, pdf_path = await generate_weekly_report()
            log.info(f"Weekly report generated: {html_path}")

            await self._send_report_notification(
                title="Rapport hebdomadaire SentinelPi",
                file_path=html_path,
                report_type="weekly",
            )
        except Exception as e:
            log.error(f"Failed to generate weekly report: {e}")

    async def _send_report_notification(
        self, title: str, file_path, report_type: str
    ) -> None:
        """Send a notification that a report has been generated."""
        try:
            from src.alerting.dispatcher import AlertPayload
            from src.storage.models import AlertSeverity

            payload = AlertPayload(
                alert_id=f"report-{report_type}-{now().strftime('%Y%m%d')}",
                severity=AlertSeverity.INFO,
                title=title,
                summary=f"Le rapport {report_type} est disponible : {file_path}",
            )

            dispatcher = get_dispatcher()
            await dispatcher.dispatch(payload)
        except Exception as e:
            log.warning(f"Failed to send report notification: {e}")

    def _schedule_learning_jobs(self) -> None:
        """Schedule preference learning jobs."""
        # Batch learning - process ignored items every 6 hours
        self._scheduler.add_job(
            self._run_batch_learning,
            trigger=IntervalTrigger(hours=6),
            id="learning_batch",
            name="Batch preference learning",
        )

        # Preference decay - run daily at 2 AM
        self._scheduler.add_job(
            self._run_preference_decay,
            trigger=CronTrigger(hour=2, minute=0),
            id="learning_decay",
            name="Preference decay",
        )

        log.debug("Scheduled learning jobs")

    async def _run_batch_learning(self) -> None:
        """Run batch learning for ignored items."""
        log.info("Running batch preference learning")
        try:
            learner = get_preference_learner()
            processed = await learner.run_batch_learning()
            log.info(f"Batch learning completed: {processed} items processed")
        except Exception as e:
            log.error(f"Batch learning failed: {e}")

    async def _run_preference_decay(self) -> None:
        """Apply time decay to preference weights."""
        log.info("Running preference decay")
        try:
            learner = get_preference_learner()
            decayed = await learner.apply_decay()
            log.info(f"Preference decay completed: {decayed} preferences decayed")
        except Exception as e:
            log.error(f"Preference decay failed: {e}")

    async def run_now(self, source_id: str | None = None) -> None:
        """
        Run collection immediately.

        Args:
            source_id: Specific source to collect, or None for all.
        """
        if source_id:
            await self._run_collection_job(source_id)
        else:
            async with get_session() as session:
                result = await session.execute(
                    select(Source).where(Source.enabled == True)
                )
                sources = result.scalars().all()

            tasks = [self._run_collection_job(s.id) for s in sources]
            await asyncio.gather(*tasks, return_exceptions=True)


# Global scheduler instance
_scheduler: Scheduler | None = None


def get_scheduler() -> Scheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = Scheduler()
    return _scheduler


async def start_scheduler() -> None:
    """Start the global scheduler."""
    scheduler = get_scheduler()
    await scheduler.start()


async def stop_scheduler() -> None:
    """Stop the global scheduler."""
    global _scheduler
    if _scheduler:
        await _scheduler.stop()
        _scheduler = None
