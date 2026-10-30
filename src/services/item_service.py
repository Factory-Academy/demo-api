from datetime import datetime
from typing import Optional

from src.services.priority import (
    PriorityAssessment,
    PriorityInput,
    PriorityStrategy,
    create_priority_strategy,
)


class ItemService:
    def __init__(self, db, notifier=None, priority_strategy: Optional[PriorityStrategy] = None):
        self.db = db
        # Optional StatusNotifierClient; when set, status changes are pushed to
        # the external notifier on a best-effort basis.
        self.notifier = notifier
        # Pluggable priority heuristic. Defaults to the weighted strategy, whose
        # defaults reproduce the original inline scoring, so existing callers
        # see no behaviour change.
        self.priority_strategy = priority_strategy or create_priority_strategy("weighted")

    def calculate_priority(self, item: dict) -> str:
        return self.assess_priority(item).level.value

    def assess_priority(self, item: dict) -> PriorityAssessment:
        """Return the full assessment (level, score, reason) for an item."""
        return self.priority_strategy.assess(PriorityInput.from_item(item))

    def validate_item(self, data: dict, allow_past_dates: bool = False) -> tuple:
        errors = []
        if not data.get("name") or len(data["name"].strip()) == 0:
            errors.append("Name is required")
        if data.get("quantity", 0) < 0:
            errors.append("Quantity cannot be negative")
        if data.get("due_date"):
            try:
                due = datetime.fromisoformat(data["due_date"])
                if not allow_past_dates and due < datetime.utcnow():
                    errors.append("Due date cannot be in the past")
            except ValueError:
                errors.append("Invalid date format")
        return len(errors) == 0, errors

    def batch_update_status(
        self, ids: list, new_status: str, updated_by: str
    ) -> dict:
        results = {"updated": [], "failed": [], "skipped": [], "notified": []}
        for id in ids:
            record = self.db.get(id)
            if record is None:
                results["failed"].append({"id": id, "reason": "not found"})
                continue
            if record.get("status") == new_status:
                results["skipped"].append({"id": id, "reason": "already in state"})
                continue
            old_status = record.get("status")
            record["status"] = new_status
            record["updated_by"] = updated_by
            record["updated_at"] = datetime.utcnow()
            self.db.save(record)
            results["updated"].append(id)

            if self.notifier is not None:
                delivered = self.notifier.notify_status_change(
                    item_id=id,
                    old_status=old_status,
                    new_status=new_status,
                    updated_by=updated_by,
                )
                if delivered:
                    results["notified"].append(id)
        return results
