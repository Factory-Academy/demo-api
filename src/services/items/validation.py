"""Pure validation for item payloads.

No I/O: the current time is injected so "due date in the past" checks are
deterministic. The error messages are part of the public contract and are kept
as named constants so callers can assert against them without duplicating
string literals.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Mapping, NamedTuple, Optional

NAME_REQUIRED = "Name is required"
NEGATIVE_QUANTITY = "Quantity cannot be negative"
DUE_DATE_IN_PAST = "Due date cannot be in the past"
INVALID_DATE_FORMAT = "Invalid date format"


class ValidationResult(NamedTuple):
    """Outcome of validating a payload.

    A :class:`~typing.NamedTuple` so it unpacks and compares exactly like the
    ``(is_valid, errors)`` tuple the original service returned, while also
    offering named access.
    """

    is_valid: bool
    errors: List[str]


def validate(data: Mapping, now: Optional[datetime] = None) -> ValidationResult:
    """Validate an item payload.

    ``now`` defaults to the current UTC time; pass it explicitly for
    deterministic results.
    """
    if now is None:
        now = datetime.utcnow()

    errors: List[str] = []

    name = data.get("name")
    if not name or len(name.strip()) == 0:
        errors.append(NAME_REQUIRED)

    if data.get("quantity", 0) < 0:
        errors.append(NEGATIVE_QUANTITY)

    due_date = data.get("due_date")
    if due_date:
        try:
            due = datetime.fromisoformat(due_date)
        except ValueError:
            errors.append(INVALID_DATE_FORMAT)
        else:
            if due < now:
                errors.append(DUE_DATE_IN_PAST)

    return ValidationResult(len(errors) == 0, errors)
