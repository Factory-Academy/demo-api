"""Pure priority scoring for items.

The score is a function of the item's urgency, whether it is flagged critical,
and how long it has been open. Splitting the numeric score from the label makes
each half independently testable and lets callers reuse the raw score if they
need it (for example, sorting a queue).
"""

from datetime import datetime
from typing import Optional

from src.services.items.coerce import as_number

# Ordered from highest to lowest. The first threshold whose minimum score is met
# wins, so this list must stay sorted by ``min_score`` descending.
PRIORITY_THRESHOLDS = (
    (80, "critical"),
    (50, "high"),
    (20, "medium"),
    (0, "low"),
)

URGENCY_WEIGHT = 10
CRITICAL_BONUS = 50
STALE_AFTER_DAYS = 30
STALE_DAILY_WEIGHT = 0.5


def priority_score(item: dict, *, now: Optional[datetime] = None) -> float:
    """Compute the raw numeric priority score for an item.

    ``now`` is injectable so tests can pin the clock; production callers leave it
    ``None`` and get ``datetime.utcnow()``, matching the original behavior.

    Urgency is read defensively: a missing, ``None``, or non-numeric value
    contributes nothing, and a negative value is clamped to zero.
    """
    if now is None:
        now = datetime.utcnow()

    age_days = (now - item["created_at"]).days
    # Clamping urgency to a non-negative number keeps the score in a
    # non-negative domain, which is what keeps the ``label_for_score`` floor
    # (below) genuinely unreachable rather than merely unlikely.
    urgency = max(as_number(item.get("urgency"), 0), 0)
    score = urgency * URGENCY_WEIGHT

    if item.get("is_critical"):
        score += CRITICAL_BONUS

    if age_days > STALE_AFTER_DAYS:
        score += age_days * STALE_DAILY_WEIGHT

    return score


def label_for_score(score: float) -> str:
    """Map a numeric score onto its priority label."""
    for min_score, label in PRIORITY_THRESHOLDS:
        if score >= min_score:
            return label
    # PRIORITY_THRESHOLDS ends at a 0 floor, so this is unreachable for any
    # finite non-negative score; kept as a defensive fallback.
    return PRIORITY_THRESHOLDS[-1][1]


def calculate_priority(item: dict, *, now: Optional[datetime] = None) -> str:
    """Return the priority label for an item."""
    return label_for_score(priority_score(item, now=now))
