"""
Preference learning module for SentinelPi.

Learns user preferences from actions on articles (star, read, archive, delete, ignore)
and adjusts relevance scores accordingly.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select, update, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_session
from src.storage.models import (
    Item,
    UserPreference,
    UserAction,
    LearningState,
)
from src.utils.dates import now
from src.utils.logging import create_logger

log = create_logger("processors.preference_learner")


# =============================================================================
# Signal Weights for Different Actions
# =============================================================================

ACTION_SIGNALS = {
    "star": 1.0,      # Strong positive - "I want more like this"
    "archive": 0.5,   # Positive - Kept for later
    "read": 0.3,      # Mild positive - Engaged with content
    "delete": -0.8,   # Strong negative - Not interested
    "ignore": -0.2,   # Mild negative - Old unread items (batch job)
}


# =============================================================================
# Configuration
# =============================================================================

@dataclass
class LearningConfig:
    """Configuration for preference learning."""
    enabled: bool = True
    learning_rate: float = 0.1
    decay_half_life_days: float = 30.0
    min_actions_required: int = 20
    max_preference_score: float = 25.0
    max_features_per_action: int = 10


# =============================================================================
# Preference Summary
# =============================================================================

@dataclass
class PreferenceSummary:
    """Summary of user preferences for display."""
    total_actions: int = 0
    min_actions_required: int = 20
    is_active: bool = False
    positive_preferences: list[dict] = field(default_factory=list)
    negative_preferences: list[dict] = field(default_factory=list)
    preferences_by_type: dict[str, int] = field(default_factory=dict)


# =============================================================================
# PreferenceLearner Class
# =============================================================================

class PreferenceLearner:
    """
    Learns user preferences from article interactions.

    Tracks actions (star, read, archive, delete, ignore) and extracts
    features (keywords, source, category, author) to build a preference model.
    """

    def __init__(self, config: LearningConfig | None = None) -> None:
        """
        Initialize the preference learner.

        Args:
            config: Learning configuration. Defaults will be used if None.
        """
        self.config = config or LearningConfig()
        self._action_count_cache: int | None = None
        self._cache_time: datetime | None = None
        self._cache_ttl = timedelta(minutes=5)

    async def record_action(
        self,
        item_id: str,
        action_type: str,
        session: AsyncSession | None = None,
    ) -> bool:
        """
        Record a user action and update preferences.

        Args:
            item_id: The ID of the item acted upon.
            action_type: One of 'star', 'read', 'archive', 'delete', 'ignore'.
            session: Optional database session (will create one if not provided).

        Returns:
            True if successfully recorded, False otherwise.
        """
        if not self.config.enabled:
            return False

        if action_type not in ACTION_SIGNALS:
            log.warning(f"Unknown action type: {action_type}")
            return False

        signal = ACTION_SIGNALS[action_type]

        async def _do_record(sess: AsyncSession) -> bool:
            # Load the item to extract features
            result = await sess.execute(
                select(Item).where(Item.id == item_id)
            )
            item = result.scalar_one_or_none()

            if not item:
                log.warning(f"Item not found: {item_id}")
                return False

            # Record the action
            user_action = UserAction(
                id=str(uuid.uuid4()),
                item_id=item_id,
                action_type=action_type,
                action_value=signal,
                created_at=now(),
            )
            sess.add(user_action)

            # Extract and update features
            features = self._extract_features(item)
            await self._update_preferences(sess, features, signal)

            # Invalidate cache
            self._action_count_cache = None

            log.debug(
                f"Recorded action: {action_type} on item {item_id[:8]}..., "
                f"extracted {len(features)} features"
            )
            return True

        if session:
            return await _do_record(session)
        else:
            async with get_session() as sess:
                result = await _do_record(sess)
                await sess.commit()
                return result

    def _extract_features(self, item: Item) -> list[tuple[str, str]]:
        """
        Extract features from an item for preference learning.

        Returns list of (feature_type, feature_value) tuples.
        """
        features: list[tuple[str, str]] = []

        # Keywords (top N from item)
        keywords = item.keywords or []
        for kw in keywords[:self.config.max_features_per_action]:
            if kw and len(kw) > 2:  # Skip very short keywords
                features.append(("keyword", kw.lower()))

        # Source
        if item.source_id:
            features.append(("source", item.source_id))

        # Category (from source relationship if available)
        if hasattr(item, "source") and item.source and item.source.category:
            features.append(("category", item.source.category.lower()))

        # Author
        if item.author:
            features.append(("author", item.author.lower()))

        return features

    async def _update_preferences(
        self,
        session: AsyncSession,
        features: list[tuple[str, str]],
        signal: float,
    ) -> None:
        """
        Update preference weights for extracted features.

        Uses Exponential Moving Average for weight updates:
        new_weight = (1 - learning_rate) * old_weight + learning_rate * signal
        """
        for feature_type, feature_value in features:
            # Check if preference exists
            result = await session.execute(
                select(UserPreference).where(
                    UserPreference.feature_type == feature_type,
                    UserPreference.feature_value == feature_value,
                )
            )
            pref = result.scalar_one_or_none()

            if pref:
                # Update existing preference with EMA
                old_weight = pref.weight
                new_weight = (
                    (1 - self.config.learning_rate) * old_weight
                    + self.config.learning_rate * signal
                )
                # Clamp to [-1, 1]
                new_weight = max(-1.0, min(1.0, new_weight))

                pref.weight = new_weight
                pref.last_updated = now()

                if signal > 0:
                    pref.positive_count += 1
                else:
                    pref.negative_count += 1
            else:
                # Create new preference
                pref = UserPreference(
                    id=str(uuid.uuid4()),
                    feature_type=feature_type,
                    feature_value=feature_value,
                    weight=signal * self.config.learning_rate,  # Start small
                    positive_count=1 if signal > 0 else 0,
                    negative_count=1 if signal < 0 else 0,
                    last_updated=now(),
                )
                session.add(pref)

    async def compute_preference_score(
        self,
        keywords: list[str] | None = None,
        source_id: str | None = None,
        category: str | None = None,
        author: str | None = None,
        session: AsyncSession | None = None,
    ) -> float:
        """
        Calculate the preference score contribution for an item.

        Args:
            keywords: Item keywords.
            source_id: Source ID.
            category: Source category.
            author: Item author.
            session: Optional database session.

        Returns:
            Preference score in range [-max_preference_score, +max_preference_score].
        """
        if not self.config.enabled:
            return 0.0

        async def _compute(sess: AsyncSession) -> float:
            # Check if we have enough actions
            action_count = await self._get_action_count(sess)
            if action_count < self.config.min_actions_required:
                return 0.0

            # Build feature lookup
            features: list[tuple[str, str]] = []

            if keywords:
                for kw in keywords[:self.config.max_features_per_action]:
                    if kw and len(kw) > 2:
                        features.append(("keyword", kw.lower()))

            if source_id:
                features.append(("source", source_id))

            if category:
                features.append(("category", category.lower()))

            if author:
                features.append(("author", author.lower()))

            if not features:
                return 0.0

            # Query matching preferences
            matched_weights: list[float] = []

            for feature_type, feature_value in features:
                result = await sess.execute(
                    select(UserPreference.weight).where(
                        UserPreference.feature_type == feature_type,
                        UserPreference.feature_value == feature_value,
                    )
                )
                weight = result.scalar_one_or_none()
                if weight is not None:
                    matched_weights.append(weight)

            if not matched_weights:
                return 0.0

            # Calculate average weight and scale to max score
            avg_weight = sum(matched_weights) / len(matched_weights)
            score = avg_weight * self.config.max_preference_score

            return score

        if session:
            return await _compute(session)
        else:
            async with get_session() as sess:
                return await _compute(sess)

    async def _get_action_count(self, session: AsyncSession) -> int:
        """Get total action count with caching."""
        current = now()

        if (
            self._action_count_cache is not None
            and self._cache_time is not None
            and current - self._cache_time < self._cache_ttl
        ):
            return self._action_count_cache

        result = await session.execute(
            select(func.count(UserAction.id))
        )
        count = result.scalar() or 0

        self._action_count_cache = count
        self._cache_time = current

        return count

    async def run_batch_learning(self) -> int:
        """
        Process ignored items (old unread items) as mild negatives.

        This should be run periodically (e.g., every 6 hours) to learn
        from items the user chose not to engage with.

        Returns:
            Number of items processed.
        """
        if not self.config.enabled:
            return 0

        from src.storage.models import ItemStatus

        # Define "old" as items more than 48 hours old that are still NEW
        cutoff = now() - timedelta(hours=48)

        async with get_session() as session:
            # Find old unread items not already processed
            result = await session.execute(
                select(Item.id).where(
                    Item.status == ItemStatus.NEW,
                    Item.collected_at < cutoff,
                ).limit(100)  # Process in batches
            )
            item_ids = result.scalars().all()

            processed = 0
            for item_id in item_ids:
                # Check if we already recorded an ignore action
                existing = await session.execute(
                    select(UserAction.id).where(
                        UserAction.item_id == item_id,
                        UserAction.action_type == "ignore",
                    )
                )
                if existing.scalar_one_or_none():
                    continue

                # Record ignore action
                await self.record_action(item_id, "ignore", session)
                processed += 1

            await session.commit()

        log.info(f"Batch learning: processed {processed} ignored items")
        return processed

    async def apply_decay(self) -> int:
        """
        Apply time decay to preference weights.

        Old preferences fade over time to allow interests to evolve.
        Uses exponential decay: decayed = weight * 2^(-days / half_life)

        Returns:
            Number of preferences decayed.
        """
        if not self.config.enabled:
            return 0

        current = now()
        half_life = self.config.decay_half_life_days

        async with get_session() as session:
            # Get all preferences
            result = await session.execute(select(UserPreference))
            preferences = result.scalars().all()

            decayed_count = 0
            to_delete: list[str] = []

            for pref in preferences:
                if not pref.last_updated:
                    continue

                elapsed_days = (current - pref.last_updated).total_seconds() / 86400

                # Apply exponential decay
                decay_factor = 2 ** (-elapsed_days / half_life)
                new_weight = pref.weight * decay_factor

                # If weight is very small, mark for deletion
                if abs(new_weight) < 0.01:
                    to_delete.append(pref.id)
                else:
                    pref.weight = new_weight
                    decayed_count += 1

            # Delete negligible preferences
            if to_delete:
                await session.execute(
                    delete(UserPreference).where(UserPreference.id.in_(to_delete))
                )
                log.debug(f"Deleted {len(to_delete)} negligible preferences")

            await session.commit()

        log.info(f"Decay applied: {decayed_count} preferences decayed")
        return decayed_count

    async def get_preference_summary(self) -> PreferenceSummary:
        """
        Get a summary of learned preferences for UI display.

        Returns:
            PreferenceSummary with stats and top preferences.
        """
        summary = PreferenceSummary(
            min_actions_required=self.config.min_actions_required,
        )

        async with get_session() as session:
            # Total actions
            result = await session.execute(
                select(func.count(UserAction.id))
            )
            summary.total_actions = result.scalar() or 0
            summary.is_active = summary.total_actions >= self.config.min_actions_required

            # Top positive preferences
            result = await session.execute(
                select(UserPreference)
                .where(UserPreference.weight > 0)
                .order_by(UserPreference.weight.desc())
                .limit(10)
            )
            for pref in result.scalars():
                summary.positive_preferences.append({
                    "type": pref.feature_type,
                    "value": pref.feature_value,
                    "weight": pref.weight,
                    "positive_count": pref.positive_count,
                    "negative_count": pref.negative_count,
                })

            # Top negative preferences
            result = await session.execute(
                select(UserPreference)
                .where(UserPreference.weight < 0)
                .order_by(UserPreference.weight.asc())
                .limit(10)
            )
            for pref in result.scalars():
                summary.negative_preferences.append({
                    "type": pref.feature_type,
                    "value": pref.feature_value,
                    "weight": pref.weight,
                    "positive_count": pref.positive_count,
                    "negative_count": pref.negative_count,
                })

            # Count by type
            result = await session.execute(
                select(
                    UserPreference.feature_type,
                    func.count(UserPreference.id),
                ).group_by(UserPreference.feature_type)
            )
            for row in result:
                summary.preferences_by_type[row[0]] = row[1]

        return summary

    async def reset_preferences(self) -> None:
        """
        Clear all learned preferences and action history.

        Use with caution - this removes all learning data.
        """
        async with get_session() as session:
            await session.execute(delete(UserAction))
            await session.execute(delete(UserPreference))
            await session.execute(delete(LearningState))
            await session.commit()

        # Invalidate cache
        self._action_count_cache = None
        self._cache_time = None

        log.info("All preference data reset")


# =============================================================================
# Global Instance
# =============================================================================

_preference_learner: PreferenceLearner | None = None


def get_preference_learner() -> PreferenceLearner:
    """Get the global preference learner instance."""
    global _preference_learner
    if _preference_learner is None:
        _preference_learner = PreferenceLearner()
    return _preference_learner


def configure_preference_learner(config: LearningConfig) -> None:
    """Configure the global preference learner."""
    global _preference_learner
    _preference_learner = PreferenceLearner(config)
