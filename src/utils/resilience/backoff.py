"""Backoff policies that decide how long to wait between retry attempts."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class BackoffPolicy:
    """Exponential backoff with optional full jitter.

    The delay before a given attempt grows geometrically with the attempt
    number and is capped at :attr:`max_delay`. With :attr:`jitter` enabled the
    returned delay is drawn uniformly from ``[0, computed_delay]`` ("full
    jitter"), which spreads out retries from many clients and avoids
    synchronised retry storms.
    """

    base_delay: float = 0.1
    max_delay: float = 30.0
    multiplier: float = 2.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.max_delay < self.base_delay:
            raise ValueError("max_delay must be >= base_delay")
        if self.multiplier < 1:
            raise ValueError("multiplier must be >= 1")

    def compute(self, attempt: int, rng: Optional[random.Random] = None) -> float:
        """Return the delay, in seconds, to wait before ``attempt``.

        ``attempt`` is 1-based: ``1`` is the delay before the first retry
        (i.e. after the first failure).
        """
        if attempt < 1:
            raise ValueError("attempt must be >= 1")
        raw = self.base_delay * (self.multiplier ** (attempt - 1))
        delay = min(raw, self.max_delay)
        if self.jitter:
            source = rng if rng is not None else random
            delay = source.uniform(0, delay)
        return delay
