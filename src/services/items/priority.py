"""Pure priority scoring for items.

Every function here is deterministic given its arguments: no database access,
no logging, and the current time is injected rather than read from the clock.
This keeps the scoring rule easy to reason about and trivial to test.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping, Optional

from src.services.items._coerce import as_datetime, make_naive_utc, number_or

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
    """The only fields that influence an item's priority.

    ``created_at`` is optional: a raw item may omit it or carry an unparseable
    value, in which case the staleness bonus simply does not apply.
    """

    created_at: Optional[datetime] = None
    urgency: float = 0
    is_critical: bool = False


def age_in_days(created_at: Optional[datetime], now: datetime) -> int:
    """Whole days between ``created_at`` and ``now`` (truncated toward zero,
    matching ``timedelta.days``).

    Missing timestamps count as zero age, and either operand may be timezone
    aware or naive -- both are normalised to UTC before subtracting so the
    comparison never raises.
    """
    if created_at is None:
        return 0
    return (make_naive_utc(now) - make_naive_utc(created_at)).days


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
    """Extract :class:`PriorityInputs` from a raw item mapping.

    Untrusted fields are coerced rather than trusted: a missing or malformed
    ``created_at`` becomes ``None`` (no staleness bonus) and a non-numeric
    ``urgency`` falls back to ``0``, so scoring never raises on bad input.
    """
    return PriorityInputs(
        created_at=as_datetime(item.get("created_at")),
        urgency=number_or(item.get("urgency", 0), 0),
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
