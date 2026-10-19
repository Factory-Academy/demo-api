import math
from enum import Enum


class Priority(str, Enum):
    """Priority buckets for an item, ordered from most to least urgent.

    Subclassing ``str`` keeps the values comparable to the plain strings
    (``"critical"``, ``"high"`` ...) that earlier revisions returned, so
    existing callers and serialized payloads keep working unchanged.
    """

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @classmethod
    def from_score(cls, score: float) -> "Priority":
        """Map a numeric urgency score onto a :class:`Priority` bucket.

        A non-numeric or non-finite score (``NaN``/``inf``) is rejected with a
        ``ValueError``. ``NaN`` is especially dangerous here because every
        comparison against it is ``False``, so it would otherwise fall through
        to :attr:`LOW` and silently mislabel the item.
        """
        try:
            numeric = float(score)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Priority score must be numeric, got {score!r}") from error
        if not math.isfinite(numeric):
            raise ValueError(f"Priority score must be finite, got {score!r}")

        if numeric >= 80:
            return cls.CRITICAL
        if numeric >= 50:
            return cls.HIGH
        if numeric >= 20:
            return cls.MEDIUM
        return cls.LOW
