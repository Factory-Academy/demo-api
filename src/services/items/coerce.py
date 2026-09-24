"""Defensive coercion helpers shared by the item data-processing helpers.

Every function here is pure: it takes an arbitrary value and returns a
well-typed result (or a caller-supplied default) without raising. The original
``ItemService`` assumed inputs were always well-formed and blew up with
``TypeError``/``AttributeError`` on ``None``, wrong types, or malformed strings.
Centralising the coercion keeps that defensiveness in one tested place.
"""

import decimal
import math
import numbers
from datetime import datetime, timezone
from typing import Any, Optional

# Sentinel so callers can distinguish "absent" from "present but unparseable".
_MISSING = object()


def _finite(value: float, default: Any) -> Any:
    """Reject NaN/inf, which compare unpredictably against thresholds."""
    if math.isnan(value) or math.isinf(value):
        return default
    return value


def as_number(value: Any, default: Any = 0.0) -> Any:
    """Best-effort numeric coercion.

    Returns ``default`` for ``None``, blank strings, non-numeric strings, and
    unsupported types. Booleans are intentionally *not* treated as numbers so a
    stray ``True``/``False`` does not silently score as ``1``/``0``. Real
    numeric types beyond ``int``/``float`` (``Decimal``, ``Fraction``, and
    numpy scalars) are accepted, since rejecting them would drop otherwise valid
    quantities/urgencies to the default.
    """
    if value is None or isinstance(value, bool):
        return default
    # ``numbers.Real`` covers int/float/Fraction/numpy reals; ``Decimal`` is
    # deliberately not registered as ``Real`` upstream, so accept it explicitly.
    if isinstance(value, (numbers.Real, decimal.Decimal)):
        try:
            return _finite(float(value), default)
        except (ValueError, OverflowError):
            return default
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        try:
            return _finite(float(stripped), default)
        except ValueError:
            return default
    return default


def as_text(value: Any, default: str = "") -> str:
    """Return a stripped string, or ``default`` for ``None``/non-strings."""
    if isinstance(value, str):
        return value.strip()
    return default


def _to_naive_utc(dt: datetime) -> datetime:
    """Normalise to naive UTC so comparisons never mix aware/naive datetimes."""
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def as_datetime(value: Any, default: Optional[datetime] = None) -> Optional[datetime]:
    """Coerce a datetime or ISO-8601 string to a naive UTC datetime.

    Accepts a trailing ``Z`` (treated as UTC). Returns ``default`` for ``None``,
    blank/malformed strings, and unsupported types instead of raising.
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return _to_naive_utc(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return default
        # ``fromisoformat`` (pre-3.11) does not understand the ``Z`` suffix.
        candidate = stripped[:-1] + "+00:00" if stripped.endswith("Z") else stripped
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return default
        return _to_naive_utc(parsed)
    return default
