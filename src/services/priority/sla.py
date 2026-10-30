"""SLA / deadline strategy.

Prioritises purely by how much time is left before an item's due date: the
closer (or more overdue) the deadline, the higher the priority. This is a
deliberately different philosophy from the weighted strategy, which ignores
deadlines entirely, and it exists to show that the two approaches are
interchangeable behind the same contract.
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
class SlaDeadlineConfig:
    """Thresholds (in hours) for :class:`SlaDeadlineStrategy`.

    An item due within ``high_within_hours`` is HIGH, within
    ``medium_within_hours`` is MEDIUM, already overdue is CRITICAL, and
    otherwise LOW. ``missing_due_date_level`` is used when an item has no
    deadline at all, and ``escalate_critical`` bumps a critical-flagged item up
    one bucket.
    """

    high_within_hours: float = 24.0
    medium_within_hours: float = 72.0
    missing_due_date_level: PriorityLevel = PriorityLevel.LOW
    escalate_critical: bool = True

    def __post_init__(self) -> None:
        if self.high_within_hours <= 0:
            raise ValueError("high_within_hours must be positive")
        if self.medium_within_hours <= 0:
            raise ValueError("medium_within_hours must be positive")
        if self.medium_within_hours < self.high_within_hours:
            raise ValueError(
                "medium_within_hours must be >= high_within_hours"
            )


class SlaDeadlineStrategy:
    """Scores an item by time remaining until its due date.

    ``clock`` is injectable so deadline maths can be tested deterministically.
    """

    def __init__(
        self,
        config: SlaDeadlineConfig | None = None,
        clock: Callable[[], datetime] = datetime.utcnow,
    ) -> None:
        self._config = config or SlaDeadlineConfig()
        self._clock = clock

    @property
    def name(self) -> str:
        return "sla"

    @property
    def config(self) -> SlaDeadlineConfig:
        return self._config

    def assess(self, item: PriorityInput) -> PriorityAssessment:
        cfg = self._config

        if item.due_date is None:
            base = cfg.missing_due_date_level
            level = self._maybe_escalate(base, item)
            return PriorityAssessment(
                level,
                float("inf"),
                "no due date; no deadline pressure",
                self.name,
            )

        hours_remaining = (item.due_date - self._clock()).total_seconds() / 3600.0
        base = self._classify(hours_remaining)
        level = self._maybe_escalate(base, item)

        if hours_remaining <= 0:
            detail = f"overdue by {abs(hours_remaining):.1f}h"
        else:
            detail = f"{hours_remaining:.1f}h until due"
        return PriorityAssessment(level, hours_remaining, detail, self.name)

    def _classify(self, hours_remaining: float) -> PriorityLevel:
        cfg = self._config
        if hours_remaining <= 0:
            return PriorityLevel.CRITICAL
        if hours_remaining <= cfg.high_within_hours:
            return PriorityLevel.HIGH
        if hours_remaining <= cfg.medium_within_hours:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW

    def _maybe_escalate(
        self, base: PriorityLevel, item: PriorityInput
    ) -> PriorityLevel:
        if item.is_critical and self._config.escalate_critical:
            return base.escalate()
        return base
