import random
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class BackoffPolicy:
    """Computes the delay to wait between retry attempts.

    Delays grow exponentially (``base_delay * factor ** (attempt - 1)``) and are
    clamped to ``max_delay``. When ``jitter`` is enabled an "equal jitter"
    strategy is applied: half of the computed delay plus a random amount up to
    the other half. Jitter spreads retries from many callers so they do not
    hammer a recovering dependency in lockstep.
    """

    base_delay: float = 0.1
    factor: float = 2.0
    max_delay: float = 30.0
    jitter: bool = True

    def __post_init__(self) -> None:
        if self.base_delay < 0:
            raise ValueError("base_delay must be non-negative")
        if self.factor < 1:
            raise ValueError("factor must be at least 1")
        if self.max_delay < 0:
            raise ValueError("max_delay must be non-negative")

    def compute_delay(self, attempt: int, rng: Callable[[], float] = random.random) -> float:
        """Return the delay (in seconds) to wait after a completed ``attempt``.

        ``attempt`` is 1-based: ``1`` is the delay after the first failure.
        ``rng`` is injectable so tests can make jitter deterministic.
        """
        if attempt < 1:
            raise ValueError("attempt must be at least 1")

        raw = self.base_delay * (self.factor ** (attempt - 1))
        delay = min(raw, self.max_delay)

        if self.jitter and delay > 0:
            half = delay / 2
            delay = half + rng() * half

        return delay
