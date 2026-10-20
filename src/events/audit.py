import threading
from dataclasses import asdict
from typing import Dict, List, Optional

from src.events.bus import EventBus, Subscription
from src.events.domain import ItemEvent


class AuditLog:
    """A subscriber that records every item event into an in-memory trail.

    This is the reference example of wiring a subscriber to the bus: it listens
    to the broad :class:`ItemEvent` base type and therefore captures every item
    subtype (created, updated, deleted) through a single subscription.
    """

    def __init__(self, max_entries: int = 1000) -> None:
        if max_entries <= 0:
            raise ValueError("max_entries must be positive")
        self._max_entries = max_entries
        self._entries: List[Dict[str, object]] = []
        self._lock = threading.Lock()
        self._subscription: Optional[Subscription] = None

    def attach(self, bus: EventBus) -> Subscription:
        """Subscribe this audit log to ``bus``; idempotent across calls."""
        if self._subscription is not None and self._subscription.active:
            return self._subscription
        self._subscription = bus.subscribe(ItemEvent, self.record)
        return self._subscription

    def detach(self) -> None:
        """Unsubscribe from the bus it was attached to, if any."""
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None

    def record(self, event: ItemEvent) -> None:
        entry = {
            "event": event.name,
            "event_id": event.event_id,
            "occurred_at": event.occurred_at.isoformat(),
            "item_id": event.item_id,
            "payload": _event_payload(event),
        }
        with self._lock:
            self._entries.append(entry)
            if len(self._entries) > self._max_entries:
                # Drop oldest entries to keep the trail bounded.
                del self._entries[: len(self._entries) - self._max_entries]

    def entries(self) -> List[Dict[str, object]]:
        """Return a shallow copy of the recorded entries, oldest first."""
        with self._lock:
            return list(self._entries)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()


def _event_payload(event: ItemEvent) -> Dict[str, object]:
    """Extract the subtype-specific fields, excluding the common metadata."""
    data = asdict(event)
    for common in ("event_id", "occurred_at", "item_id"):
        data.pop(common, None)
    return data


_default_audit_log: Optional[AuditLog] = None
_default_audit_lock = threading.Lock()


def get_audit_log() -> AuditLog:
    """Return the process-wide default :class:`AuditLog`, creating it once."""
    global _default_audit_log
    if _default_audit_log is None:
        with _default_audit_lock:
            if _default_audit_log is None:
                _default_audit_log = AuditLog()
    return _default_audit_log
