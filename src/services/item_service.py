"""Item business logic.

The heavy lifting lives in small, pure helpers under
:mod:`src.services.priority` and :mod:`src.services.items`. This class is a
thin, stateful facade that wires those helpers to the datastore.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

from src.services.items.batch import batch_update_status as _batch_update_status
from src.services.items.validation import validate_item as _validate_item
from src.services.priority import calculate_priority as _calculate_priority


class ItemService:
    def __init__(self, db):
        self.db = db

    def calculate_priority(self, item: Optional[Mapping[str, Any]]) -> str:
        return _calculate_priority(item)

    def validate_item(
        self, data: Optional[Mapping[str, Any]]
    ) -> Tuple[bool, List[str]]:
        return _validate_item(data)

    def batch_update_status(
        self, ids: Optional[Iterable[Any]], new_status: str, updated_by: str
    ) -> Dict[str, List[Any]]:
        return _batch_update_status(self.db, ids, new_status, updated_by)
