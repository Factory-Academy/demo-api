"""Item domain service.

Split into a pure, I/O-free core and a thin adapter:

- :mod:`~src.services.items.priority` -- priority scoring
- :mod:`~src.services.items.validation` -- payload validation
- :mod:`~src.services.items.status` -- batch status-change decisions
- :class:`~src.services.items.service.ItemService` -- the adapter that wires
  the core to a database
"""
from src.services.items import priority, status, validation
from src.services.items.service import ItemService
from src.services.items.validation import ValidationResult

__all__ = [
    "ItemService",
    "ValidationResult",
    "priority",
    "validation",
    "status",
]
