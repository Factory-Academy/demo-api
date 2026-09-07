from datetime import datetime
from typing import Optional

from src.clients.status_notifier import NotifierError
from src.utils.resilience import (
    BackoffPolicy,
    ResilienceError,
    RetryError,
    retry_with_backoff,
)


def retry(func, attempts: int = 3, exceptions: tuple = (Exception,)):
    """Retry ``func`` up to ``attempts`` times, re-raising the last error.

    Thin backwards-compatible wrapper over ``retry_with_backoff`` with no delay
    between attempts, preserved so existing callers keep working while sharing
    the hardened retry implementation.
    """
    try:
        return retry_with_backoff(
            func,
            retries=attempts - 1,
            retry_on=exceptions,
            policy=BackoffPolicy(base_delay=0, max_delay=0, jitter=False),
        )
    except RetryError as exc:
        raise exc.last_exception


class ItemService:
    def __init__(self, db, notifier=None):
        self.db = db
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
        results = {"updated": [], "failed": [], "skipped": [], "notify_failed": []}
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
            self._notify(id, new_status, updated_by, results)
        return results

    def _notify(self, id, new_status: str, updated_by: str, results: dict) -> None:
        # Downstream notification is best-effort: the local update has already
        # committed, so a notifier outage (circuit open, retries exhausted, or
        # a rejected request) must not fail the batch. Failures are reported
        # separately so callers can reconcile later.
        if self.notifier is None:
            return
        try:
            self.notifier.notify_status_change(id, new_status, updated_by=updated_by)
        except (ResilienceError, NotifierError) as exc:
            results["notify_failed"].append({"id": id, "reason": str(exc)})
