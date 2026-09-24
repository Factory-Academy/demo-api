"""Pure priority-scoring functions for items.

This is the split-up form of the old ``ItemService.calculate_priority``. The
original built the whole score in one expression and assumed ``created_at`` was
always a present ``datetime`` and ``urgency`` was always a number, so a missing
key, a stringified timestamp, a timezone-aware timestamp, or a ``None`` urgency
each raised. Here the score is composed from small, individually testable
functions, and every field is coerced defensively.
"""

from datetime import datetime
from typing import Any, Mapping, Optional

from . import coerce

URGENCY_WEIGHT = 10.0
CRITICAL_BONUS = 50.0
AGING_THRESHOLD_DAYS = 30
AGING_RATE = 0.5

# Ordered from most to least severe; first threshold met wins.
LABEL_THRESHOLDS = (
    ("critical", 80.0),
    ("high", 50.0),
    ("medium", 20.0),
)
DEFAULT_LABEL = "low"


def age_in_days(created_at: Any, *, now: Optional[datetime] = None) -> int:
    """Age of a record in whole days, clamped at zero.

    Unparseable or missing timestamps count as brand new (0 days). Future
    timestamps also clamp to 0 rather than contributing a negative age.
    """
    reference = now or datetime.utcnow()
    created = coerce.as_datetime(created_at)
    if created is None:
        return 0
    days = (reference - created).days
    return days if days > 0 else 0


def urgency_score(urgency: Any) -> float:
    """Weighted urgency contribution. Negative/malformed urgency scores zero."""
    return max(coerce.as_number(urgency, 0.0), 0.0) * URGENCY_WEIGHT


def criticality_bonus(is_critical: Any) -> float:
    """Flat bonus applied to anything flagged critical (truthy)."""
    return CRITICAL_BONUS if is_critical else 0.0


def aging_bonus(age_days: Any) -> float:
    """Extra weight for records older than the aging threshold."""
    days = max(coerce.as_number(age_days, 0.0), 0.0)
    if days > AGING_THRESHOLD_DAYS:
        return days * AGING_RATE
    return 0.0


def priority_score(item: Any, *, now: Optional[datetime] = None) -> float:
    """Total numeric priority score for an item mapping.

    Non-mapping input (``None``, a list, a bare value) scores zero rather than
    raising, so a malformed record degrades to the lowest priority.
    """
    if not isinstance(item, Mapping):
        return 0.0
    days = age_in_days(item.get("created_at"), now=now)
    score = urgency_score(item.get("urgency"))
    score += criticality_bonus(item.get("is_critical"))
    score += aging_bonus(days)
    return score


def score_to_label(score: Any) -> str:
    """Map a numeric score onto a priority label."""
    value = coerce.as_number(score, 0.0)
    for label, threshold in LABEL_THRESHOLDS:
        if value >= threshold:
            return label
    return DEFAULT_LABEL


def calculate_priority(item: Any, *, now: Optional[datetime] = None) -> str:
    """Convenience wrapper: score an item and return its priority label."""
    return score_to_label(priority_score(item, now=now))
