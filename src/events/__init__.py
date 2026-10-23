"""Lightweight in-process pub/sub with typed events.

See ``docs/NOTES.md`` for usage. Import the public API from this package::

    from src.events import get_event_bus, ItemCreated

    get_event_bus().publish(ItemCreated(item_id=1, name="x", status="active"))
"""

from src.events.audit import AuditEntry, AuditLog
from src.events.base import Event, utcnow
from src.events.bus import EventBus, Subscription
from src.events.domain import ItemCreated, ItemDeleted, ItemUpdated

_default_bus: EventBus = EventBus()


def get_event_bus() -> EventBus:
    """Return the process-wide default :class:`EventBus`."""
    return _default_bus


__all__ = [
    "AuditEntry",
    "AuditLog",
    "Event",
    "EventBus",
    "ItemCreated",
    "ItemDeleted",
    "ItemUpdated",
    "Subscription",
    "get_event_bus",
    "utcnow",
]
