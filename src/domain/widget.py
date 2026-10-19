from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any, Optional


@dataclass(frozen=True)
class WidgetRecord:
    """Canonical in-memory representation of a stored widget."""

    id: int
    name: str
    item_id: int
    created_at: datetime
    updated_at: datetime
    priority: int = 0
    notes: Optional[str] = None

    def with_changes(self, now: Optional[datetime] = None, **changes: Any) -> "WidgetRecord":
        stamped = now if now is not None else datetime.utcnow()
        return replace(self, updated_at=stamped, **changes)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class WidgetStats:
    """Derived statistics for a widget.

    Replaces the ad-hoc ``dict`` previously returned by the widget service.
    """

    id: int
    complexity_score: float
    last_analyzed: str

    def to_dict(self) -> dict:
        return asdict(self)
