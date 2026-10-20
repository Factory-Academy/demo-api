"""Concrete priority strategies.

Two deliberately different approaches ship here so the factory has something
to choose between and ``docs/NOTES.md`` has something to compare:

* :class:`WeightedScoreStrategy` - an additive scoring model (the original
  ``ItemService`` algorithm, generalized and made configurable).
* :class:`DeadlineStrategy` - a deadline/SLA-driven model that buckets items
  by how soon they are due rather than by an accumulated score.
"""

from __future__ import annotations

from typing import Mapping, Optional

from src.services.priority.base import (
    PriorityContext,
    PriorityLevel,
    PriorityResult,
)


class WeightedScoreStrategy:
    """Additive scoring: urgency, a criticality bonus, and an age penalty.

    This preserves the behavior of the original ``ItemService.calculate_priority``
    (urgency * 10, +50 when critical, +0.5 per day once older than 30 days, with
    80/50/20 cut-offs) while exposing every weight and threshold as a knob.
    """

    name = "weighted"

    def __init__(
        self,
        *,
        urgency_weight: float = 10.0,
        critical_bonus: float = 50.0,
        age_threshold_days: int = 30,
        age_weight: float = 0.5,
        thresholds: Optional[Mapping[PriorityLevel, float]] = None,
    ) -> None:
        self.urgency_weight = urgency_weight
        self.critical_bonus = critical_bonus
        self.age_threshold_days = age_threshold_days
        self.age_weight = age_weight
        self.thresholds = (
            dict(thresholds)
            if thresholds is not None
            else {
                PriorityLevel.CRITICAL: 80.0,
                PriorityLevel.HIGH: 50.0,
                PriorityLevel.MEDIUM: 20.0,
            }
        )
        self._validate_thresholds()

    def _validate_thresholds(self) -> None:
        required = (PriorityLevel.CRITICAL, PriorityLevel.HIGH, PriorityLevel.MEDIUM)
        missing = [level for level in required if level not in self.thresholds]
        if missing:
            names = ", ".join(level.value for level in missing)
            raise ValueError(f"missing threshold(s) for: {names}")
        critical = self.thresholds[PriorityLevel.CRITICAL]
        high = self.thresholds[PriorityLevel.HIGH]
        medium = self.thresholds[PriorityLevel.MEDIUM]
        if not (critical >= high >= medium):
            raise ValueError("thresholds must satisfy critical >= high >= medium")

    def evaluate(self, context: PriorityContext) -> PriorityResult:
        reasons = []

        score = context.urgency * self.urgency_weight
        reasons.append(
            f"urgency {context.urgency:g} x {self.urgency_weight:g} = {score:g}"
        )

        if context.is_critical:
            score += self.critical_bonus
            reasons.append(f"+{self.critical_bonus:g} critical bonus")

        # Floor the age to whole days so the penalty only kicks in on complete
        # days past the threshold, matching the original integer-day behavior.
        age_days = int(context.age_days)
        if age_days > self.age_threshold_days:
            bonus = age_days * self.age_weight
            score += bonus
            reasons.append(f"+{bonus:g} age penalty ({age_days}d old)")

        level = self._classify(score)
        return PriorityResult(level=level, score=score, reasons=reasons)

    def _classify(self, score: float) -> PriorityLevel:
        if score >= self.thresholds[PriorityLevel.CRITICAL]:
            return PriorityLevel.CRITICAL
        if score >= self.thresholds[PriorityLevel.HIGH]:
            return PriorityLevel.HIGH
        if score >= self.thresholds[PriorityLevel.MEDIUM]:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW


class DeadlineStrategy:
    """Deadline-driven: classify by how soon an item is due.

    Overdue items are always ``CRITICAL``. Otherwise the time remaining falls
    into configurable windows. When ``escalate_critical`` is set, a critical
    item is bumped up one level (so, e.g., a critical item due in 5 days lands
    at ``HIGH`` instead of ``MEDIUM``). Items with no due date cannot be placed
    on the timeline, so they fall back to a criticality-only classification.
    """

    name = "deadline"

    def __init__(
        self,
        *,
        critical_within_days: float = 1.0,
        high_within_days: float = 3.0,
        medium_within_days: float = 7.0,
        escalate_critical: bool = True,
    ) -> None:
        if not (critical_within_days <= high_within_days <= medium_within_days):
            raise ValueError(
                "deadline windows must be non-decreasing: "
                "critical <= high <= medium"
            )
        self.critical_within_days = critical_within_days
        self.high_within_days = high_within_days
        self.medium_within_days = medium_within_days
        self.escalate_critical = escalate_critical

    def evaluate(self, context: PriorityContext) -> PriorityResult:
        reasons = []
        days = context.days_until_due

        if days is None:
            level = PriorityLevel.HIGH if context.is_critical else PriorityLevel.LOW
            reasons.append("no due date; classified from criticality only")
            return PriorityResult(level=level, score=0.0, reasons=reasons)

        if context.is_overdue:
            level = PriorityLevel.CRITICAL
            score = 100.0
            reasons.append(f"overdue by {abs(days):.1f} day(s)")
        else:
            # Linear pressure: full marks at the deadline, shedding 10 points
            # per day of runway. Purely informational; classification below is
            # driven by the windows, not this number.
            score = max(0.0, 100.0 - days * 10.0)
            if days <= self.critical_within_days:
                level = PriorityLevel.CRITICAL
            elif days <= self.high_within_days:
                level = PriorityLevel.HIGH
            elif days <= self.medium_within_days:
                level = PriorityLevel.MEDIUM
            else:
                level = PriorityLevel.LOW
            reasons.append(f"{days:.1f} day(s) until due")

        if (
            self.escalate_critical
            and context.is_critical
            and level is not PriorityLevel.CRITICAL
        ):
            escalated = level.escalate()
            reasons.append(
                f"escalated {level.value} -> {escalated.value} (critical flag)"
            )
            level = escalated

        return PriorityResult(level=level, score=score, reasons=reasons)
