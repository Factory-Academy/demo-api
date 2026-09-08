"""
Numeric guardrails shared across the token-bucket rate limiter.

Centralizing these checks keeps a single, well-tested definition of "a valid
rate" and "a valid token count" in one place instead of scattering the same
comparisons through every method.

Non-finite values (``NaN`` and ``+/-inf``) are rejected up front. They are the
dangerous case: ``NaN`` compares ``False`` against every threshold, so a raw
``capacity <= 0`` guard lets it through and then silently poisons a bucket's
balance for the rest of its life. Catching them here turns a subtle corruption
into an immediate, obvious error.
"""
import math
from typing import Union

Number = Union[int, float]

# Token balances are floats refilled continuously, so repeated fractional
# arithmetic can leave a value a hair below a whole number (for example
# 0.9999999999 instead of 1.0). Comparisons allow this much slack so an exact
# request is never rejected by rounding dust.
TOKEN_EPSILON = 1e-9


def _require_finite(value: Number, name: str) -> float:
    """Coerce ``value`` to ``float`` and reject NaN/inf with a clear message."""
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be a finite number")
    return number


def validate_capacity(capacity: Number) -> float:
    """Return ``capacity`` as a float or raise ``ValueError`` if not > 0."""
    value = _require_finite(capacity, "capacity")
    if value <= 0:
        raise ValueError("capacity must be greater than 0")
    return value


def validate_refill_rate(refill_rate: Number) -> float:
    """Return ``refill_rate`` as a float or raise ``ValueError`` if negative."""
    value = _require_finite(refill_rate, "refill_rate")
    if value < 0:
        raise ValueError("refill_rate cannot be negative")
    return value


def validate_token_request(tokens: Number) -> float:
    """Return the requested ``tokens`` as a float or raise if not > 0."""
    value = _require_finite(tokens, "tokens")
    if value <= 0:
        raise ValueError("tokens must be greater than 0")
    return value


def clamp_initial_tokens(initial_tokens: Number, capacity: float) -> float:
    """Coerce a starting balance into the valid ``[0, capacity]`` range."""
    value = _require_finite(initial_tokens, "initial_tokens")
    return max(0.0, min(value, capacity))
