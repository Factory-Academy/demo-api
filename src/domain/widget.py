from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from datetime import datetime
from typing import Any, Mapping, Optional

from src.domain.coercion import (
    coerce_datetime,
    coerce_int,
    ensure_known_fields,
    require,
)


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
        ensure_known_fields(self, changes)
        stamped = now if now is not None else datetime.utcnow()
        return replace(self, updated_at=stamped, **changes)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "WidgetRecord":
        """Build a record from a loose mapping, coercing loose field types.

        Mirrors :meth:`src.domain.item.ItemRecord.from_mapping`: ``id``, ``name``
        and ``item_id`` are required, and numeric/date fields are coerced with
        ``ValueError`` on bad input.
        """
        now = datetime.utcnow()
        return cls(
            id=coerce_int(require(data, "id"), field="id"),
            name=require(data, "name"),
            item_id=coerce_int(require(data, "item_id"), field="item_id"),
            created_at=coerce_datetime(
                data.get("created_at"), field="created_at", default=now
            ),
            updated_at=coerce_datetime(
                data.get("updated_at"), field="updated_at", default=now
            ),
            priority=coerce_int(data.get("priority", 0), field="priority"),
            notes=data.get("notes"),
        )


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
