"""Core types for the pluggable priority-scoring module.

This module defines the shared vocabulary that every priority strategy
speaks: the :class:`PriorityLevel` enum, a normalized :class:`PriorityContext`
built from a raw item payload, the :class:`PriorityResult` a strategy returns,
and the :class:`PriorityStrategy` protocol strategies implement.

Keeping normalization in one place means individual strategies never have to
re-parse dates, coerce types, or worry about timezone handling.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Mapping, Optional, Protocol, runtime_checkable


class PriorityLevel(str, Enum):
    """Ordered priority buckets, lowest to highest."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Ordinal rank where ``LOW`` is ``0`` and ``CRITICAL`` is the highest."""
        return _ORDER.index(self)

    def escalate(self) -> "PriorityLevel":
        """Return the next level up, clamping at :attr:`CRITICAL`."""
        return _ORDER[min(self.rank + 1, len(_ORDER) - 1)]

    def __str__(self) -> str:  # pragma: no cover - trivial
        return self.value


# Declared after the enum so the members exist when we reference them.
_ORDER: List[PriorityLevel] = [
    PriorityLevel.LOW,
    PriorityLevel.MEDIUM,
    PriorityLevel.HIGH,
    PriorityLevel.CRITICAL,
]


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    """Return ``value`` as a timezone-aware UTC datetime.

    Naive datetimes are assumed to already be in UTC, matching the convention
    used elsewhere in the codebase (``datetime.utcnow``).
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_datetime(value: Any) -> Optional[datetime]:
    """Best-effort conversion of a datetime or ISO-8601 string to UTC.

    Returns ``None`` for missing or unparseable values rather than raising, so
    a single malformed field never takes down a whole batch evaluation.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, str):
        try:
            return _as_utc(datetime.fromisoformat(value))
        except ValueError:
            return None
    return None


def _coerce_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class PriorityContext:
    """Normalized, strategy-agnostic view of an item.

    Strategies read from this instead of a raw ``dict`` so they share one
    definition of "how old is this" and "how long until it is due". ``now`` is
    captured once and injectable, which keeps strategies deterministic and
    their tests free of real wall-clock timing.
    """

    urgency: float = 0.0
    is_critical: bool = False
    created_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    now: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @classmethod
    def from_item(
        cls, item: Mapping[str, Any], now: Optional[datetime] = None
    ) -> "PriorityContext":
        """Build a context from a raw item mapping, clamping bad input.

        Negative urgency is clamped to zero and unparseable dates become
        ``None``; the caller gets a usable context for any payload shape.
        """
        reference = _as_utc(now) if now is not None else datetime.now(timezone.utc)
        return cls(
            urgency=max(0.0, _coerce_float(item.get("urgency", 0.0))),
            is_critical=bool(item.get("is_critical", False)),
            created_at=_coerce_datetime(item.get("created_at")),
            due_date=_coerce_datetime(item.get("due_date")),
            now=reference,
        )

    @property
    def age_days(self) -> float:
        """Whole-and-fractional days since ``created_at`` (never negative)."""
        if self.created_at is None:
            return 0.0
        seconds = (self.now - self.created_at).total_seconds()
        return max(0.0, seconds / 86400.0)

    @property
    def days_until_due(self) -> Optional[float]:
        """Days until ``due_date``; negative if overdue, ``None`` if unset."""
        if self.due_date is None:
            return None
        return (self.due_date - self.now).total_seconds() / 86400.0

    @property
    def is_overdue(self) -> bool:
        days = self.days_until_due
        return days is not None and days < 0


@dataclass(frozen=True)
class PriorityResult:
    """The outcome of evaluating one item against a strategy.

    ``reasons`` is a human-readable audit trail of why the strategy landed on
    ``level``; it is handy in demos, logs, and tests without changing the
    machine-readable ``level``/``score``.
    """

    level: PriorityLevel
    score: float
    reasons: List[str] = field(default_factory=list)


@runtime_checkable
class PriorityStrategy(Protocol):
    """Interface every pluggable priority strategy implements.

    ``name`` is a stable identifier used by the factory registry; ``evaluate``
    turns a normalized context into a :class:`PriorityResult`.
    """

    name: str

    def evaluate(self, context: PriorityContext) -> PriorityResult:
        ...
