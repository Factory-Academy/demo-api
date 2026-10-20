import itertools
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

# Process-wide monotonic counter used to stamp every event with a strictly
# increasing sequence number. ``occurred_at`` cannot order two events created
# within the same clock tick, and its resolution varies by platform, so
# consumers that need the exact publish order read ``sequence`` instead of
# comparing timestamps.
_sequence_lock = threading.Lock()
_sequence_counter = itertools.count(1)


def _next_sequence() -> int:
    with _sequence_lock:
        return next(_sequence_counter)


@dataclass(frozen=True)
class Event:
    """
    Base class for every event published on the :class:`~src.events.bus.EventBus`.

    Concrete events subclass this and add their own typed payload fields. The
    base carries metadata common to all events so subscribers can log, order,
    or de-duplicate without each event re-declaring it.

    Fields are keyword-friendly with defaults so subclasses can add required
    payload fields ahead of these without ordering conflicts.

    Metadata:
        event_id: A unique identifier for this event instance.
        occurred_at: Timezone-aware UTC timestamp of when the event was built.
        sequence: A process-wide, strictly increasing ordinal. Unlike
            ``occurred_at`` it never ties, so it is the canonical key for
            reconstructing publish order.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    # Excluded from equality/hash so two events are distinguished by their
    # ``event_id``, not by an ordinal that is incidental to their identity.
    sequence: int = field(default_factory=_next_sequence, compare=False)

    @property
    def name(self) -> str:
        """Human-readable event name, defaulting to the class name."""
        return type(self).__name__


# A handler is any callable that accepts a single event instance. Handlers are
# intentionally untyped at the callable level (``Event``) because the bus
# narrows the type per subscription; see ``EventBus.subscribe``.
Handler = Callable[[Event], None]
