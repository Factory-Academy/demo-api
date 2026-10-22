"""Priority levels and the scoring rule that assigns them."""

from datetime import datetime
from enum import Enum
from typing import Optional

from src.domain.models import ItemRecord

# Scoring constants, named so the thresholds read as intent rather than magic
# numbers scattered through an if/elif ladder.
URGENCY_WEIGHT = 10
CRITICAL_BONUS = 50
STALE_AFTER_DAYS = 30
STALE_DAILY_WEIGHT = 0.5

CRITICAL_THRESHOLD = 80
HIGH_THRESHOLD = 50
MEDIUM_THRESHOLD = 20


class Priority(str, Enum):
    """Derived priority bucket for an item.

    Subclasses ``str`` so existing comparisons against the plain strings
    (``"critical"`` etc.) and JSON serialization keep working unchanged.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


def score_item(record: ItemRecord, *, now: Optional[datetime] = None) -> float:
    """Compute the raw priority score for an item record."""
    moment = now or datetime.utcnow()
    age_days = (moment - record.created_at).days
    score = record.urgency * URGENCY_WEIGHT

    if record.is_critical:
        score += CRITICAL_BONUS

    if age_days > STALE_AFTER_DAYS:
        score += age_days * STALE_DAILY_WEIGHT

    return score


def compute_priority(record: ItemRecord, *, now: Optional[datetime] = None) -> Priority:
    """Map an item record to its :class:`Priority` bucket."""
    score = score_item(record, now=now)
    if score >= CRITICAL_THRESHOLD:
        return Priority.CRITICAL
    if score >= HIGH_THRESHOLD:
        return Priority.HIGH
    if score >= MEDIUM_THRESHOLD:
        return Priority.MEDIUM
    return Priority.LOW
