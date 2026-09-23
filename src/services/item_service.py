from datetime import datetime
from typing import Optional

from src.services.priority import (
    DEFAULT_STRATEGY,
    PriorityStrategy,
    create_priority_strategy,
)


class ItemService:
    def __init__(self, db, priority_strategy: Optional[PriorityStrategy] = None):
        self.db = db
        # A strategy is stateless and thread-safe, so one instance is reused
        # for the life of the service. Callers can inject an alternative (for
        # example the deadline model) without changing this class.
        self.priority_strategy = priority_strategy or create_priority_strategy(
            DEFAULT_STRATEGY
        )

    def calculate_priority(self, item: dict) -> str:
        return self.priority_strategy.assess(item).level.value

    def validate_item(self, data: dict) -> tuple:
        errors = []
        if not data.get("name") or len(data["name"].strip()) == 0:
            errors.append("Name is required")
        if data.get("quantity", 0) < 0:
            errors.append("Quantity cannot be negative")
        if data.get("due_date"):
            try:
                due = datetime.fromisoformat(data["due_date"])
                if due < datetime.utcnow():
                    errors.append("Due date cannot be in the past")
            except ValueError:
                errors.append("Invalid date format")
        return len(errors) == 0, errors

    def batch_update_status(
        self, ids: list, new_status: str, updated_by: str
    ) -> dict:
        results = {"updated": [], "failed": [], "skipped": []}
        for id in ids:
            record = self.db.get(id)
            if record is None:
                results["failed"].append({"id": id, "reason": "not found"})
                continue
            if record.get("status") == new_status:
                results["skipped"].append({"id": id, "reason": "already in state"})
                continue
            record["status"] = new_status
            record["updated_by"] = updated_by
            record["updated_at"] = datetime.utcnow()
            self.db.save(record)
            results["updated"].append(id)
        return results
