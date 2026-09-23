"""Field coercion shared by the priority strategies.

Items reach the strategies from several places: request payloads (strings),
the in-memory store (native types), and tests (a mix). These helpers normalize
the handful of fields the strategies care about and raise
:class:`InvalidItemError` when a value is present but unusable, rather than
letting a ``TypeError`` leak out mid-calculation.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from .errors import InvalidItemError
from .protocol import Item


def now_utc() -> datetime:
    """Timezone-aware 'now'. Kept as a seam so tests can compare deterministically."""
    return datetime.now(timezone.utc)


def as_utc(value: object, field: str) -> Optional[datetime]:
    """Coerce ``value`` to a timezone-aware UTC datetime, or ``None`` if absent.

    Accepts ``datetime`` instances and ISO-8601 strings. Naive datetimes are
    assumed to already be UTC, which matches the app's use of
    ``datetime.utcnow()`` when it writes records.
    """
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        # ``fromisoformat`` handles a trailing "Z" only on 3.11+; normalize it.
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(text)
        except ValueError as exc:
            raise InvalidItemError(
                f"{field!r} is not a valid ISO-8601 datetime: {value!r}",
                field=field,
            ) from exc
    if not isinstance(value, datetime):
        raise InvalidItemError(
            f"{field!r} must be a datetime or ISO-8601 string, got {type(value).__name__}",
            field=field,
        )
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def as_float(value: object, field: str, default: float = 0.0) -> float:
    """Coerce ``value`` to a float, using ``default`` when the field is absent."""
    if value is None:
        return default
    if isinstance(value, bool):
        # bool is an int subclass; treat it as a number deliberately.
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError as exc:
            raise InvalidItemError(
                f"{field!r} must be numeric, got {value!r}", field=field
            ) from exc
    raise InvalidItemError(
        f"{field!r} must be numeric, got {type(value).__name__}", field=field
    )


def age_days(item: Item, *, reference: Optional[datetime] = None) -> float:
    """Age of ``item`` in days based on its ``created_at`` field.

    Returns ``0.0`` when ``created_at`` is missing or lies in the future
    (clock skew), so aging never *reduces* an item's priority.
    """
    created = as_utc(item.get("created_at"), field="created_at")
    if created is None:
        return 0.0
    reference = reference or now_utc()
    delta = (reference - created).total_seconds() / 86400.0
    return max(0.0, delta)


def time_to_due_days(
    item: Item, *, reference: Optional[datetime] = None
) -> Optional[float]:
    """Days until ``due_date``; negative when overdue, ``None`` when unset."""
    due = as_utc(item.get("due_date"), field="due_date")
    if due is None:
        return None
    reference = reference or now_utc()
    return (due - reference).total_seconds() / 86400.0
