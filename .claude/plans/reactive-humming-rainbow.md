# Plan: Engagement-Based Learning System

## Overview

Implement a system that learns user preferences from their actions on articles (star, read, archive, delete, ignore) and automatically adjusts relevance scores to match learned preferences.

## How It Works

1. **User performs actions** → System extracts features (keywords, source, category, author)
2. **Features are weighted** → Positive actions increase weight, negative actions decrease
3. **New articles scored** → Preference weights contribute to relevance_score
4. **Preferences decay** → Old preferences fade over time (interests evolve)

### Signal Weights
| Action | Signal | Description |
|--------|--------|-------------|
| ⭐ Star | +1.0 | Strong positive - "I want more like this" |
| 📁 Archive | +0.5 | Positive - Kept for later |
| ✅ Read | +0.3 | Mild positive - Engaged with content |
| 🗑️ Delete | -0.8 | Strong negative - Not interested |
| Ignored | -0.2 | Mild negative - Old unread items (batch job) |

---

## Database Changes

### New Table: `user_preferences`
```sql
CREATE TABLE user_preferences (
    id TEXT PRIMARY KEY,
    feature_type TEXT NOT NULL,     -- 'keyword', 'source', 'category', 'author'
    feature_value TEXT NOT NULL,    -- the actual value
    weight REAL DEFAULT 0.0,        -- -1.0 to +1.0
    positive_count INTEGER DEFAULT 0,
    negative_count INTEGER DEFAULT 0,
    last_updated DATETIME,
    UNIQUE(feature_type, feature_value)
);
```

### New Table: `user_actions`
```sql
CREATE TABLE user_actions (
    id TEXT PRIMARY KEY,
    item_id TEXT NOT NULL,
    action_type TEXT NOT NULL,      -- 'star', 'read', 'archive', 'delete', 'ignore'
    action_value REAL NOT NULL,
    created_at DATETIME,
    FOREIGN KEY (item_id) REFERENCES items(id) ON DELETE CASCADE
);
```

### New Table: `learning_state`
```sql
CREATE TABLE learning_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME
);
```

---

## New Module: `src/processors/preference_learner.py`

### PreferenceLearner Class

**Key methods:**
- `record_action(item_id, action_type)` - Record action and update preferences
- `compute_preference_score(keywords, source_id, category, author)` - Calculate score contribution
- `run_batch_learning()` - Process ignored items (scheduled job)
- `apply_decay()` - Decay old preferences (scheduled job)
- `get_preference_summary()` - For UI display
- `reset_preferences()` - Clear all learned data

**Algorithm:**
```python
# Weight update (Exponential Moving Average)
new_weight = (1 - learning_rate) * old_weight + learning_rate * signal

# Decay over time
decayed_weight = weight * 2^(-elapsed_days / half_life_days)

# Score calculation
preference_score = avg(matched_weights) * max_preference_score
# Range: -25 to +25 points (configurable)
```

**Feature extraction per action:**
- Keywords (top 10 from article)
- Source ID
- Category (from source)
- Author

---

## Integration Points

### 1. Modify `src/storage/models.py`
Add 3 new SQLAlchemy models:
- `UserPreference`
- `UserAction`
- `LearningState`

### 2. Modify `src/processors/scorer.py`
- Add `preference_score: float = 0.0` to `ScoreBreakdown`
- Add `preference_learner` parameter to `Scorer.__init__`
- Add async `score_item_async()` method that includes preference scoring

### 3. Modify `src/dashboard/components/feed.py`
Update action handlers to record preferences:
- `_toggle_star()` → record 'star' action
- `_mark_item_read()` → record 'read' action
- `_archive_item()` → record 'archive' action
- `_delete_item()` → record 'delete' action (before deletion)

### 4. Modify `src/scheduler/jobs.py`
- Add `_run_batch_learning()` job (every 6 hours)
- Add `_run_preference_decay()` job (daily at 2 AM)
- Integrate `PreferenceLearner` into `CollectionJob` scoring

### 5. Modify `src/dashboard/app.py`
Add "Preferences" section in settings:
- Learning status indicator (active/in progress)
- Actions count and threshold
- Top positive/negative preferences display
- Reset button

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `src/processors/preference_learner.py` | CREATE | Main learning module (~300 lines) |
| `src/storage/models.py` | MODIFY | Add 3 new models |
| `src/processors/scorer.py` | MODIFY | Add preference_score component |
| `src/processors/__init__.py` | MODIFY | Export PreferenceLearner |
| `src/dashboard/components/feed.py` | MODIFY | Record actions |
| `src/scheduler/jobs.py` | MODIFY | Add learning jobs |
| `src/dashboard/app.py` | MODIFY | Add preferences UI |

---

## Configuration

Add to `config/settings.yaml`:
```yaml
learning:
  enabled: true
  learning_rate: 0.1
  decay_half_life_days: 30
  min_actions_required: 20
  max_preference_score: 25.0
```

---

## UI Components

### Sidebar Learning Indicator
```
🧠 Apprentissage actif (47 actions)
```
or
```
📊 Apprentissage: 13/20 actions
```

### Settings > Preferences Section
- Total actions metric
- Learning status (active/waiting)
- Preferences count by type
- Top positive preferences list
- Top negative preferences list
- Reset button

---

## Activation Threshold

System requires **20 actions minimum** before affecting scores:
- Prevents cold-start noise
- UI shows progress toward activation
- Returns 0.0 for preference_score until threshold met

---

## Verification

1. **Syntax check:**
   ```bash
   venv/bin/python -m py_compile src/processors/preference_learner.py
   venv/bin/python -c "import src.dashboard.app"
   ```

2. **Manual testing:**
   - Star 5 articles → check keywords get positive weight
   - Delete 3 articles → check keywords get negative weight
   - View preferences in settings
   - Reset and verify cleared

3. **Score verification:**
   - After 20+ actions, new articles should show preference_score in breakdown
   - Articles similar to starred ones should score higher
