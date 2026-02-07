"""Tests for the report generator."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from src.reporting.generator import ReportData, ReportGenerator


class TestReportData:
    def test_initial_values(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        data = ReportData(start, end, "daily")

        assert data.period_start == start
        assert data.period_end == end
        assert data.report_type == "daily"
        assert data.total_items == 0
        assert data.new_items == 0
        assert data.total_alerts == 0
        assert data.top_items == []
        assert data.highlighted_items == []

    def test_period_label_daily(self):
        start = datetime(2026, 1, 15, tzinfo=timezone.utc)
        end = datetime(2026, 1, 16, tzinfo=timezone.utc)
        data = ReportData(start, end, "daily")
        label = data.period_label
        assert "2026" in label

    def test_period_label_weekly(self):
        start = datetime(2026, 1, 8, tzinfo=timezone.utc)
        end = datetime(2026, 1, 15, tzinfo=timezone.utc)
        data = ReportData(start, end, "weekly")
        label = data.period_label
        assert "-" in label or "/" in label

    def test_to_dict(self):
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        data = ReportData(start, end, "daily")
        d = data.to_dict()

        assert "period_start" in d
        assert "period_end" in d
        assert "total_items" in d
        assert "top_items" in d
        assert "alerts_by_severity" in d


class TestReportGenerator:
    def test_init(self):
        generator = ReportGenerator()
        assert generator.output_dir.exists()

    def test_render_html_daily(self):
        generator = ReportGenerator()
        start = datetime(2026, 1, 1, tzinfo=timezone.utc)
        end = datetime(2026, 1, 2, tzinfo=timezone.utc)
        data = ReportData(start, end, "daily")
        data.total_items = 42
        data.total_alerts = 3

        html = generator.render_html(data)
        assert isinstance(html, str)
        assert len(html) > 0

    def test_render_html_weekly(self):
        generator = ReportGenerator()
        start = datetime(2026, 1, 8, tzinfo=timezone.utc)
        end = datetime(2026, 1, 15, tzinfo=timezone.utc)
        data = ReportData(start, end, "weekly")

        html = generator.render_html(data)
        assert isinstance(html, str)

    def test_save_html(self, tmp_path):
        generator = ReportGenerator()
        generator.output_dir = tmp_path

        html = "<html><body>Test report</body></html>"
        path = generator.save_html(html, "test_report")

        assert path.exists()
        assert path.name == "test_report.html"
        assert path.read_text() == html
