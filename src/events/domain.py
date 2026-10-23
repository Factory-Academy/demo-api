from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.events.base import Event, utcnow


@dataclass(frozen=True)
class ItemCreated(Event):
    item_id: int
    name: str
    status: str
    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class ItemUpdated(Event):
    item_id: int
    changed_fields: tuple
    status: Optional[str] = None
    occurred_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class ItemDeleted(Event):
    item_id: int
    occurred_at: datetime = field(default_factory=utcnow)
