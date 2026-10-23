"""Map a numeric priority score onto a discrete label."""

from __future__ import annotations

from typing import Any

CRITICAL_THRESHOLD = 80
HIGH_THRESHOLD = 50
MEDIUM_THRESHOLD = 20

CRITICAL = "critical"
HIGH = "high"
MEDIUM = "medium"
LOW = "low"


def classify_score(score: Any) -> str:
    """Return the priority label for ``score``.

    Non-numeric scores are treated as ``0`` so this function is total.
    """
    try:
        value = float(score)
    except (TypeError, ValueError):
        value = 0.0
    if value != value:  # NaN
        value = 0.0

    if value >= CRITICAL_THRESHOLD:
        return CRITICAL
    if value >= HIGH_THRESHOLD:
        return HIGH
    if value >= MEDIUM_THRESHOLD:
        return MEDIUM
    return LOW
