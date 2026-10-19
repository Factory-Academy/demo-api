from datetime import datetime
from typing import Any, List, Optional

from src.domain import BatchUpdateResult, ItemRecord, Priority, ValidationResult
from src.utils.caching import ttl_cache


class ItemService:
    def __init__(self, db: Any) -> None:
        """Initialize the service with the backing database-like dependency.

        ``db`` is expected to expose ``get(id) -> Optional[ItemRecord]`` and
        ``save(record)`` for persisting an :class:`ItemRecord`.
        """
        self.db = db

    @staticmethod
    def score(record: ItemRecord, now: Optional[datetime] = None) -> float:
        """Compute the raw urgency score for an item.

        Kept pure (no side effects, deterministic for a fixed ``now``) so the
        thresholds can be tested directly without the caching layer.
        """
        base_score = record.urgency * 10

        if record.is_critical:
            base_score += 50

        age_days = record.age_days(now)
        if age_days > 30:
            base_score += age_days * 0.5

        return base_score

    @staticmethod
    @ttl_cache(ttl=300, maxsize=100)
    def calculate_priority(record: ItemRecord) -> Priority:
        """Bucket an item into a :class:`Priority` based on its score."""
        return Priority.from_score(ItemService.score(record))

    def validate_item(
        self, record: ItemRecord, now: Optional[datetime] = None
    ) -> ValidationResult:
        """Enforce business rules on an item, returning structured errors."""
        reference = now if now is not None else datetime.utcnow()
        errors: List[str] = []

        if not record.name or len(record.name.strip()) == 0:
            errors.append("Name is required")
        if record.quantity < 0:
            errors.append("Quantity cannot be negative")
        if record.due_date is not None and record.due_date < reference:
            errors.append("Due date cannot be in the past")

        if errors:
            return ValidationResult.failed(errors)
        return ValidationResult.ok()

    def batch_update_status(
        self,
        ids: List[int],
        new_status: str,
        updated_by: str,
        now: Optional[datetime] = None,
    ) -> BatchUpdateResult:
        """Transition many items to ``new_status``, reporting per-id outcomes."""
        result = BatchUpdateResult()
        for item_id in ids:
            record = self.db.get(item_id)
            if record is None:
                result.mark_failed(item_id, "not found")
                continue
            if record.status == new_status:
                result.mark_skipped(item_id, "already in state")
                continue
            self.db.save(
                record.with_status(new_status, updated_by, now=now)
            )
            result.mark_updated(item_id)
        return result
