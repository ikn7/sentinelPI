"""
Tests for the scoring processor.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from src.collectors.base import CollectedItem
from src.processors.filter import FilterResult
from src.processors.scorer import (
    ScoreBreakdown,
    ScoredItem,
    Scorer,
    ScoringWeights,
    score_and_rank,
)


@pytest.fixture
def recent_item() -> CollectedItem:
    """Create a recent item."""
    return CollectedItem(
        guid="recent-item",
        title="Recent News Article",
        content="This is a recent article with good content. " * 50,
        author="Author Name",
        image_url="https://example.com/image.jpg",
        published_at=datetime.now(timezone.utc) - timedelta(hours=1),
    )


@pytest.fixture
def old_item() -> CollectedItem:
    """Create an old item."""
    return CollectedItem(
        guid="old-item",
        title="Old News Article",
        content="This is an older article.",
        published_at=datetime.now(timezone.utc) - timedelta(days=7),
    )


@pytest.fixture
def minimal_item() -> CollectedItem:
    """Create a minimal item with little content."""
    return CollectedItem(
        guid="minimal-item",
        title="Minimal",
    )


class TestScorer:
    """Tests for Scorer."""

    def test_score_basic_item(self, recent_item):
        """Test scoring a basic item."""
        scorer = Scorer()
        scored = scorer.score_item(recent_item)

        assert scored.score > 0
        assert scored.breakdown.base_score == 50.0
        assert scored.breakdown.recency_score > 0
        assert scored.breakdown.quality_score > 0

    def test_recency_affects_score(self, recent_item, old_item):
        """Test that recent items score higher."""
        scorer = Scorer()

        recent_scored = scorer.score_item(recent_item)
        old_scored = scorer.score_item(old_item)

        assert recent_scored.breakdown.recency_score > old_scored.breakdown.recency_score
        assert recent_scored.score > old_scored.score

    def test_content_quality_affects_score(self, recent_item, minimal_item):
        """Test that content quality affects score."""
        scorer = Scorer()

        # Set same published time for fair comparison
        now = datetime.now(timezone.utc)
        recent_item.published_at = now
        minimal_item.published_at = now

        full_scored = scorer.score_item(recent_item)
        minimal_scored = scorer.score_item(minimal_item)

        assert full_scored.breakdown.quality_score > minimal_scored.breakdown.quality_score

    def test_priority_affects_score(self, recent_item):
        """Test that source priority affects score."""
        scorer = Scorer()

        high_priority = scorer.score_item(recent_item, source_priority=1)
        normal_priority = scorer.score_item(recent_item, source_priority=2)
        low_priority = scorer.score_item(recent_item, source_priority=3)

        assert high_priority.breakdown.priority_score > normal_priority.breakdown.priority_score
        assert normal_priority.breakdown.priority_score > low_priority.breakdown.priority_score

    def test_filter_result_affects_score(self, recent_item):
        """Test that filter results affect score."""
        scorer = Scorer()

        # Create a filter result with score modifier
        filter_result = FilterResult(item=recent_item)
        filter_result.total_score_modifier = 50.0
        filter_result.highlighted = True

        scored_with_filter = scorer.score_item(recent_item, filter_result=filter_result)
        scored_without_filter = scorer.score_item(recent_item)

        assert scored_with_filter.breakdown.filter_score == 50.0
        assert scored_with_filter.breakdown.highlight_score > 0
        assert scored_with_filter.score > scored_without_filter.score

    def test_custom_scorer(self, recent_item):
        """Test custom scoring function."""
        scorer = Scorer()

        # Add custom scorer that gives bonus for AI-related content
        def ai_bonus(item: CollectedItem, context: dict) -> float:
            if "ai" in item.title.lower() or "artificial" in (item.content or "").lower():
                return 25.0
            return 0.0

        scorer.register_custom_scorer(ai_bonus)

        # Item without AI content
        scored = scorer.score_item(recent_item)
        assert scored.breakdown.custom_score == 0.0

        # Item with AI content
        ai_item = CollectedItem(
            guid="ai-item",
            title="AI Revolution",
            content="Artificial intelligence is changing...",
            published_at=datetime.now(timezone.utc),
        )
        ai_scored = scorer.score_item(ai_item)
        assert ai_scored.breakdown.custom_score == 25.0

    def test_rank_items(self, recent_item, old_item, minimal_item):
        """Test ranking items by score."""
        scorer = Scorer()

        items = [old_item, minimal_item, recent_item]
        scored_items = scorer.score_items(items)
        ranked = scorer.rank_items(scored_items)

        # Recent item should be first (highest score)
        assert ranked[0].item.guid == recent_item.guid
        # Scores should be in descending order
        assert all(
            ranked[i].score >= ranked[i + 1].score
            for i in range(len(ranked) - 1)
        )

    def test_custom_weights(self, recent_item):
        """Test custom scoring weights."""
        # High recency weight
        weights = ScoringWeights(
            recency_weight=100.0,
            priority_weight=0.0,
            has_content_bonus=0.0,
        )
        scorer = Scorer(weights)
        scored = scorer.score_item(recent_item)

        assert scored.breakdown.recency_score > 50  # Higher due to weight


class TestScoreAndRank:
    """Tests for score_and_rank convenience function."""

    def test_score_and_rank(self, recent_item, old_item):
        """Test the convenience function."""
        items = [old_item, recent_item]
        ranked = score_and_rank(items)

        assert len(ranked) == 2
        # Recent should be first
        assert ranked[0].item.guid == recent_item.guid
        assert ranked[1].item.guid == old_item.guid


class TestScoreBreakdown:
    """Tests for ScoreBreakdown."""

    def test_total_calculation(self):
        """Test total score calculation."""
        breakdown = ScoreBreakdown(
            base_score=50.0,
            filter_score=25.0,
            recency_score=15.0,
            priority_score=10.0,
            quality_score=5.0,
            highlight_score=30.0,
            custom_score=10.0,
        )

        assert breakdown.total == 145.0

    def test_to_dict(self):
        """Test conversion to dictionary."""
        breakdown = ScoreBreakdown(base_score=50.0)
        d = breakdown.to_dict()

        assert "base" in d
        assert "total" in d
        assert d["base"] == 50.0
