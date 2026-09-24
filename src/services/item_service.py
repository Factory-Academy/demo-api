"""Item business logic.

The priority scoring, payload validation, and batch-update logic have been
split into the pure helpers under :mod:`src.services.items`. ``ItemService``
now orchestrates those helpers with the database, keeping the same public API
(:meth:`calculate_priority`, :meth:`validate_item`, :meth:`batch_update_status`)
that routes and callers already depend on.
"""

from typing import Any, List, Tuple

from src.services.items import batch, priority, validation
from src.services.items.errors import ItemDataError

__all__ = ["ItemService", "ItemDataError"]


class ItemService:
    def __init__(self, db):
        self.db = db

    def calculate_priority(self, item: dict) -> str:
        return priority.calculate_priority(item)

    def validate_item(self, data: dict) -> Tuple[bool, List[str]]:
        return validation.validate_item(data)

    def batch_update_status(
        self, ids: Any, new_status: str, updated_by: str
    ) -> dict:
        if not new_status:
            raise ItemDataError("new_status is required")

        results = {"updated": [], "failed": [], "skipped": []}
        unique_ids = batch.normalize_ids(ids)
        batch.enforce_batch_limit(unique_ids)

        for identifier in unique_ids:
            record = self.db.get(identifier)
            action, reason = batch.plan_update(record, new_status)
            if action == batch.ACTION_FAILED:
                results["failed"].append({"id": identifier, "reason": reason})
            elif action == batch.ACTION_SKIPPED:
                results["skipped"].append({"id": identifier, "reason": reason})
            else:
                updated = batch.apply_update(record, new_status, updated_by)
                self.db.save(updated)
                results["updated"].append(identifier)

        return results
