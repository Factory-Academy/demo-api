from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, List, Optional, Type, TypeVar

from src.events.base import Event

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Event)
Handler = Callable[[Event], None]
ErrorHandler = Callable[[Event, Handler, BaseException], None]


def _log_handler_error(event: Event, handler: Handler, exc: BaseException) -> None:
    logger.exception(
        "Event handler %r failed while processing %s",
        getattr(handler, "__name__", repr(handler)),
        event.event_name,
    )


class Subscription:
    """Handle returned by :meth:`EventBus.subscribe`.

    Keeps a reference to the owning bus so a caller can cancel the
    subscription without having to remember the handler and event type.
    """

    def __init__(self, bus: "EventBus", event_type: Type[Event], handler: Handler):
        self._bus = bus
        self.event_type = event_type
        self.handler = handler
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def unsubscribe(self) -> bool:
        if not self._active:
            return False
        removed = self._bus.unsubscribe(self.event_type, self.handler)
        self._active = False
        return removed

    def __enter__(self) -> "Subscription":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.unsubscribe()


class EventBus:
    """A minimal, thread-safe, in-process publish/subscribe dispatcher.

    Handlers subscribe to a concrete :class:`Event` subclass. When an event is
    published, every handler registered for the event's type *or any of its
    base event types* is invoked, so subscribing to :class:`Event` itself
    receives every event. A failing handler never prevents the remaining
    handlers from running; failures are routed to ``on_error``.
    """

    def __init__(self, on_error: Optional[ErrorHandler] = None):
        self._subscribers: Dict[Type[Event], List[Handler]] = {}
        self._once: "set[tuple[Type[Event], Handler]]" = set()
        self._lock = threading.RLock()
        self._on_error = on_error or _log_handler_error

    def subscribe(self, event_type: Type[E], handler: Callable[[E], None]) -> Subscription:
        self._validate(event_type, handler)
        with self._lock:
            handlers = self._subscribers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)
        return Subscription(self, event_type, handler)  # type: ignore[arg-type]

    def subscribe_once(self, event_type: Type[E], handler: Callable[[E], None]) -> Subscription:
        self._validate(event_type, handler)
        with self._lock:
            handlers = self._subscribers.setdefault(event_type, [])
            if handler not in handlers:
                handlers.append(handler)
            self._once.add((event_type, handler))
        return Subscription(self, event_type, handler)  # type: ignore[arg-type]

    def unsubscribe(self, event_type: Type[Event], handler: Handler) -> bool:
        with self._lock:
            handlers = self._subscribers.get(event_type)
            if not handlers or handler not in handlers:
                return False
            handlers.remove(handler)
            self._once.discard((event_type, handler))
            if not handlers:
                del self._subscribers[event_type]
            return True

    def publish(self, event: Event) -> int:
        if not isinstance(event, Event):
            raise TypeError(f"Can only publish Event instances, got {type(event).__name__}")

        # Snapshot matching handlers under the lock, then invoke them outside
        # the lock so a handler may safely (un)subscribe or publish in turn.
        dispatched: List[tuple] = []
        with self._lock:
            for event_type in type(event).__mro__:
                if not (isinstance(event_type, type) and issubclass(event_type, Event)):
                    continue
                for handler in self._subscribers.get(event_type, ()):  # type: ignore[arg-type]
                    dispatched.append((event_type, handler))

        invoked = 0
        for event_type, handler in dispatched:
            if (event_type, handler) in self._once:
                # Remove before invoking so a raising once-handler still fires only once.
                self.unsubscribe(event_type, handler)
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001 - isolation is the whole point
                self._on_error(event, handler, exc)
            invoked += 1
        return invoked

    def clear(self, event_type: Optional[Type[Event]] = None) -> None:
        with self._lock:
            if event_type is None:
                self._subscribers.clear()
                self._once.clear()
                return
            self._subscribers.pop(event_type, None)
            self._once = {pair for pair in self._once if pair[0] is not event_type}

    def subscriber_count(self, event_type: Optional[Type[Event]] = None) -> int:
        with self._lock:
            if event_type is None:
                return sum(len(handlers) for handlers in self._subscribers.values())
            return len(self._subscribers.get(event_type, ()))

    @staticmethod
    def _validate(event_type: Type[Event], handler: Handler) -> None:
        if not (isinstance(event_type, type) and issubclass(event_type, Event)):
            raise TypeError("event_type must be a subclass of Event")
        if not callable(handler):
            raise TypeError("handler must be callable")
