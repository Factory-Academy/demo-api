"""Shared, dependency-free coercion helpers for the item core.

Both the priority scorer and the payload validator receive raw mappings whose
values may be missing, ``None``, or the wrong type. Centralising the "turn this
untrusted value into something safe to compute with" logic here keeps the
domain modules focused on their rules instead of repeating the same defensive
branches, and gives those edge cases one place to be tested.

Nothing here does I/O or reads the clock; every function is a pure
transformation of its arguments. The module is internal (hence the leading
underscore): callers depend on :mod:`~src.services.items.priority` and
:mod:`~src.services.items.validation`, not on these primitives.
"""
from __future__ import annotations

import numbers
from datetime import datetime, timezone
from typing import Optional


def is_number(value) -> bool:
    """True only for a real, non-boolean number (an ``int`` or ``float``).

    ``bool`` is a subclass of ``int`` in Python; excluding it here stops
    ``True``/``False`` from silently passing a check that expects a quantity.
    """
    return isinstance(value, numbers.Real) and not isinstance(value, bool)


def number_or(value, default: float) -> float:
    """Best-effort numeric coercion for scoring, which has no error channel.

    Accepts real numbers and numeric strings (e.g. ``"5"``); anything that
    cannot be read as a number falls back to ``default`` instead of raising, so
    a malformed field degrades a score rather than crashing it.
    """
    if is_number(value):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def parse_timestamp(value) -> Optional[datetime]:
    """Parse an ISO-8601 string into a :class:`~datetime.datetime`.

    Returns ``None`` for non-strings, blank strings, and unparseable text
    rather than raising. A trailing ``Z`` (UTC) is accepted on every supported
    Python version, not just 3.11+, by normalising it to ``+00:00`` first.
    """
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    if text[-1] in ("Z", "z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def as_datetime(value) -> Optional[datetime]:
    """Coerce ``value`` to a ``datetime`` if possible, else ``None``.

    An existing ``datetime`` is returned as-is and ISO-8601 strings are parsed;
    any other type yields ``None``.
    """
    if isinstance(value, datetime):
        return value
    return parse_timestamp(value)


def make_naive_utc(value: datetime) -> datetime:
    """Return a timezone-naive ``datetime`` expressed in UTC.

    Comparing a timezone-aware ``datetime`` with a naive one raises
    ``TypeError``. Normalising both operands through this helper lets the core
    order two timestamps regardless of how the caller supplied them: aware
    values are converted to UTC and stripped of their ``tzinfo``; naive values
    are assumed to already be UTC and returned unchanged.
    """
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value
