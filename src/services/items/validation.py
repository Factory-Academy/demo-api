"""Pure validation rules for item payloads.

Each rule is a small function returning an error message or ``None``. The public
``validate_item`` aggregates them and returns the ``(is_valid, errors)`` tuple
that the rest of the codebase already expects.
"""

from datetime import datetime
from typing import List, Optional, Tuple


def _validate_name(data: dict) -> Optional[str]:
    name = data.get("name")
    if not name or len(name.strip()) == 0:
        return "Name is required"
    return None


def _validate_quantity(data: dict) -> Optional[str]:
    if data.get("quantity", 0) < 0:
        return "Quantity cannot be negative"
    return None


def _validate_due_date(data: dict, now: datetime) -> Optional[str]:
    raw = data.get("due_date")
    if not raw:
        return None
    try:
        due = datetime.fromisoformat(raw)
    except ValueError:
        return "Invalid date format"
    if due < now:
        return "Due date cannot be in the past"
    return None


def validate_item(
    data: dict, *, now: Optional[datetime] = None
) -> Tuple[bool, List[str]]:
    """Validate an item payload.

    Returns ``(is_valid, errors)``. ``now`` is injectable for deterministic
    due-date tests; production callers omit it and get ``datetime.utcnow()``.
    """
    if now is None:
        now = datetime.utcnow()

    errors: List[str] = []
    for message in (
        _validate_name(data),
        _validate_quantity(data),
        _validate_due_date(data, now),
    ):
        if message is not None:
            errors.append(message)

    return len(errors) == 0, errors
