"""Value types shared by every priority strategy.

These decouple the strategies from the ad-hoc ``dict`` shape the rest of the
app passes around. :class:`PriorityInput` normalises an item dict once (parsing
dates, filling defaults) so each strategy can work with clean, typed fields,
and :class:`PriorityAssessment` is the uniform result every strategy returns.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Mapping, Optional

from src.services.priority.errors import PriorityError

# Levels in ascending order of severity. Kept as a module constant so rank
# lookups and escalation don't depend on the enum's definition order.
_ORDER = ("low", "medium", "high", "critical")


class PriorityLevel(str, Enum):
    """The four priority buckets, ordered ``LOW < MEDIUM < HIGH < CRITICAL``.

    Subclassing ``str`` means a level compares equal to and serialises as its
    plain string value (``PriorityLevel.HIGH == "high"``), so it drops into the
    existing string-based API without ceremony.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return _ORDER.index(self.value)

    @classmethod
    def from_rank(cls, rank: int) -> "PriorityLevel":
        """Return the level at ``rank``, clamped into the valid range."""
        clamped = max(0, min(rank, len(_ORDER) - 1))
        return cls(_ORDER[clamped])

    def escalate(self, steps: int = 1) -> "PriorityLevel":
        """Return the level ``steps`` buckets more severe, capped at CRITICAL."""
        return PriorityLevel.from_rank(self.rank + steps)


def _to_datetime(value: Any, *, field_name: str) -> Optional[datetime]:
    """Coerce ``value`` into a ``datetime`` (or ``None``).

    Accepts ``None``, ``datetime``, ``date``, and ISO-8601 strings. Anything
    else, or an unparseable string, raises :class:`PriorityError` so a malformed
    item surfaces loudly instead of silently scoring wrong.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise PriorityError(
                f"{field_name} is not a valid ISO-8601 datetime: {value!r}"
            ) from exc
    raise PriorityError(
        f"{field_name} must be a datetime, date, ISO string, or None, "
        f"got {type(value).__name__}"
    )


def _to_int(value: Any, *, field_name: str) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        # bool is an int subclass; treat it as a plain flag coerced to 0/1.
        return int(value)
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise PriorityError(
            f"{field_name} must be an integer, got {value!r}"
        ) from exc


@dataclass(frozen=True)
class PriorityInput:
    """The normalised facts about an item that strategies score against.

    ``created_at`` and ``due_date`` are optional: an item with no creation time
    is treated as brand new (age 0), and an item with no due date has no
    deadline pressure. Build one from a raw item dict with :meth:`from_item`.
    """

    created_at: Optional[datetime] = None
    urgency: int = 0
    is_critical: bool = False
    due_date: Optional[datetime] = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_item(cls, item: Mapping[str, Any]) -> "PriorityInput":
        return cls(
            created_at=_to_datetime(item.get("created_at"), field_name="created_at"),
            urgency=_to_int(item.get("urgency"), field_name="urgency"),
            is_critical=bool(item.get("is_critical")),
            due_date=_to_datetime(item.get("due_date"), field_name="due_date"),
            metadata=dict(item),
        )


@dataclass(frozen=True)
class PriorityAssessment:
    """A strategy's verdict for one item.

    ``score`` is strategy-specific (the weighted strategy returns its numeric
    score; the SLA strategy returns hours until the deadline, negative when
    overdue), so treat ``level`` as the portable field and ``score`` as a
    diagnostic detail. ``reason`` is a short human-readable explanation and
    ``strategy`` names the strategy that produced the verdict.
    """

    level: PriorityLevel
    score: float
    reason: str
    strategy: str
