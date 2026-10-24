from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class Event:
    """Base class for every event published on the :class:`EventBus`.

    Events are immutable value objects. Concrete events subclass this and
    declare their own typed payload fields. Each concrete event is expected to
    carry an ``occurred_at`` timestamp; declaring it on the subclass (rather
    than here) keeps dataclass field ordering valid on Python 3.9, where a
    field with a default on the base cannot precede required subclass fields.
    """

    @property
    def event_name(self) -> str:
        """Identity of the event type (distinct from any payload ``name`` field)."""
        return type(self).__name__

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
