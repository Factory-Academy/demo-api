from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.events.base import Event
from src.events.bus import EventBus, Subscription


@dataclass(frozen=True)
class AuditEntry:
    name: str
    occurred_at: Optional[datetime]
    payload: Dict[str, Any]


class AuditLog:
    """Example subscriber that records every event it receives.

    Attaching an :class:`AuditLog` to a bus subscribes it to the :class:`Event`
    base type, so it captures all events regardless of their concrete type.
    """

    def __init__(self) -> None:
        self._entries: List[AuditEntry] = []
        self._subscription: Optional[Subscription] = None

    def attach(self, bus: EventBus) -> Subscription:
        if self._subscription is not None and self._subscription.active:
            return self._subscription
        self._subscription = bus.subscribe(Event, self.record)
        return self._subscription

    def detach(self) -> None:
        if self._subscription is not None:
            self._subscription.unsubscribe()
            self._subscription = None

    def record(self, event: Event) -> None:
        payload = event.to_dict()
        self._entries.append(
            AuditEntry(
                name=event.event_name,
                occurred_at=payload.get("occurred_at"),
                payload=payload,
            )
        )

    @property
    def entries(self) -> List[AuditEntry]:
        return list(self._entries)

    def names(self) -> List[str]:
        return [entry.name for entry in self._entries]

    def clear(self) -> None:
        self._entries.clear()
