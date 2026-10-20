from datetime import datetime
from typing import Any, Optional
from src.services.priority import (
    PriorityContext,
    PriorityResult,
    PriorityStrategy,
    create_priority_strategy,
)


class ItemService:
    def __init__(
        self, db: Any, priority_strategy: Optional[PriorityStrategy] = None
    ) -> None:
        """Initialize the service with its dependencies.

        ``priority_strategy`` is pluggable; when omitted the default (weighted)
        strategy is used, preserving the service's historical scoring behavior.
        """
        self.db = db
        self.priority_strategy = priority_strategy or create_priority_strategy()

    def evaluate_priority(
        self, item: dict, now: Optional[datetime] = None
    ) -> PriorityResult:
        """Return the full priority result (level, score, and reasons).

        ``now`` is injectable so callers and tests can evaluate against a fixed
        reference time instead of the wall clock.
        """
        context = PriorityContext.from_item(item, now=now)
        return self.priority_strategy.evaluate(context)

    def calculate_priority(self, item: dict, now: Optional[datetime] = None) -> str:
        """Return only the priority level as a string.

        Thin wrapper over :meth:`evaluate_priority` that keeps the original
        ``str`` return contract for existing callers.
        """
        return self.evaluate_priority(item, now=now).level.value

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
