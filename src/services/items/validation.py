"""Pure validation functions for item payloads.

Split out of ``ItemService.validate_item``. Each field validator returns either
``None`` (valid) or a single human-readable error string, which keeps them easy
to unit test in isolation. The original raised ``AttributeError`` on a
non-string name and only caught ``ValueError`` from date parsing, so a
non-string ``due_date`` (for example an ``int``) escaped as an uncaught
``TypeError``.
"""

from datetime import datetime
from typing import Any, List, Mapping, Optional, Tuple

from . import coerce

MAX_NAME_LENGTH = 255


def validate_name(name: Any) -> Optional[str]:
    if name is None:
        return "Name is required"
    if not isinstance(name, str):
        return "Name must be a string"
    if len(name.strip()) == 0:
        return "Name is required"
    if len(name) > MAX_NAME_LENGTH:
        return f"Name must be at most {MAX_NAME_LENGTH} characters"
    return None


def validate_quantity(quantity: Any) -> Optional[str]:
    # Quantity is optional; only validate when a value is supplied.
    if quantity is None:
        return None
    number = coerce.as_number(quantity, default=None)
    if number is None:
        return "Quantity must be a number"
    if number < 0:
        return "Quantity cannot be negative"
    return None


def validate_due_date(due_date: Any, *, now: Optional[datetime] = None) -> Optional[str]:
    if due_date is None or due_date == "":
        return None
    parsed = coerce.as_datetime(due_date)
    if parsed is None:
        return "Invalid date format"
    reference = now or datetime.utcnow()
    if parsed < reference:
        return "Due date cannot be in the past"
    return None


def collect_errors(data: Any, *, now: Optional[datetime] = None) -> List[str]:
    """Return every validation error for a payload (empty list means valid)."""
    if not isinstance(data, Mapping):
        return ["Invalid item payload"]
    checks = (
        validate_name(data.get("name")),
        validate_quantity(data.get("quantity")),
        validate_due_date(data.get("due_date"), now=now),
    )
    return [error for error in checks if error]


def validate_item(data: Any, *, now: Optional[datetime] = None) -> Tuple[bool, List[str]]:
    """Backwards-compatible entry point: ``(is_valid, errors)``."""
    errors = collect_errors(data, now=now)
    return len(errors) == 0, errors
