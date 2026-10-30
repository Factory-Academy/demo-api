from datetime import datetime
from typing import Optional
from src.utils.exceptions import ResourceNotFoundError, ValidationError


class ItemService:
    def __init__(self, db, notifier=None):
        self.db = db
        # Optional StatusNotifierClient; when set, status changes are pushed to
        # the external notifier on a best-effort basis.
        self.notifier = notifier

    def calculate_priority(self, item: dict) -> str:
        age_days = (datetime.utcnow() - item["created_at"]).days
        base_score = item.get("urgency", 0) * 10

        if item.get("is_critical"):
            base_score += 50

        if age_days > 30:
            base_score += age_days * 0.5

        if base_score >= 80:
            return "critical"
        elif base_score >= 50:
            return "high"
        elif base_score >= 20:
            return "medium"
        return "low"

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
            try:
                record = self.db.get(id)
                if record is None:
                    raise ResourceNotFoundError("Item", id)
                
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
            except ResourceNotFoundError as exc:
                results["failed"].append({"id": id, "reason": str(exc)})
        return results
