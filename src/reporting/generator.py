"""
Report generator for SentinelPi.

Generates daily and weekly summary reports in HTML/PDF format.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_session
from src.storage.models import Item, Source, Alert, AlertSeverity, ItemStatus, Report
from src.utils.config import get_settings, PROJECT_ROOT
from src.utils.dates import now, format_date, start_of_day
from src.utils.logging import create_logger

log = create_logger("reporting.generator")

# Template directory
TEMPLATES_DIR = PROJECT_ROOT / "src" / "reporting" / "templates"


class ReportData:
    """Container for report data."""

    def __init__(
        self,
        period_start: datetime,
        period_end: datetime,
        report_type: str = "daily",
    ) -> None:
        self.period_start = period_start
        self.period_end = period_end
        self.report_type = report_type
        self.generated_at = now()

        # Counts
        self.total_items: int = 0
        self.new_items: int = 0
        self.total_alerts: int = 0

        # Breakdowns
        self.items_by_source: list[dict[str, Any]] = []
        self.items_by_category: list[dict[str, Any]] = []
        self.alerts_by_severity: dict[str, int] = {}

        # Top items
        self.top_items: list[dict[str, Any]] = []
        self.highlighted_items: list[dict[str, Any]] = []

        # Sources status
        self.sources_status: list[dict[str, Any]] = []

    @property
    def period_label(self) -> str:
        """Human-readable period label."""
        if self.report_type == "daily":
            return format_date(self.period_start, "%A %d %B %Y")
        elif self.report_type == "weekly":
            return (
                f"{format_date(self.period_start, '%d/%m/%Y')} - "
                f"{format_date(self.period_end, '%d/%m/%Y')}"
            )
        return f"{self.period_start} - {self.period_end}"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template."""
        return {
            "period_start": self.period_start,
            "period_end": self.period_end,
            "period_label": self.period_label,
            "report_type": self.report_type,
            "generated_at": self.generated_at,
            "total_items": self.total_items,
            "new_items": self.new_items,
            "total_alerts": self.total_alerts,
            "items_by_source": self.items_by_source,
            "items_by_category": self.items_by_category,
            "alerts_by_severity": self.alerts_by_severity,
            "top_items": self.top_items,
            "highlighted_items": self.highlighted_items,
            "sources_status": self.sources_status,
        }


class ReportGenerator:
    """
    Generates HTML and PDF reports.

    Uses Jinja2 templates for HTML generation and WeasyPrint for PDF.
    """

    def __init__(self) -> None:
        """Initialize the generator."""
        self.settings = get_settings()
        self.output_dir = PROJECT_ROOT / "data" / "exports"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2 environment
        self._env = Environment(
            loader=FileSystemLoader(str(TEMPLATES_DIR)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        self._env.filters["format_date"] = format_date
        self._env.filters["format_number"] = lambda x: f"{x:,}"

    async def collect_data(
        self,
        period_start: datetime,
        period_end: datetime,
        report_type: str = "daily",
    ) -> ReportData:
        """
        Collect data for the report.

        Args:
            period_start: Start of reporting period.
            period_end: End of reporting period.
            report_type: Type of report (daily, weekly).

        Returns:
            ReportData with collected statistics.
        """
        data = ReportData(period_start, period_end, report_type)

        async with get_session() as session:
            # Total items in period
            result = await session.execute(
                select(func.count(Item.id)).where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                )
            )
            data.total_items = result.scalar() or 0

            # New items (not seen before)
            result = await session.execute(
                select(func.count(Item.id)).where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                    Item.status == ItemStatus.NEW,
                )
            )
            data.new_items = result.scalar() or 0

            # Total alerts
            result = await session.execute(
                select(func.count(Alert.id)).where(
                    Alert.created_at >= period_start,
                    Alert.created_at < period_end,
                )
            )
            data.total_alerts = result.scalar() or 0

            # Items by source
            result = await session.execute(
                select(
                    Source.name,
                    func.count(Item.id).label("count"),
                )
                .join(Item, Item.source_id == Source.id)
                .where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                )
                .group_by(Source.id)
                .order_by(func.count(Item.id).desc())
                .limit(10)
            )
            data.items_by_source = [
                {"source": row[0], "count": row[1]}
                for row in result.all()
            ]

            # Items by category
            result = await session.execute(
                select(
                    Source.category,
                    func.count(Item.id).label("count"),
                )
                .join(Item, Item.source_id == Source.id)
                .where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                    Source.category.isnot(None),
                )
                .group_by(Source.category)
                .order_by(func.count(Item.id).desc())
            )
            data.items_by_category = [
                {"category": row[0] or "Sans catégorie", "count": row[1]}
                for row in result.all()
            ]

            # Alerts by severity
            for severity in AlertSeverity:
                result = await session.execute(
                    select(func.count(Alert.id)).where(
                        Alert.created_at >= period_start,
                        Alert.created_at < period_end,
                        Alert.severity == severity,
                    )
                )
                data.alerts_by_severity[severity.value] = result.scalar() or 0

            # Top items by score
            result = await session.execute(
                select(Item, Source.name)
                .join(Source, Source.id == Item.source_id)
                .where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                )
                .order_by(Item.relevance_score.desc())
                .limit(10)
            )
            data.top_items = [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": source_name,
                    "score": item.relevance_score,
                    "published_at": item.published_at,
                }
                for item, source_name in result.all()
            ]

            # Highlighted items
            result = await session.execute(
                select(Item, Source.name)
                .join(Source, Source.id == Item.source_id)
                .where(
                    Item.collected_at >= period_start,
                    Item.collected_at < period_end,
                    Item.starred == True,
                )
                .order_by(Item.relevance_score.desc())
                .limit(10)
            )
            data.highlighted_items = [
                {
                    "title": item.title,
                    "url": item.url,
                    "source": source_name,
                    "summary": item.summary,
                }
                for item, source_name in result.all()
            ]

            # Sources status
            result = await session.execute(
                select(Source).where(Source.enabled == True)
            )
            sources = result.scalars().all()

            data.sources_status = [
                {
                    "name": s.name,
                    "type": s.type.value,
                    "last_check": s.last_check,
                    "last_success": s.last_success,
                    "errors": s.consecutive_errors,
                    "status": "ok" if s.consecutive_errors == 0 else "error",
                }
                for s in sources
            ]

        return data

    def render_html(self, data: ReportData) -> str:
        """
        Render report as HTML.

        Args:
            data: Report data.

        Returns:
            HTML string.
        """
        template_name = f"{data.report_type}.html.j2"
        template = self._env.get_template(template_name)

        return template.render(**data.to_dict())

    def save_html(self, html_content: str, filename: str) -> Path:
        """
        Save HTML report to file.

        Args:
            html_content: HTML content.
            filename: Output filename (without extension).

        Returns:
            Path to saved file.
        """
        output_path = self.output_dir / f"{filename}.html"
        output_path.write_text(html_content, encoding="utf-8")
        log.info(f"HTML report saved: {output_path}")
        return output_path

    def save_pdf(self, html_content: str, filename: str) -> Path | None:
        """
        Save report as PDF.

        Args:
            html_content: HTML content.
            filename: Output filename (without extension).

        Returns:
            Path to saved file, or None if WeasyPrint not available.
        """
        try:
            from weasyprint import HTML

            output_path = self.output_dir / f"{filename}.pdf"
            HTML(string=html_content).write_pdf(output_path)
            log.info(f"PDF report saved: {output_path}")
            return output_path

        except ImportError:
            log.warning("WeasyPrint not installed, skipping PDF generation")
            return None
        except Exception as e:
            log.error(f"Failed to generate PDF: {e}")
            return None

    async def generate_daily_report(
        self,
        date: datetime | None = None,
    ) -> tuple[Path, Path | None]:
        """
        Generate daily report.

        Args:
            date: Date for the report (defaults to yesterday).

        Returns:
            Tuple of (html_path, pdf_path).
        """
        if date is None:
            date = now() - timedelta(days=1)

        period_start = start_of_day(date)
        period_end = period_start + timedelta(days=1)

        log.info(f"Generating daily report for {format_date(period_start, '%Y-%m-%d')}")

        # Collect data
        data = await self.collect_data(period_start, period_end, "daily")

        # Render
        html_content = self.render_html(data)

        # Save
        filename = f"rapport_quotidien_{format_date(period_start, '%Y%m%d')}"
        html_path = self.save_html(html_content, filename)
        pdf_path = self.save_pdf(html_content, filename)

        # Store report record
        await self._store_report_record(data, html_path)

        return html_path, pdf_path

    async def generate_weekly_report(
        self,
        end_date: datetime | None = None,
    ) -> tuple[Path, Path | None]:
        """
        Generate weekly report.

        Args:
            end_date: End date for the report (defaults to yesterday).

        Returns:
            Tuple of (html_path, pdf_path).
        """
        if end_date is None:
            end_date = now() - timedelta(days=1)

        period_end = start_of_day(end_date) + timedelta(days=1)
        period_start = period_end - timedelta(days=7)

        log.info(
            f"Generating weekly report for "
            f"{format_date(period_start, '%Y-%m-%d')} to {format_date(period_end, '%Y-%m-%d')}"
        )

        # Collect data
        data = await self.collect_data(period_start, period_end, "weekly")

        # Render
        html_content = self.render_html(data)

        # Save
        filename = f"rapport_hebdo_{format_date(period_start, '%Y%m%d')}_{format_date(period_end, '%Y%m%d')}"
        html_path = self.save_html(html_content, filename)
        pdf_path = self.save_pdf(html_content, filename)

        # Store report record
        await self._store_report_record(data, html_path)

        return html_path, pdf_path

    async def _store_report_record(self, data: ReportData, file_path: Path) -> None:
        """Store report metadata in database."""
        import uuid

        async with get_session() as session:
            report = Report()
            report.id = str(uuid.uuid4())
            report.report_type = data.report_type
            report.title = f"Rapport {data.report_type} - {data.period_label}"
            report.period_start = data.period_start
            report.period_end = data.period_end
            report.item_count = data.total_items
            report.alert_count = data.total_alerts
            report.file_path = str(file_path)
            report.stats = {
                "new_items": data.new_items,
                "items_by_source": data.items_by_source,
                "alerts_by_severity": data.alerts_by_severity,
            }

            session.add(report)
            await session.commit()


async def generate_daily_report(date: datetime | None = None) -> tuple[Path, Path | None]:
    """Convenience function to generate daily report."""
    generator = ReportGenerator()
    return await generator.generate_daily_report(date)


async def generate_weekly_report(end_date: datetime | None = None) -> tuple[Path, Path | None]:
    """Convenience function to generate weekly report."""
    generator = ReportGenerator()
    return await generator.generate_weekly_report(end_date)
