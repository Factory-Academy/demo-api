"""Pure validation for item payloads.

No I/O: the current time is injected so "due date in the past" checks are
deterministic. Values arrive from untrusted callers, so each rule coerces its
field defensively through :mod:`src.services.items._coerce` and reports a
problem instead of letting a raw ``TypeError`` escape. The error messages are
part of the public contract and are kept as named constants so callers can
assert against them without duplicating string literals.
"""
from __future__ import annotations

from datetime import datetime
from typing import List, Mapping, NamedTuple, Optional

from src.services.items._coerce import is_number, make_naive_utc, parse_timestamp

NAME_REQUIRED = "Name is required"
NAME_MUST_BE_TEXT = "Name must be text"
NEGATIVE_QUANTITY = "Quantity cannot be negative"
NON_NUMERIC_QUANTITY = "Quantity must be a number"
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
    if name is None:
        errors.append(NAME_REQUIRED)
    elif not isinstance(name, str):
        errors.append(NAME_MUST_BE_TEXT)
    elif len(name.strip()) == 0:
        errors.append(NAME_REQUIRED)

    if "quantity" in data:
        quantity = data["quantity"]
        if not is_number(quantity):
            errors.append(NON_NUMERIC_QUANTITY)
        elif quantity < 0:
            errors.append(NEGATIVE_QUANTITY)

    due_date = data.get("due_date")
    if due_date:
        due = parse_timestamp(due_date)
        if due is None:
            errors.append(INVALID_DATE_FORMAT)
        elif make_naive_utc(due) < make_naive_utc(now):
            errors.append(DUE_DATE_IN_PAST)

    return ValidationResult(len(errors) == 0, errors)
