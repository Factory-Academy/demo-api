from dataclasses import dataclass
from typing import Any, Dict, Optional

from src.events.base import Event


@dataclass(frozen=True)
class ItemEvent(Event):
    """Common base for events describing a change to a single item.

    Subscribers that care about any item change (for example an audit log) can
    subscribe to ``ItemEvent`` and receive every subtype, thanks to the bus's
    inheritance-aware dispatch.
    """

    item_id: int = 0


@dataclass(frozen=True)
class ItemCreated(ItemEvent):
    """Published after a new item has been persisted."""

    item: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ItemUpdated(ItemEvent):
    """Published after an existing item has been modified.

    ``changes`` holds only the fields that were supplied in the update, which
    lets subscribers react to specific transitions (for example status changes)
    without diffing the whole record.
    """

    changes: Optional[Dict[str, Any]] = None


@dataclass(frozen=True)
class ItemDeleted(ItemEvent):
    """Published after an item has been removed."""
