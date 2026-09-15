"""Pure decision logic for batch status updates.

The adapter is responsible for fetching and saving records. This module only
decides, for a record that has already been fetched, whether it should be
updated, skipped, or marked as failed, and computes the field changes to apply.
Keeping the branching here means the batch rules can be exercised without a
database.
"""

from datetime import datetime
from dataclasses import dataclass
from typing import Optional

UPDATE = "update"
SKIP = "skip"
FAIL = "fail"


@dataclass(frozen=True)
class Decision:
    """Outcome of classifying a single record for a batch update."""

    action: str
    reason: Optional[str] = None


def classify_record(record: Optional[dict], new_status: str) -> Decision:
    """Decide what should happen to one record given the requested status.

    - A missing record fails.
    - A record already in the requested status is skipped.
    - Anything else is updated.
    """
    if record is None:
        return Decision(FAIL, "not found")
    if record.get("status") == new_status:
        return Decision(SKIP, "already in state")
    return Decision(UPDATE)


def status_fields(
    new_status: str, updated_by: str, now: Optional[datetime] = None
) -> dict:
    """Build the field changes applied to a record during a status update."""
    if now is None:
        now = datetime.utcnow()
    return {
        "status": new_status,
        "updated_by": updated_by,
        "updated_at": now,
    }
