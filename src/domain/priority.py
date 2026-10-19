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
        """Map a numeric urgency score onto a :class:`Priority` bucket."""
        if score >= 80:
            return cls.CRITICAL
        if score >= 50:
            return cls.HIGH
        if score >= 20:
            return cls.MEDIUM
        return cls.LOW
