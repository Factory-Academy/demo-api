from datetime import datetime
from typing import Optional


class ItemService:
    def __init__(self, db):
        self.db = db

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
