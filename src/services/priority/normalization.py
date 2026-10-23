"""Defensive coercion of raw item fields into well-typed values.

The scoring path receives dicts that originate from user input, external
systems, and the in-memory store, so individual fields may be missing, of the
wrong type, or malformed. Every function here is pure and total: it never
raises on bad input, returning a safe fallback instead.
"""

from __future__ import annotations

from datetime import datetime
from numbers import Real
from typing import Any, Optional


def coerce_timestamp(value: Any) -> Optional[datetime]:
    """Return a ``datetime`` for ``value`` or ``None`` when unparseable.

    Accepts an existing ``datetime`` or an ISO 8601 string. A trailing ``Z``
    is tolerated because :meth:`datetime.fromisoformat` does not accept it on
    Python 3.9/3.10.
    """
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        if text.endswith(("Z", "z")):
            text = text[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(text)
        except ValueError:
            return None
    return None


def compute_age_days(created_at: Any, *, now: Optional[datetime] = None) -> int:
    """Whole days between ``created_at`` and ``now``, clamped at zero.

    Future or missing timestamps yield ``0`` so they can never subtract from
    or inflate a score.
    """
    reference = now if now is not None else datetime.utcnow()
    timestamp = coerce_timestamp(created_at)
    if timestamp is None:
        return 0
    # Mixing naive and aware datetimes raises TypeError; treat as unknown age.
    try:
        delta_days = (reference - timestamp).days
    except TypeError:
        return 0
    return max(0, delta_days)


def coerce_non_negative_number(value: Any, default: float = 0.0) -> float:
    """Coerce ``value`` to a non-negative float.

    Booleans, non-numeric types, and non-numeric strings fall back to
    ``default``. Negative numbers clamp to ``0``.
    """
    if isinstance(value, bool):
        return float(default)
    number: Optional[float] = None
    if isinstance(value, Real):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip())
        except (ValueError, AttributeError):
            number = None
    if number is None:
        number = float(default)
    if number != number:  # NaN never compares true to itself.
        number = float(default)
    return max(0.0, number)


def coerce_flag(value: Any) -> bool:
    """Interpret ``value`` as a boolean flag without raising."""
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)
