"""Pure priority-score computation.

The score is a plain number derived from an item's urgency, critical flag, and
age. Keeping this separate from classification and from I/O makes each rule
independently testable.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Optional

from src.services.priority.normalization import (
    coerce_flag,
    coerce_non_negative_number,
    compute_age_days,
)

URGENCY_WEIGHT = 10
CRITICAL_BONUS = 50
AGE_THRESHOLD_DAYS = 30
AGE_WEIGHT = 0.5

# Scores only matter relative to the classification thresholds, so a ceiling
# keeps a pathologically large urgency from producing an unbounded number.
MAX_SCORE = 1000.0


def urgency_component(urgency: Any) -> float:
    """Score contributed by an item's urgency."""
    return coerce_non_negative_number(urgency) * URGENCY_WEIGHT


def critical_component(is_critical: Any) -> float:
    """Flat bonus applied to items flagged critical."""
    return CRITICAL_BONUS if coerce_flag(is_critical) else 0.0


def age_component(age_days: int) -> float:
    """Score contributed by an item older than the age threshold."""
    if age_days > AGE_THRESHOLD_DAYS:
        return age_days * AGE_WEIGHT
    return 0.0


def compute_score(
    *,
    urgency: Any = 0,
    is_critical: Any = False,
    age_days: int = 0,
) -> float:
    """Combine the scoring components and clamp to ``[0, MAX_SCORE]``."""
    score = (
        urgency_component(urgency)
        + critical_component(is_critical)
        + age_component(age_days)
    )
    return max(0.0, min(score, MAX_SCORE))


def score_item(item: Optional[Mapping[str, Any]], *, now: Optional[datetime] = None) -> float:
    """Score a raw item mapping, tolerating missing or malformed fields."""
    if not isinstance(item, Mapping):
        return 0.0
    age_days = compute_age_days(item.get("created_at"), now=now)
    return compute_score(
        urgency=item.get("urgency", 0),
        is_critical=item.get("is_critical", False),
        age_days=age_days,
    )
