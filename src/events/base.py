import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable


@dataclass(frozen=True)
class Event:
    """
    Base class for every event published on the :class:`~src.events.bus.EventBus`.

    Concrete events subclass this and add their own typed payload fields. The
    base carries metadata common to all events so subscribers can log, order,
    or de-duplicate without each event re-declaring it.

    Fields are keyword-friendly with defaults so subclasses can add required
    payload fields ahead of these without ordering conflicts.
    """

    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def name(self) -> str:
        """Human-readable event name, defaulting to the class name."""
        return type(self).__name__


# A handler is any callable that accepts a single event instance. Handlers are
# intentionally untyped at the callable level (``Event``) because the bus
# narrows the type per subscription; see ``EventBus.subscribe``.
Handler = Callable[[Event], None]
