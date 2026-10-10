"""Thin adapter wiring the pure item core to a database.

:class:`ItemService` owns the only stateful concern -- reading and writing
records through ``db`` -- and delegates every scoring, validation, and
decision rule to the pure modules in this package.
"""
from __future__ import annotations

from datetime import datetime
from typing import Iterable, Mapping, Optional

from src.services.items import priority, status, validation
from src.services.items.validation import ValidationResult


class ItemService:
    def __init__(self, db):
        self.db = db

    def calculate_priority(
        self, item: Mapping, now: Optional[datetime] = None
    ) -> str:
        return priority.classify(item, now)

    def validate_item(
        self, data: Mapping, now: Optional[datetime] = None
    ) -> ValidationResult:
        return validation.validate(data, now)

    def batch_update_status(
        self,
        ids: Iterable,
        new_status: str,
        updated_by: str,
        now: Optional[datetime] = None,
    ) -> dict:
        results: dict = {"updated": [], "failed": [], "skipped": []}
        for id in ids:
            record = self.db.get(id)
            outcome = status.classify_status_change(record, new_status)
            if outcome is status.StatusChangeOutcome.NOT_FOUND:
                results["failed"].append(
                    {"id": id, "reason": status.REASON_NOT_FOUND}
                )
            elif outcome is status.StatusChangeOutcome.ALREADY_IN_STATE:
                results["skipped"].append(
                    {"id": id, "reason": status.REASON_ALREADY_IN_STATE}
                )
            else:
                status.apply_status_change(record, new_status, updated_by, now)
                self.db.save(record)
                results["updated"].append(id)
        return results
