"""Weighted-score strategy.

Combines a few signals (urgency, a critical flag, and age) into a single numeric
score and maps that score onto a priority bucket. This is the original
``ItemService.calculate_priority`` heuristic, extracted behind the strategy
contract and made configurable; the defaults reproduce the original behaviour
exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from src.services.priority.models import (
    PriorityAssessment,
    PriorityInput,
    PriorityLevel,
)


@dataclass(frozen=True)
class WeightedScoreConfig:
    """Tunable weights and thresholds for :class:`WeightedScoreStrategy`.

    The defaults match the historical scoring: ``urgency * 10``, ``+50`` when
    critical, ``+0.5`` per day of age beyond 30 days, bucketed at ``>= 80``
    (critical), ``>= 50`` (high) and ``>= 20`` (medium).
    """

    urgency_weight: float = 10.0
    critical_bonus: float = 50.0
    age_threshold_days: int = 30
    age_weight: float = 0.5
    critical_at: float = 80.0
    high_at: float = 50.0
    medium_at: float = 20.0

    def __post_init__(self) -> None:
        if self.urgency_weight < 0:
            raise ValueError("urgency_weight must be non-negative")
        if self.critical_bonus < 0:
            raise ValueError("critical_bonus must be non-negative")
        if self.age_threshold_days < 0:
            raise ValueError("age_threshold_days must be non-negative")
        if self.age_weight < 0:
            raise ValueError("age_weight must be non-negative")
        if not (self.critical_at >= self.high_at >= self.medium_at >= 0):
            raise ValueError(
                "thresholds must satisfy critical_at >= high_at >= medium_at >= 0"
            )


class WeightedScoreStrategy:
    """Scores an item by a weighted sum of urgency, criticality and age.

    ``clock`` is injectable so age-based scoring can be tested without relying
    on the real wall clock.
    """

    def __init__(
        self,
        config: WeightedScoreConfig | None = None,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._config = config or WeightedScoreConfig()
        self._clock = clock

    @property
    def name(self) -> str:
        return "weighted"

    @property
    def config(self) -> WeightedScoreConfig:
        return self._config

    def assess(self, item: PriorityInput) -> PriorityAssessment:
        cfg = self._config
        score = item.urgency * cfg.urgency_weight
        if item.is_critical:
            score += cfg.critical_bonus

        age_days = 0
        if item.created_at is not None:
            age_days = (self._clock() - item.created_at).days
        if age_days > cfg.age_threshold_days:
            score += age_days * cfg.age_weight

        level = self._classify(score)
        reason = (
            f"weighted score {score:.1f} "
            f"(urgency={item.urgency}, critical={item.is_critical}, "
            f"age_days={age_days})"
        )
        return PriorityAssessment(level, score, reason, self.name)

    def _classify(self, score: float) -> PriorityLevel:
        cfg = self._config
        if score >= cfg.critical_at:
            return PriorityLevel.CRITICAL
        if score >= cfg.high_at:
            return PriorityLevel.HIGH
        if score >= cfg.medium_at:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW
