from datetime import datetime
from typing import Any, Mapping, Optional

from src.domain.models import ItemRecord
from src.domain.priority import Priority, compute_priority
from src.domain.repository import InMemoryRepository
from src.domain.results import BatchOutcome, BatchUpdateResult, ValidationResult


class ItemService:
    def __init__(self, db: InMemoryRepository):
        self.db = db

    def calculate_priority(
        self, item: ItemRecord, *, now: Optional[datetime] = None
    ) -> Priority:
        return compute_priority(item, now=now)

    def validate_item(
        self, data: Mapping[str, Any], *, now: Optional[datetime] = None
    ) -> ValidationResult:
        moment = now or datetime.utcnow()
        errors = []

        name = data.get("name")
        if not name or len(name.strip()) == 0:
            errors.append("Name is required")

        if data.get("quantity", 0) < 0:
            errors.append("Quantity cannot be negative")

        due_date = data.get("due_date")
        if due_date:
            due = self._parse_due_date(due_date)
            if due is None:
                errors.append("Invalid date format")
            elif due < moment:
                errors.append("Due date cannot be in the past")

        return ValidationResult(is_valid=len(errors) == 0, errors=errors)

    def batch_update_status(
        self,
        ids: list,
        new_status: str,
        updated_by: str,
        *,
        now: Optional[datetime] = None,
    ) -> BatchUpdateResult:
        moment = now or datetime.utcnow()
        result = BatchUpdateResult()
        for id in ids:
            record = self.db.get(id)
            if record is None:
                result.failed.append(BatchOutcome(id=id, reason="not found"))
                continue
            if record.status == new_status:
                result.skipped.append(BatchOutcome(id=id, reason="already in state"))
                continue
            record.status = new_status
            record.updated_by = updated_by
            record.updated_at = moment
            self.db.save(record)
            result.updated.append(id)
        return result

    @staticmethod
    def _parse_due_date(value: Any) -> Optional[datetime]:
        if isinstance(value, datetime):
            return value
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
