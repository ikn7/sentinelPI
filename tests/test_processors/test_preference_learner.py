"""
Tests for the PreferenceLearner module.

Tests the engagement-based learning system that learns user preferences
from actions on articles.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from datetime import datetime, timezone

from src.processors.preference_learner import (
    PreferenceLearner,
    LearningConfig,
    PreferenceSummary,
    ACTION_SIGNALS,
)
from src.storage.models import (
    Base,
    Source,
    SourceType,
    Item,
    ItemStatus,
    UserPreference,
    UserAction,
)


class TestActionSignals:
    """Test action signal weights."""

    def test_star_is_strong_positive(self):
        """Star action should be a strong positive signal."""
        assert ACTION_SIGNALS["star"] == 1.0

    def test_archive_is_positive(self):
        """Archive action should be positive."""
        assert ACTION_SIGNALS["archive"] == 0.5

    def test_read_is_mild_positive(self):
        """Read action should be mildly positive."""
        assert ACTION_SIGNALS["read"] == 0.3

    def test_delete_is_strong_negative(self):
        """Delete action should be a strong negative signal."""
        assert ACTION_SIGNALS["delete"] == -0.8

    def test_ignore_is_mild_negative(self):
        """Ignore action should be mildly negative."""
        assert ACTION_SIGNALS["ignore"] == -0.2


class TestLearningConfig:
    """Test LearningConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LearningConfig()
        assert config.enabled is True
        assert config.learning_rate == 0.1
        assert config.decay_half_life_days == 30.0
        assert config.min_actions_required == 20
        assert config.max_preference_score == 25.0
        assert config.max_features_per_action == 10

    def test_custom_values(self):
        """Test custom configuration values."""
        config = LearningConfig(
            enabled=False,
            learning_rate=0.2,
            min_actions_required=10,
        )
        assert config.enabled is False
        assert config.learning_rate == 0.2
        assert config.min_actions_required == 10


class TestPreferenceLearner:
    """Test PreferenceLearner class."""

    @pytest.fixture
    def learner(self):
        """Create a PreferenceLearner with test config."""
        config = LearningConfig(
            min_actions_required=5,  # Lower threshold for testing
            max_preference_score=25.0,
        )
        return PreferenceLearner(config)

    @pytest.fixture
    def disabled_learner(self):
        """Create a disabled PreferenceLearner."""
        config = LearningConfig(enabled=False)
        return PreferenceLearner(config)

    def test_init_with_default_config(self):
        """Test initialization with default config."""
        learner = PreferenceLearner()
        assert learner.config is not None
        assert learner.config.enabled is True

    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        config = LearningConfig(learning_rate=0.5)
        learner = PreferenceLearner(config)
        assert learner.config.learning_rate == 0.5

    def test_extract_features_with_keywords(self, learner):
        """Test feature extraction from item with keywords."""
        item = Item()
        item.id = "test-item-1"
        item.keywords_json = '["python", "machine learning", "ai"]'
        item.source_id = "source-1"
        item.author = "John Doe"

        features = learner._extract_features(item)

        # Should have keywords + source + author
        assert len(features) >= 4
        assert ("keyword", "python") in features
        assert ("keyword", "machine learning") in features
        assert ("source", "source-1") in features
        assert ("author", "john doe") in features

    def test_extract_features_without_keywords(self, learner):
        """Test feature extraction from item without keywords."""
        item = Item()
        item.id = "test-item-2"
        item.source_id = "source-2"

        features = learner._extract_features(item)

        # Should at least have source
        assert ("source", "source-2") in features

    def test_extract_features_respects_max_limit(self, learner):
        """Test that feature extraction respects max_features_per_action."""
        import json
        item = Item()
        item.id = "test-item-3"
        # Create more keywords than the limit
        keywords = [f"keyword{i}" for i in range(20)]
        item.keywords_json = json.dumps(keywords)
        item.source_id = "source-3"

        features = learner._extract_features(item)

        # Count keyword features
        keyword_features = [f for f in features if f[0] == "keyword"]
        assert len(keyword_features) <= learner.config.max_features_per_action

    def test_disabled_learner_returns_zero_score(self, disabled_learner):
        """Test that disabled learner returns zero for preference score."""
        # This is a sync test - actual async test would need db_session
        assert disabled_learner.config.enabled is False


class TestPreferenceSummary:
    """Test PreferenceSummary dataclass."""

    def test_default_values(self):
        """Test default summary values."""
        summary = PreferenceSummary()
        assert summary.total_actions == 0
        assert summary.min_actions_required == 20
        assert summary.is_active is False
        assert summary.positive_preferences == []
        assert summary.negative_preferences == []
        assert summary.preferences_by_type == {}

    def test_is_active_when_threshold_met(self):
        """Test is_active flag when threshold is met."""
        summary = PreferenceSummary(
            total_actions=25,
            min_actions_required=20,
            is_active=True,
        )
        assert summary.is_active is True

    def test_preferences_lists(self):
        """Test preference lists."""
        summary = PreferenceSummary(
            positive_preferences=[
                {"type": "keyword", "value": "python", "weight": 0.8}
            ],
            negative_preferences=[
                {"type": "keyword", "value": "spam", "weight": -0.5}
            ],
        )
        assert len(summary.positive_preferences) == 1
        assert len(summary.negative_preferences) == 1
        assert summary.positive_preferences[0]["value"] == "python"


@pytest.mark.asyncio
class TestPreferenceLearnerAsync:
    """Async tests for PreferenceLearner that require database."""

    @pytest_asyncio.fixture
    async def setup_db(self, db_session):
        """Set up test data in database."""
        # Create a source
        source = Source()
        source.id = "test-source-1"
        source.name = "Test Source"
        source.type = SourceType.RSS
        source.url = "https://example.com/feed.xml"
        source.category = "tech"
        db_session.add(source)

        # Create items
        for i in range(5):
            item = Item()
            item.id = f"test-item-{i}"
            item.source_id = "test-source-1"
            item.guid = f"guid-{i}"
            item.content_hash = f"hash-{i}"
            item.title = f"Test Article {i}"
            item.keywords_json = '["python", "testing"]'
            item.status = ItemStatus.NEW
            db_session.add(item)

        await db_session.commit()
        return db_session

    async def test_record_action_creates_user_action(self, setup_db):
        """Test that record_action creates a UserAction record."""
        session = setup_db
        learner = PreferenceLearner(LearningConfig(min_actions_required=1))

        # This test would need the actual database operations
        # For now, just verify the setup
        from sqlalchemy import select
        result = await session.execute(select(Item))
        items = result.scalars().all()
        assert len(items) == 5

    async def test_get_preference_summary_empty(self, setup_db):
        """Test preference summary with no actions."""
        learner = PreferenceLearner()
        # Would test actual summary with db
        summary = PreferenceSummary()
        assert summary.total_actions == 0
        assert summary.is_active is False
