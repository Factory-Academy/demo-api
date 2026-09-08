"""
Token-bucket rate limiting utilities.

A small, dependency-free implementation of the token-bucket algorithm plus a
keyed registry for limiting many independent callers (users, API keys, IP
addresses) with a single object.

A token bucket holds up to ``capacity`` tokens and refills continuously at
``refill_rate`` tokens per second. Each request consumes one or more tokens;
when the bucket does not hold enough tokens the request is rejected. This
allows short bursts up to ``capacity`` while enforcing a steady long-run rate.

The package is split into focused modules:

- :mod:`~src.utils.rate_limiter.validation` — numeric guardrails (finite,
  positive, in-range) shared by both classes.
- :mod:`~src.utils.rate_limiter.errors` — the :class:`RateLimitExceeded`
  exception.
- :mod:`~src.utils.rate_limiter.bucket` — the single-bucket :class:`TokenBucket`.
- :mod:`~src.utils.rate_limiter.limiter` — the keyed :class:`RateLimiter`.

Importing the public names from this package keeps the historical import path
(``from src.utils.rate_limiter import RateLimiter``) stable.
"""
from .bucket import TokenBucket
from .errors import RateLimitExceeded
from .limiter import RateLimiter
from .validation import TOKEN_EPSILON

__all__ = [
    "TokenBucket",
    "RateLimiter",
    "RateLimitExceeded",
    "TOKEN_EPSILON",
]
