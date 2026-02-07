"""
Tests for the filter engine.
"""

from __future__ import annotations

import pytest

from src.collectors.base import CollectedItem
from src.processors.filter import (
    ConditionEvaluator,
    FilterEngine,
    FilterMatch,
    FilterResult,
    MatchResult,
    create_filter_from_config,
)
from src.storage.models import Filter, FilterAction


@pytest.fixture
def sample_item() -> CollectedItem:
    """Create a sample item for testing."""
    return CollectedItem(
        guid="test-guid-123",
        title="Breaking News: AI Startup Raises $50M in Series A",
        content="A new artificial intelligence company has secured funding...",
        summary="AI startup funding news",
        author="John Reporter",
        url="https://example.com/ai-startup-funding",
    )


@pytest.fixture
def sample_item_fr() -> CollectedItem:
    """Create a French sample item."""
    return CollectedItem(
        guid="test-guid-fr",
        title="Intelligence artificielle : une startup lève 50M€",
        content="Une nouvelle entreprise spécialisée dans l'intelligence artificielle...",
        author="Jean Journaliste",
    )


class TestConditionEvaluator:
    """Tests for ConditionEvaluator."""

    def test_keywords_contains_match(self, sample_item):
        """Test keyword contains matching."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "keywords",
            "field": "title",
            "operator": "contains",
            "value": ["AI", "startup"],
        }

        result, field, value = evaluator.evaluate(sample_item, conditions)

        assert result == MatchResult.MATCH
        assert field == "title"

    def test_keywords_no_match(self, sample_item):
        """Test keyword no match."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "keywords",
            "field": "title",
            "operator": "contains",
            "value": ["blockchain", "crypto"],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.NO_MATCH

    def test_keywords_case_insensitive(self, sample_item):
        """Test case-insensitive keyword matching."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "keywords",
            "field": "title",
            "operator": "contains",
            "value": ["breaking news"],
            "case_sensitive": False,
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.MATCH

    def test_keywords_not_contains(self, sample_item):
        """Test not_contains operator."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "keywords",
            "field": "title",
            "operator": "not_contains",
            "value": ["blockchain"],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.MATCH

    def test_regex_match(self, sample_item):
        """Test regex matching."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "regex",
            "field": "title",
            "operator": "matches",
            "value": r"\$\d+M",  # Match $XXM format
        }

        result, field, value = evaluator.evaluate(sample_item, conditions)

        assert result == MatchResult.MATCH
        assert value == "$50M"

    def test_regex_no_match(self, sample_item):
        """Test regex no match."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "regex",
            "field": "title",
            "operator": "matches",
            "value": r"\d{4}-\d{2}-\d{2}",  # Date format
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.NO_MATCH

    def test_compound_and(self, sample_item):
        """Test compound AND conditions."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "compound",
            "logic": "and",
            "conditions": [
                {"type": "keywords", "field": "title", "value": ["AI"]},
                {"type": "keywords", "field": "title", "value": ["Series A"]},
            ],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.MATCH

    def test_compound_and_partial_match(self, sample_item):
        """Test compound AND with partial match fails."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "compound",
            "logic": "and",
            "conditions": [
                {"type": "keywords", "field": "title", "value": ["AI"]},
                {"type": "keywords", "field": "title", "value": ["Series B"]},  # Not present
            ],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.NO_MATCH

    def test_compound_or(self, sample_item):
        """Test compound OR conditions."""
        evaluator = ConditionEvaluator()

        conditions = {
            "type": "compound",
            "logic": "or",
            "conditions": [
                {"type": "keywords", "field": "title", "value": ["blockchain"]},  # No match
                {"type": "keywords", "field": "title", "value": ["AI"]},  # Match
            ],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.MATCH

    def test_field_all(self, sample_item):
        """Test matching against all fields."""
        evaluator = ConditionEvaluator()

        # "funding" is in content, not title
        conditions = {
            "type": "keywords",
            "field": "all",
            "value": ["funding"],
        }

        result, _, _ = evaluator.evaluate(sample_item, conditions)
        assert result == MatchResult.MATCH


class TestFilterEngine:
    """Tests for FilterEngine."""

    def test_process_item_highlight(self, sample_item):
        """Test processing with highlight action."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "AI Highlight"
        filter_obj.enabled = True
        filter_obj.priority = 100
        filter_obj.action = FilterAction.HIGHLIGHT
        filter_obj.conditions = {
            "type": "keywords",
            "field": "title",
            "value": ["AI"],
        }
        filter_obj.score_modifier = 50.0
        filter_obj.action_params = {}

        engine = FilterEngine([filter_obj])
        result = engine.process_item(sample_item)

        assert result.highlighted is True
        assert len(result.matches) == 1
        assert result.total_score_modifier == 50.0

    def test_process_item_exclude(self, sample_item):
        """Test processing with exclude action."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "Exclude Spam"
        filter_obj.enabled = True
        filter_obj.priority = 1
        filter_obj.action = FilterAction.EXCLUDE
        filter_obj.conditions = {
            "type": "keywords",
            "field": "title",
            "value": ["Breaking News"],
        }
        filter_obj.score_modifier = 0.0
        filter_obj.action_params = {}

        engine = FilterEngine([filter_obj])
        result = engine.process_item(sample_item)

        assert result.excluded is True

    def test_process_item_tag(self, sample_item):
        """Test processing with tag action."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "Tag Funding"
        filter_obj.enabled = True
        filter_obj.priority = 100
        filter_obj.action = FilterAction.TAG
        filter_obj.conditions = {
            "type": "keywords",
            "field": "all",
            "value": ["funding", "Series A"],
        }
        filter_obj.score_modifier = 0.0
        filter_obj.action_params = {"tag": "funding"}

        engine = FilterEngine([filter_obj])
        result = engine.process_item(sample_item)

        assert "funding" in result.tags

    def test_process_item_alert(self, sample_item):
        """Test processing with alert action."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "Alert Major Funding"
        filter_obj.enabled = True
        filter_obj.priority = 100
        filter_obj.action = FilterAction.ALERT
        filter_obj.conditions = {
            "type": "regex",
            "field": "title",
            "value": r"\$\d+M",
        }
        filter_obj.score_modifier = 100.0
        filter_obj.action_params = {"severity": "notice"}

        engine = FilterEngine([filter_obj])
        result = engine.process_item(sample_item)

        assert result.should_alert is True
        assert len(result.alerts) == 1
        assert result.alerts[0].action_params.get("severity") == "notice"

    def test_process_items_batch(self, sample_item, sample_item_fr):
        """Test batch processing."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "AI Filter"
        filter_obj.enabled = True
        filter_obj.priority = 100
        filter_obj.action = FilterAction.HIGHLIGHT
        filter_obj.conditions = {
            "type": "keywords",
            "field": "title",
            "value": ["AI", "intelligence artificielle"],
        }
        filter_obj.score_modifier = 30.0
        filter_obj.action_params = {}

        engine = FilterEngine([filter_obj])
        results, included, excluded = engine.process_items([sample_item, sample_item_fr])

        assert len(results) == 2
        assert included == 2
        assert excluded == 0
        assert all(r.highlighted for r in results)

    def test_disabled_filter_ignored(self, sample_item):
        """Test that disabled filters are ignored."""
        filter_obj = Filter()
        filter_obj.id = "test-filter"
        filter_obj.name = "Disabled Filter"
        filter_obj.enabled = False
        filter_obj.priority = 100
        filter_obj.action = FilterAction.EXCLUDE
        filter_obj.conditions = {
            "type": "keywords",
            "field": "title",
            "value": ["AI"],
        }
        filter_obj.score_modifier = 0.0
        filter_obj.action_params = {}

        engine = FilterEngine([filter_obj])
        result = engine.process_item(sample_item)

        assert result.excluded is False
        assert len(result.matches) == 0


class TestCreateFilterFromConfig:
    """Tests for create_filter_from_config."""

    def test_create_basic_filter(self):
        """Test creating a filter from config."""
        config = {
            "name": "Test Filter",
            "description": "A test filter",
            "action": "highlight",
            "conditions": {
                "type": "keywords",
                "field": "title",
                "value": ["test"],
            },
            "score_modifier": 25.0,
            "priority": 50,
        }

        filter_obj = create_filter_from_config(config)

        assert filter_obj.name == "Test Filter"
        assert filter_obj.action == FilterAction.HIGHLIGHT
        assert filter_obj.score_modifier == 25.0
        assert filter_obj.priority == 50
        assert filter_obj.enabled is True

    def test_create_alert_filter(self):
        """Test creating an alert filter."""
        config = {
            "name": "Critical Alert",
            "action": "alert",
            "action_params": {"severity": "critical"},
            "conditions": {
                "type": "keywords",
                "value": ["breach", "hack"],
            },
        }

        filter_obj = create_filter_from_config(config)

        assert filter_obj.action == FilterAction.ALERT
        assert filter_obj.action_params.get("severity") == "critical"
