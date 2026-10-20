import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Tuple, Type, TypeVar

from src.events.base import Event, Handler

E = TypeVar("E", bound=Event)

# Optional bus-level callback invoked when a handler raises. It receives the
# handler, the event being dispatched, and the exception. If it is not set (or
# itself raises) the error is swallowed so one bad subscriber cannot break
# publishing for the others.
ErrorCallback = Callable[[Handler, Event, Exception], None]


@dataclass
class PublishResult:
    """Outcome of a single :meth:`EventBus.publish` call.

    Attributes:
        handled: Number of handlers that ran without raising.
        errors: ``(handler, exception)`` pairs for handlers that raised.
    """

    handled: int = 0
    errors: List[Tuple[Handler, Exception]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        """True when every notified handler completed without raising."""
        return not self.errors


class Subscription:
    """Handle returned by :meth:`EventBus.subscribe`.

    Keeping a handle means callers can unsubscribe without re-stating the exact
    event type and handler, and ``once`` subscriptions can remove themselves.
    Unsubscribing twice is a safe no-op.
    """

    def __init__(
        self, bus: "EventBus", event_type: Type[Event], handler: Handler, once: bool
    ) -> None:
        self._bus = bus
        self.event_type = event_type
        self.handler = handler
        self.once = once
        self._active = True

    @property
    def active(self) -> bool:
        return self._active

    def unsubscribe(self) -> None:
        if self._active:
            self._bus._remove(self)
            self._active = False

    def __enter__(self) -> "Subscription":
        return self

    def __exit__(self, *_exc: object) -> None:
        self.unsubscribe()


class EventBus:
    """A minimal, thread-safe, in-process publish/subscribe dispatcher.

    Handlers subscribe to an event *type* (a subclass of :class:`Event`).
    Publishing an event notifies every handler registered for the event's exact
    type as well as for any of its base event types, so a handler subscribed to
    a broad base event receives all of its subtypes.

    Design choices worth noting:

    * **Error isolation.** A handler that raises never prevents the remaining
      handlers from running; failures are collected into the returned
      :class:`PublishResult` and optionally forwarded to ``on_error``.
    * **Stable ordering.** Within a single event type handlers run in
      subscription order. Across the type hierarchy, the most-derived type's
      handlers run first, moving up toward :class:`Event`.
    * **Snapshot dispatch.** The handler list is copied under the lock before
      dispatch, so handlers may subscribe or unsubscribe (including one-shot
      ``once`` handlers) during ``publish`` without mutating the list mid-loop.
    """

    def __init__(self, on_error: Optional[ErrorCallback] = None) -> None:
        self._subscriptions: Dict[Type[Event], List[Subscription]] = {}
        self._lock = threading.RLock()
        self._on_error = on_error

    def subscribe(
        self,
        event_type: Type[E],
        handler: Callable[[E], None],
        *,
        once: bool = False,
    ) -> Subscription:
        """Register ``handler`` for ``event_type`` (and its subtypes).

        Args:
            event_type: The event class to listen for. Must be ``Event`` or a
                subclass.
            handler: A callable invoked with the published event.
            once: When true the subscription is removed automatically after the
                handler is invoked a single time.

        Returns:
            A :class:`Subscription` handle that can be used to unsubscribe.

        Subscribing the same handler to the same type more than once is
        idempotent: the existing subscription is returned unchanged, regardless
        of the ``once`` flag passed on the later call. Keying idempotency on the
        handler alone (not on ``handler`` plus ``once``) avoids registering a
        duplicate that would deliver the same event twice and prevents a second
        call from silently flipping a persistent handler into a one-shot one.
        """
        if not (isinstance(event_type, type) and issubclass(event_type, Event)):
            raise TypeError("event_type must be a subclass of Event")
        if not callable(handler):
            raise TypeError("handler must be callable")

        with self._lock:
            handlers = self._subscriptions.setdefault(event_type, [])
            for existing in handlers:
                if existing.handler == handler:
                    return existing
            subscription = Subscription(self, event_type, handler, once)
            handlers.append(subscription)
            return subscription

    def unsubscribe(self, event_type: Type[Event], handler: Handler) -> bool:
        """Remove ``handler`` from ``event_type``.

        Returns:
            True if a matching subscription was found and removed.
        """
        with self._lock:
            handlers = self._subscriptions.get(event_type)
            if not handlers:
                return False
            removed = False
            for subscription in list(handlers):
                if subscription.handler == handler:
                    handlers.remove(subscription)
                    subscription._active = False
                    removed = True
            if not handlers:
                del self._subscriptions[event_type]
            return removed

    def publish(self, event: Event) -> PublishResult:
        """Dispatch ``event`` to all matching handlers.

        Handlers registered for the event's exact type run first, followed by
        handlers registered for each base type up the hierarchy. Returns a
        :class:`PublishResult` summarising how many handlers ran and which, if
        any, raised.
        """
        if not isinstance(event, Event):
            raise TypeError("event must be an Event instance")

        result = PublishResult()
        for subscription in self._matching_subscriptions(type(event)):
            # ``once`` subscriptions are torn down before invocation so a
            # handler that re-publishes the same event is not re-entered.
            if subscription.once:
                subscription.unsubscribe()
            try:
                subscription.handler(event)
                result.handled += 1
            except Exception as error:  # noqa: BLE001 - isolation is the point
                result.errors.append((subscription.handler, error))
                self._notify_error(subscription.handler, event, error)
        return result

    def clear(self, event_type: Optional[Type[Event]] = None) -> None:
        """Remove all subscriptions, or only those for ``event_type``."""
        with self._lock:
            if event_type is None:
                self._subscriptions.clear()
            else:
                self._subscriptions.pop(event_type, None)

    def subscriber_count(self, event_type: Optional[Type[Event]] = None) -> int:
        """Count subscriptions for ``event_type``, or across all types."""
        with self._lock:
            if event_type is not None:
                return len(self._subscriptions.get(event_type, []))
            return sum(len(handlers) for handlers in self._subscriptions.values())

    def _matching_subscriptions(
        self, event_type: Type[Event]
    ) -> List[Subscription]:
        with self._lock:
            matched: List[Subscription] = []
            # ``__mro__`` yields the class then its bases, giving most-derived
            # first and stopping naturally before ``object``.
            for klass in event_type.__mro__:
                if klass is object:
                    break
                handlers = self._subscriptions.get(klass)
                if handlers:
                    matched.extend(handlers)
            return matched

    def _remove(self, subscription: Subscription) -> None:
        with self._lock:
            handlers = self._subscriptions.get(subscription.event_type)
            if not handlers:
                return
            if subscription in handlers:
                handlers.remove(subscription)
            if not handlers:
                del self._subscriptions[subscription.event_type]

    def _notify_error(
        self, handler: Handler, event: Event, error: Exception
    ) -> None:
        if self._on_error is None:
            return
        try:
            self._on_error(handler, event, error)
        except Exception:  # noqa: BLE001 - a broken error hook must not propagate
            pass


_default_bus: Optional[EventBus] = None
_default_bus_lock = threading.Lock()


def get_event_bus() -> EventBus:
    """Return the process-wide default :class:`EventBus`, creating it once.

    Application code that just needs a shared bus should use this rather than
    constructing its own, so publishers and subscribers meet on the same
    instance. Tests can isolate themselves with :func:`reset_event_bus`.
    """
    global _default_bus
    if _default_bus is None:
        with _default_bus_lock:
            if _default_bus is None:
                _default_bus = EventBus()
    return _default_bus


def reset_event_bus() -> EventBus:
    """Replace the default bus with a fresh, empty one and return it.

    Intended for test isolation so subscriptions do not leak between tests.
    """
    global _default_bus
    with _default_bus_lock:
        _default_bus = EventBus()
    return _default_bus
