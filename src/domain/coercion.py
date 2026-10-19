"""Defensive helpers for the domain boundary.

The domain dataclasses are reconstructed from loosely-typed mappings (previously
persisted ``dict`` payloads, decoded JSON, query params, ...). The helpers here
centralize the coercion and validation of those inputs so every record parses
loose values the same way and reports failures with a consistent, field-aware
``ValueError`` instead of a bare ``KeyError`` or an opaque ``int()`` message.
"""

from __future__ import annotations

from dataclasses import fields
from datetime import datetime
from typing import Any, Mapping, Optional

# Case-insensitive string spellings accepted for boolean fields. Anything else
# (e.g. ``"maybe"``) is rejected rather than silently coerced, which is the bug
# a plain ``bool("false") is True`` would hide when migrating stored payloads.
_TRUE_STRINGS = frozenset({"true", "t", "1", "yes", "y", "on"})
_FALSE_STRINGS = frozenset({"false", "f", "0", "no", "n", "off", ""})


def require(data: Mapping[str, Any], field: str) -> Any:
    """Return ``data[field]`` or raise a clear ``ValueError`` if absent."""
    try:
        return data[field]
    except KeyError:
        raise ValueError(f"Missing required field '{field}'") from None


def coerce_int(value: Any, *, field: str) -> int:
    """Coerce ``value`` to ``int``, rejecting bools and unparseable values.

    ``bool`` is a subclass of ``int`` in Python, so ``int(True)`` is ``1``.
    That is almost never intended for an id/count field, so booleans are
    rejected outright rather than silently treated as ``0``/``1``.
    """
    if isinstance(value, bool):
        raise ValueError(f"Expected an integer for '{field}', not a bool")
    try:
        return int(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid integer for '{field}': {value!r}") from error


def coerce_bool(value: Any, *, field: str) -> bool:
    """Coerce ``value`` to ``bool``, honoring common string spellings.

    ``None`` maps to ``False`` (treated as "absent"); numeric values follow
    truthiness; strings must match a known spelling or a ``ValueError`` is
    raised. This avoids the classic trap where ``bool("false")`` is ``True``.
    """
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in _TRUE_STRINGS:
            return True
        if normalized in _FALSE_STRINGS:
            return False
    raise ValueError(f"Invalid boolean for '{field}': {value!r}")


def coerce_datetime(
    value: Any, *, field: str, default: Optional[datetime]
) -> Optional[datetime]:
    """Coerce ``value`` to ``datetime``.

    ``None`` and blank/whitespace-only strings fall back to ``default`` (a blank
    stored timestamp means "not set", not a parse error). An already-parsed
    ``datetime`` passes through. A non-blank string must be ISO-8601 or a
    ``ValueError`` is raised.
    """
    if value is None:
        return default
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return datetime.fromisoformat(text)
        except ValueError as error:
            raise ValueError(
                f"Invalid date format for '{field}': {value!r}"
            ) from error
    raise ValueError(f"Invalid date value for '{field}': {value!r}")


def ensure_known_fields(record: Any, changes: Mapping[str, Any]) -> None:
    """Raise ``ValueError`` if ``changes`` names a field ``record`` does not have.

    ``dataclasses.replace`` already fails on an unknown keyword, but with a
    generic ``TypeError``; this surfaces the offending names and the record type
    so a mistyped ``with_changes`` call is obvious.
    """
    valid = {f.name for f in fields(record)}
    unknown = sorted(set(changes) - valid)
    if unknown:
        raise ValueError(
            f"Unknown field for {type(record).__name__}: {', '.join(unknown)}"
        )
