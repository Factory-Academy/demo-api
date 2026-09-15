"""Thin adapter wiring item persistence to the pure core.

All business rules live in :mod:`src.services.items`. This class only handles the
side-effecting parts: reading records from ``db``, applying the changes the core
decides on, and writing them back. The public interface is unchanged, so existing
callers keep working.
"""

from datetime import datetime

from src.services.items import (
    UPDATE,
    calculate_priority,
    classify_record,
    status_fields,
    validate_item,
)


class ItemService:
    def __init__(self, db):
        self.db = db

    def calculate_priority(self, item: dict) -> str:
        return calculate_priority(item)

    def validate_item(self, data: dict) -> tuple:
        return validate_item(data)

    def batch_update_status(
        self, ids: list, new_status: str, updated_by: str
    ) -> dict:
        results = {"updated": [], "failed": [], "skipped": []}
        # Pin the clock once so every record touched in a batch shares a timestamp.
        now = datetime.utcnow()

        for id in ids:
            record = self.db.get(id)
            decision = classify_record(record, new_status)

            if decision.action == UPDATE:
                record.update(status_fields(new_status, updated_by, now))
                self.db.save(record)
                results["updated"].append(id)
            else:
                results[_bucket(decision.action)].append(
                    {"id": id, "reason": decision.reason}
                )

        return results


def _bucket(action: str) -> str:
    return {"fail": "failed", "skip": "skipped"}[action]
