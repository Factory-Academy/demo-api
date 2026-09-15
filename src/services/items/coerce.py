"""Small, dependency-free coercion helpers for the item core.

The pure rule modules accept raw payloads that may carry missing, ``None``, or
otherwise malformed fields. Rather than each rule re-implementing "is this
actually a number?" checks, they share these helpers so the definition of a
usable number lives in exactly one place.
"""

from typing import Any


def is_number(value: Any) -> bool:
    """Return ``True`` only for real numeric values.

    ``bool`` is deliberately excluded even though it subclasses ``int``: a
    boolean in a numeric field (``quantity=True``) is almost always a payload
    bug, so callers treat it as non-numeric rather than silently as ``1``.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def as_number(value: Any, default: float = 0.0) -> float:
    """Coerce ``value`` to a number, falling back to ``default``.

    Missing (``None``) and non-numeric values collapse to ``default`` so
    best-effort scoring never raises on a malformed field.
    """
    return value if is_number(value) else default
