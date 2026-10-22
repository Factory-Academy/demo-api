"""Dataclass domain models.

These dataclasses are the in-memory, business-logic representation of the
records the API manages. They replace the loose ``dict`` structures that used
to flow through the routes and services. Pydantic schemas in ``src/models``
stay responsible for request parsing and response serialization; because those
schemas set ``from_attributes = True`` they serialize straight from these
dataclasses.
"""

from dataclasses import dataclass, fields, replace
from datetime import datetime
from typing import Any, Dict, Mapping, Optional


def _utcnow() -> datetime:
    return datetime.utcnow()


@dataclass
class ItemRecord:
    """A persisted item and the fields the service layer reasons about."""

    id: int
    name: str
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    status: str = "active"
    urgency: int = 0
    is_critical: bool = False
    quantity: int = 0
    due_date: Optional[datetime] = None
    updated_by: Optional[str] = None

    @classmethod
    def create(
        cls,
        id: int,
        payload: Mapping[str, Any],
        *,
        now: Optional[datetime] = None,
    ) -> "ItemRecord":
        """Build a record from an id and a payload of known field values.

        Unknown keys are rejected so a typo in a caller surfaces immediately
        instead of being silently dropped the way a dict spread would.
        """
        moment = now or _utcnow()
        allowed = _field_names(cls)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Unknown item field(s): {', '.join(sorted(unknown))}")
        return cls(id=id, created_at=moment, updated_at=moment, **dict(payload))

    def apply_update(
        self,
        changes: Mapping[str, Any],
        *,
        now: Optional[datetime] = None,
    ) -> "ItemRecord":
        """Apply a partial update in place and bump ``updated_at``.

        Mirrors the previous ``{**existing, **update_data}`` merge but refuses
        to create fields that are not part of the model.
        """
        allowed = _field_names(type(self)) - {"id", "created_at"}
        unknown = set(changes) - allowed
        if unknown:
            raise ValueError(f"Unknown item field(s): {', '.join(sorted(unknown))}")
        for key, value in changes.items():
            setattr(self, key, value)
        self.updated_at = now or _utcnow()
        return self

    def copy(self, **overrides: Any) -> "ItemRecord":
        return replace(self, **overrides)

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


@dataclass
class WidgetRecord:
    """A persisted widget belonging to an item."""

    id: int
    name: str
    item_id: int
    created_at: datetime
    updated_at: datetime
    priority: int = 0
    notes: Optional[str] = None

    @classmethod
    def create(
        cls,
        id: int,
        payload: Mapping[str, Any],
        *,
        now: Optional[datetime] = None,
    ) -> "WidgetRecord":
        moment = now or _utcnow()
        allowed = _field_names(cls)
        unknown = set(payload) - allowed
        if unknown:
            raise ValueError(f"Unknown widget field(s): {', '.join(sorted(unknown))}")
        return cls(id=id, created_at=moment, updated_at=moment, **dict(payload))

    def to_dict(self) -> Dict[str, Any]:
        return {f.name: getattr(self, f.name) for f in fields(self)}


def _field_names(cls: type) -> set:
    return {f.name for f in fields(cls)}
