"""Pure priority scoring for items.

Every function here is deterministic given its arguments: no database access,
no logging, and the current time is injected rather than read from the clock.
This keeps the scoring rule easy to reason about and trivial to test.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional

# Priority levels, ordered from most to least urgent. Returned as plain
# strings so the public service contract is unchanged.
CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"

# Scoring weights, named so the rule lives in one place instead of being
# scattered through branching code.
URGENCY_WEIGHT = 10
CRITICAL_BONUS = 50
STALE_AGE_DAYS = 30
STALE_AGE_WEIGHT = 0.5

# (inclusive lower bound, level), highest first. Scores below the lowest
# bound fall through to LOW.
_THRESHOLDS = (
    (80, CRITICAL),
    (50, HIGH),
    (20, MEDIUM),
)


@dataclass(frozen=True)
class PriorityInputs:
    """The only fields that influence an item's priority."""

    created_at: datetime
    urgency: int = 0
    is_critical: bool = False


def age_in_days(created_at: datetime, now: datetime) -> int:
    """Whole days between ``created_at`` and ``now`` (truncated toward zero,
    matching ``timedelta.days``)."""
    return (now - created_at).days


def score(inputs: PriorityInputs, now: datetime) -> float:
    """Compute the raw priority score for ``inputs`` as of ``now``."""
    value = inputs.urgency * URGENCY_WEIGHT
    if inputs.is_critical:
        value += CRITICAL_BONUS
    age = age_in_days(inputs.created_at, now)
    if age > STALE_AGE_DAYS:
        value += age * STALE_AGE_WEIGHT
    return value


def level_for_score(value: float) -> str:
    """Map a raw score onto a priority level string."""
    for threshold, level in _THRESHOLDS:
        if value >= threshold:
            return level
    return LOW


def inputs_from_item(item: Mapping) -> PriorityInputs:
    """Extract :class:`PriorityInputs` from a raw item mapping."""
    return PriorityInputs(
        created_at=item["created_at"],
        urgency=item.get("urgency", 0),
        is_critical=bool(item.get("is_critical")),
    )


def classify(item: Mapping, now: Optional[datetime] = None) -> str:
    """Return the priority level for ``item``.

    ``now`` defaults to the current UTC time; pass it explicitly for
    deterministic results.
    """
    if now is None:
        now = datetime.utcnow()
    return level_for_score(score(inputs_from_item(item), now))
