"""
Filter engine for SentinelPi.

Evaluates items against filter rules and applies actions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Sequence

from src.collectors.base import CollectedItem
from src.storage.models import Filter, FilterAction
from src.utils.logging import create_logger

log = create_logger("processors.filter")


class MatchResult(Enum):
    """Result of a filter match."""
    NO_MATCH = "no_match"
    MATCH = "match"
    ERROR = "error"


@dataclass
class FilterMatch:
    """Represents a filter that matched an item."""
    filter_id: str
    filter_name: str
    action: FilterAction
    action_params: dict[str, Any]
    score_modifier: float
    matched_field: str | None = None
    matched_value: str | None = None


@dataclass
class FilterResult:
    """Result of filtering an item."""
    item: CollectedItem
    matches: list[FilterMatch] = field(default_factory=list)
    excluded: bool = False
    highlighted: bool = False
    tags: list[str] = field(default_factory=list)
    alerts: list[FilterMatch] = field(default_factory=list)
    total_score_modifier: float = 0.0

    @property
    def should_alert(self) -> bool:
        """Check if any alerts should be triggered."""
        return len(self.alerts) > 0

    @property
    def matched_filter_ids(self) -> list[str]:
        """Get list of matched filter IDs."""
        return [m.filter_id for m in self.matches]


class ConditionEvaluator:
    """
    Evaluates filter conditions against item content.

    Supports:
    - keywords: List of keywords to match
    - regex: Regular expression pattern
    - compound: Combination of conditions with AND/OR logic
    """

    def __init__(self) -> None:
        """Initialize the evaluator."""
        self._custom_functions: dict[str, Callable] = {}

    def register_custom_function(
        self,
        name: str,
        func: Callable[[CollectedItem, dict], bool],
    ) -> None:
        """
        Register a custom condition function.

        Args:
            name: Function name to use in conditions.
            func: Function taking (item, params) and returning bool.
        """
        self._custom_functions[name] = func

    def evaluate(
        self,
        item: CollectedItem,
        conditions: dict[str, Any],
    ) -> tuple[MatchResult, str | None, str | None]:
        """
        Evaluate conditions against an item.

        Args:
            item: The item to evaluate.
            conditions: Condition configuration dict.

        Returns:
            Tuple of (result, matched_field, matched_value).
        """
        condition_type = conditions.get("type", "keywords")

        try:
            if condition_type == "keywords":
                return self._evaluate_keywords(item, conditions)
            elif condition_type == "regex":
                return self._evaluate_regex(item, conditions)
            elif condition_type == "compound":
                return self._evaluate_compound(item, conditions)
            elif condition_type == "custom":
                return self._evaluate_custom(item, conditions)
            else:
                log.warning(f"Unknown condition type: {condition_type}")
                return MatchResult.ERROR, None, None

        except Exception as e:
            log.error(f"Error evaluating condition: {e}")
            return MatchResult.ERROR, None, None

    def _get_field_value(self, item: CollectedItem, field: str) -> str:
        """Get the text content of a field from an item."""
        if field == "all":
            parts = [
                item.title or "",
                item.content or "",
                item.summary or "",
                item.author or "",
            ]
            return " ".join(parts)
        elif field == "title":
            return item.title or ""
        elif field == "content":
            return item.content or item.summary or ""
        elif field == "author":
            return item.author or ""
        elif field == "url":
            return item.url or ""
        else:
            return ""

    def _evaluate_keywords(
        self,
        item: CollectedItem,
        conditions: dict[str, Any],
    ) -> tuple[MatchResult, str | None, str | None]:
        """Evaluate keyword conditions."""
        field = conditions.get("field", "all")
        operator = conditions.get("operator", "contains")
        keywords = conditions.get("value", [])
        case_sensitive = conditions.get("case_sensitive", False)

        if isinstance(keywords, str):
            keywords = [keywords]

        text = self._get_field_value(item, field)

        if not case_sensitive:
            text = text.lower()
            keywords = [k.lower() for k in keywords]

        for keyword in keywords:
            matched = False

            if operator == "contains":
                matched = keyword in text
            elif operator == "not_contains":
                matched = keyword not in text
            elif operator == "starts_with":
                matched = text.startswith(keyword)
            elif operator == "ends_with":
                matched = text.endswith(keyword)
            elif operator == "equals":
                matched = text == keyword

            if matched and operator != "not_contains":
                return MatchResult.MATCH, field, keyword
            elif not matched and operator == "not_contains":
                # For not_contains, all keywords must be absent
                continue

        # For not_contains, if we get here all keywords were absent
        if operator == "not_contains":
            return MatchResult.MATCH, field, None

        return MatchResult.NO_MATCH, None, None

    def _evaluate_regex(
        self,
        item: CollectedItem,
        conditions: dict[str, Any],
    ) -> tuple[MatchResult, str | None, str | None]:
        """Evaluate regex conditions."""
        field = conditions.get("field", "all")
        operator = conditions.get("operator", "matches")
        pattern = conditions.get("value", "")
        case_sensitive = conditions.get("case_sensitive", False)

        text = self._get_field_value(item, field)

        flags = 0 if case_sensitive else re.IGNORECASE

        try:
            regex = re.compile(pattern, flags)

            if operator == "matches":
                match = regex.search(text)
                if match:
                    return MatchResult.MATCH, field, match.group(0)
            elif operator == "not_matches":
                if not regex.search(text):
                    return MatchResult.MATCH, field, None

        except re.error as e:
            log.warning(f"Invalid regex pattern '{pattern}': {e}")
            return MatchResult.ERROR, None, None

        return MatchResult.NO_MATCH, None, None

    def _evaluate_compound(
        self,
        item: CollectedItem,
        conditions: dict[str, Any],
    ) -> tuple[MatchResult, str | None, str | None]:
        """Evaluate compound conditions (AND/OR)."""
        logic = conditions.get("logic", "and").lower()
        sub_conditions = conditions.get("conditions", [])

        if not sub_conditions:
            return MatchResult.NO_MATCH, None, None

        results = []
        matched_field = None
        matched_value = None

        for sub_cond in sub_conditions:
            result, field, value = self.evaluate(item, sub_cond)
            results.append(result == MatchResult.MATCH)

            if result == MatchResult.MATCH and matched_field is None:
                matched_field = field
                matched_value = value

        if logic == "and":
            if all(results):
                return MatchResult.MATCH, matched_field, matched_value
        elif logic == "or":
            if any(results):
                return MatchResult.MATCH, matched_field, matched_value

        return MatchResult.NO_MATCH, None, None

    def _evaluate_custom(
        self,
        item: CollectedItem,
        conditions: dict[str, Any],
    ) -> tuple[MatchResult, str | None, str | None]:
        """Evaluate custom function conditions."""
        func_name = conditions.get("function")
        params = conditions.get("params", {})

        if func_name not in self._custom_functions:
            log.warning(f"Unknown custom function: {func_name}")
            return MatchResult.ERROR, None, None

        try:
            func = self._custom_functions[func_name]
            if func(item, params):
                return MatchResult.MATCH, "custom", func_name
        except Exception as e:
            log.error(f"Error in custom function '{func_name}': {e}")
            return MatchResult.ERROR, None, None

        return MatchResult.NO_MATCH, None, None


class FilterEngine:
    """
    Main filter engine.

    Applies multiple filters to items and aggregates results.
    """

    def __init__(self, filters: Sequence[Filter] | None = None) -> None:
        """
        Initialize the filter engine.

        Args:
            filters: List of Filter objects to apply.
        """
        self.filters: list[Filter] = list(filters) if filters else []
        self.evaluator = ConditionEvaluator()

        # Sort filters by priority (lower = higher priority)
        self.filters.sort(key=lambda f: f.priority)

    def add_filter(self, filter_obj: Filter) -> None:
        """Add a filter to the engine."""
        self.filters.append(filter_obj)
        self.filters.sort(key=lambda f: f.priority)

    def register_custom_function(
        self,
        name: str,
        func: Callable[[CollectedItem, dict], bool],
    ) -> None:
        """Register a custom condition function."""
        self.evaluator.register_custom_function(name, func)

    def _filter_applies_to_item(
        self,
        filter_obj: Filter,
        item: CollectedItem,
        source_category: str | None = None,
    ) -> bool:
        """Check if a filter should be applied to an item."""
        # Check source ID targeting
        source_ids = filter_obj.source_ids
        if source_ids:
            # We need the source_id from item.extra or context
            item_source_id = item.extra.get("source_id")
            if item_source_id and item_source_id not in source_ids:
                return False

        # Check category targeting
        categories = filter_obj.categories
        if categories and source_category:
            if source_category not in categories:
                return False

        return True

    def apply_filter(
        self,
        filter_obj: Filter,
        item: CollectedItem,
    ) -> FilterMatch | None:
        """
        Apply a single filter to an item.

        Args:
            filter_obj: The filter to apply.
            item: The item to filter.

        Returns:
            FilterMatch if the filter matched, None otherwise.
        """
        if not filter_obj.enabled:
            return None

        conditions = filter_obj.conditions
        if not conditions:
            return None

        result, matched_field, matched_value = self.evaluator.evaluate(
            item, conditions
        )

        if result == MatchResult.MATCH:
            return FilterMatch(
                filter_id=filter_obj.id,
                filter_name=filter_obj.name,
                action=filter_obj.action,
                action_params=filter_obj.action_params,
                score_modifier=filter_obj.score_modifier,
                matched_field=matched_field,
                matched_value=matched_value,
            )

        return None

    def process_item(
        self,
        item: CollectedItem,
        source_category: str | None = None,
    ) -> FilterResult:
        """
        Process an item through all filters.

        Args:
            item: The item to process.
            source_category: Category of the item's source.

        Returns:
            FilterResult with all matches and computed actions.
        """
        result = FilterResult(item=item)

        for filter_obj in self.filters:
            # Check if filter applies to this item
            if not self._filter_applies_to_item(filter_obj, item, source_category):
                continue

            match = self.apply_filter(filter_obj, item)

            if match is None:
                continue

            result.matches.append(match)
            result.total_score_modifier += match.score_modifier

            # Apply action
            if match.action == FilterAction.EXCLUDE:
                result.excluded = True
                # Stop processing on exclude (item won't be kept)
                break

            elif match.action == FilterAction.INCLUDE:
                # Include is the default, no special action needed
                pass

            elif match.action == FilterAction.HIGHLIGHT:
                result.highlighted = True

            elif match.action == FilterAction.TAG:
                tag = match.action_params.get("tag")
                if tag and tag not in result.tags:
                    result.tags.append(tag)

            elif match.action == FilterAction.ALERT:
                result.alerts.append(match)

        return result

    def process_items(
        self,
        items: Sequence[CollectedItem],
        source_category: str | None = None,
    ) -> tuple[list[FilterResult], int, int]:
        """
        Process multiple items through all filters.

        Args:
            items: Items to process.
            source_category: Category of the items' source.

        Returns:
            Tuple of (results, included_count, excluded_count).
        """
        results: list[FilterResult] = []
        included = 0
        excluded = 0

        for item in items:
            result = self.process_item(item, source_category)
            results.append(result)

            if result.excluded:
                excluded += 1
            else:
                included += 1

        log.info(
            f"Filtered {len(items)} items: {included} included, {excluded} excluded"
        )

        return results, included, excluded


def create_filter_from_config(config: dict[str, Any], filter_id: str | None = None) -> Filter:
    """
    Create a Filter object from configuration dict.

    Args:
        config: Filter configuration from YAML.
        filter_id: Optional filter ID (generated if not provided).

    Returns:
        Filter object.
    """
    import uuid

    filter_obj = Filter()
    filter_obj.id = filter_id or str(uuid.uuid4())
    filter_obj.name = config.get("name", "Unnamed Filter")
    filter_obj.description = config.get("description")
    filter_obj.enabled = config.get("enabled", True)
    filter_obj.priority = config.get("priority", 100)
    filter_obj.score_modifier = config.get("score_modifier", 0.0)

    # Action
    action_str = config.get("action", "include")
    filter_obj.action = FilterAction(action_str)
    filter_obj.action_params = config.get("action_params", {})

    # Conditions
    filter_obj.conditions = config.get("conditions", {})

    # Targeting
    filter_obj.source_ids = config.get("source_ids")
    filter_obj.categories = config.get("categories")

    return filter_obj


def load_filters_from_config() -> list[Filter]:
    """
    Load filters from the YAML configuration file.

    Returns:
        List of Filter objects.
    """
    from src.utils.config import load_filters_config

    config = load_filters_config()
    filters_config = config.get("filters", [])

    filters = []
    for i, fc in enumerate(filters_config):
        filter_id = f"config-filter-{i}"
        try:
            filter_obj = create_filter_from_config(fc, filter_id)
            filters.append(filter_obj)
        except Exception as e:
            log.error(f"Failed to load filter '{fc.get('name', i)}': {e}")

    log.info(f"Loaded {len(filters)} filters from configuration")
    return filters
