"""
Input guardrails shared across the token-bucket rate limiter.

Centralizing these checks keeps a single, well-tested definition of "a valid
rate", "a valid token count", and "a valid key" in one place instead of
scattering the same comparisons through every method.

Non-finite values (``NaN`` and ``+/-inf``) are rejected up front. They are the
dangerous case: ``NaN`` compares ``False`` against every threshold, so a raw
``capacity <= 0`` guard lets it through and then silently poisons a bucket's
balance for the rest of its life. Catching them here turns a subtle corruption
into an immediate, obvious error.
"""

import math
from typing import Union

Number = Union[int, float]

# Tokens within this distance of a threshold are treated as equal. Continuous
# refill multiplies elapsed time by a rate, so a balance that is mathematically
# "exactly enough" can land a hair short; this epsilon absorbs that dust.
TOKEN_EPSILON = 1e-9


def _require_finite(value: Number, name: str) -> float:
    """Coerce ``value`` to ``float`` and reject NaN/inf with a clear message."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a real number, got {value!r}")
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite, got {result!r}")
    return result


def validate_capacity(capacity: Number) -> float:
    """Return ``capacity`` as a float or raise ``ValueError`` if not > 0."""
    result = _require_finite(capacity, "capacity")
    if result <= 0:
        raise ValueError(f"capacity must be greater than 0, got {result!r}")
    return result


def validate_refill_rate(refill_rate: Number) -> float:
    """Return ``refill_rate`` as a float or raise ``ValueError`` if negative."""
    result = _require_finite(refill_rate, "refill_rate")
    if result < 0:
        raise ValueError(f"refill_rate must not be negative, got {result!r}")
    return result


def validate_token_request(tokens: Number) -> float:
    """Return the requested ``tokens`` as a float or raise if not > 0."""
    result = _require_finite(tokens, "tokens")
    if result <= 0:
        raise ValueError(f"tokens must be greater than 0, got {result!r}")
    return result


def clamp_initial_tokens(initial_tokens: Number, capacity: float) -> float:
    """Coerce a starting balance into the valid ``[0, capacity]`` range."""
    result = _require_finite(initial_tokens, "initial_tokens")
    if result < 0:
        return 0.0
    if result > capacity:
        return capacity
    return result


def validate_key(key: object) -> object:
    """Return ``key`` unchanged, or raise ``TypeError`` if it is unhashable.

    Per-key buckets live in a ``dict`` keyed by the caller identifier. An
    unhashable key (a ``list``, ``dict``, or ``set``) would otherwise fail deep
    inside the registry with a bare ``unhashable type`` message that never names
    the offending argument. Checking here reports the problem at the call site.
    """
    try:
        hash(key)
    except TypeError:
        raise TypeError(f"rate limiter key must be hashable, got {key!r}")
    return key
