"""Contract shared by every priority strategy.

A strategy answers a single question: given an item, how urgent is it? The
answer is expressed as a :class:`PriorityResult` so callers get a stable label
(for routing and display), a numeric score (for sorting), and a human-readable
reason (for debugging and audit trails) regardless of which strategy produced
it.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping, Protocol, runtime_checkable


class PriorityLevel(str, Enum):
    """Ordered priority buckets.

    Inheriting from ``str`` keeps values JSON-serializable and comparable to
    the plain strings the rest of the app already uses (``"critical"`` etc.).
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        """Numeric rank where a larger number means more urgent."""
        return _LEVEL_RANK[self]


_LEVEL_RANK = {
    PriorityLevel.LOW: 0,
    PriorityLevel.MEDIUM: 1,
    PriorityLevel.HIGH: 2,
    PriorityLevel.CRITICAL: 3,
}


@dataclass(frozen=True)
class PriorityResult:
    """Outcome of scoring a single item."""

    level: PriorityLevel
    score: float
    reason: str = ""


# An item is any read-only mapping of field name to value. Using ``Mapping``
# rather than a concrete model keeps strategies decoupled from the ORM and the
# Pydantic schema, which both differ across demo branches.
Item = Mapping[str, object]


@runtime_checkable
class PriorityStrategy(Protocol):
    """Interface every priority strategy implements."""

    #: Stable identifier used by the factory and in serialized output.
    name: str

    def assess(self, item: Item) -> PriorityResult:
        """Return the priority of ``item``.

        Implementations must be pure and side-effect free so a single instance
        can be shared across requests and threads.
        """
        ...
