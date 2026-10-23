"""Pure validation rules for item payloads.

Each rule inspects a raw mapping and returns an error message or ``None``.
Rules never raise on malformed input, so callers can run the whole set against
untrusted data safely.
"""

from __future__ import annotations

from datetime import datetime
from numbers import Real
from typing import Any, List, Mapping, Optional, Tuple

from src.services.priority.normalization import coerce_timestamp


def validate_name(data: Mapping[str, Any]) -> Optional[str]:
    """Require a non-empty string name."""
    name = data.get("name")
    if name is None:
        return "Name is required"
    if not isinstance(name, str):
        return "Name must be a string"
    if len(name.strip()) == 0:
        return "Name is required"
    return None


def validate_quantity(data: Mapping[str, Any]) -> Optional[str]:
    """Reject negative or non-numeric quantities."""
    if "quantity" not in data:
        return None
    quantity = data.get("quantity")
    if isinstance(quantity, bool) or not isinstance(quantity, Real):
        return "Quantity must be a number"
    if quantity < 0:
        return "Quantity cannot be negative"
    return None


def validate_due_date(
    data: Mapping[str, Any], *, now: Optional[datetime] = None
) -> Optional[str]:
    """Reject past or malformed due dates; absent/empty values pass."""
    raw = data.get("due_date")
    if not raw:
        return None
    if not isinstance(raw, (str, datetime)):
        return "Invalid date format"
    due = coerce_timestamp(raw)
    if due is None:
        return "Invalid date format"
    reference = now if now is not None else datetime.utcnow()
    try:
        is_past = due < reference
    except TypeError:
        # Comparing naive and aware datetimes is ambiguous; flag as invalid.
        return "Invalid date format"
    if is_past:
        return "Due date cannot be in the past"
    return None


# Ordered so messages always surface in a predictable sequence.
_RULES = (validate_name, validate_quantity, validate_due_date)


def collect_errors(
    data: Optional[Mapping[str, Any]], *, now: Optional[datetime] = None
) -> List[str]:
    """Run every rule and return all error messages."""
    if not isinstance(data, Mapping):
        return ["Invalid payload"]
    errors: List[str] = []
    for rule in _RULES:
        if rule is validate_due_date:
            message = rule(data, now=now)
        else:
            message = rule(data)
        if message:
            errors.append(message)
    return errors


def validate_item(
    data: Optional[Mapping[str, Any]], *, now: Optional[datetime] = None
) -> Tuple[bool, List[str]]:
    """Return ``(is_valid, errors)`` for an item payload."""
    errors = collect_errors(data, now=now)
    return len(errors) == 0, errors
