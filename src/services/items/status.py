"""Pure decision logic for batch status changes.

The side effects (reading and writing records) live in the adapter. Here we
only decide what *should* happen to a record and build the field updates, so
the branching rules can be tested without a database.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import MutableMapping, Optional

# Reasons reported back to callers. Kept as constants to match the original
# service's result payload exactly.
REASON_NOT_FOUND = "not found"
REASON_ALREADY_IN_STATE = "already in state"


class StatusChangeOutcome(Enum):
    """What should happen to a single record during a batch update."""

    NOT_FOUND = "not_found"
    ALREADY_IN_STATE = "already_in_state"
    UPDATE = "update"


def classify_status_change(
    record: Optional[MutableMapping], new_status: str
) -> StatusChangeOutcome:
    """Decide the outcome for one record without mutating anything."""
    if record is None:
        return StatusChangeOutcome.NOT_FOUND
    if record.get("status") == new_status:
        return StatusChangeOutcome.ALREADY_IN_STATE
    return StatusChangeOutcome.UPDATE


def status_change_fields(
    new_status: str, updated_by: str, now: Optional[datetime] = None
) -> dict:
    """Build the fields to write when applying a status change."""
    if now is None:
        now = datetime.utcnow()
    return {
        "status": new_status,
        "updated_by": updated_by,
        "updated_at": now,
    }


def apply_status_change(
    record: MutableMapping,
    new_status: str,
    updated_by: str,
    now: Optional[datetime] = None,
) -> MutableMapping:
    """Apply a status change to ``record`` in place and return it.

    Mutating in place (rather than copying) preserves the original behavior,
    where the same object was handed to ``db.save``.
    """
    record.update(status_change_fields(new_status, updated_by, now))
    return record
