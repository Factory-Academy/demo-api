"""Concrete priority strategies.

Two deliberately different approaches share the :class:`PriorityStrategy`
contract:

* :class:`WeightedScoreStrategy` -- an additive point model. It preserves the
  behavior the app shipped with (urgency weight + critical bonus + aging) so
  swapping it in is a no-op.
* :class:`DeadlineAwareStrategy` -- an SLA model driven by how close an item is
  to its due date. It ignores accumulated points and answers "how soon must
  this be dealt with?" instead.

See ``docs/NOTES.md`` for the trade-offs between them.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from . import coerce
from .protocol import Item, PriorityLevel, PriorityResult


class WeightedScoreStrategy:
    """Additive point model.

    ``score = urgency * urgency_weight + critical_bonus (if critical)
              + aging_bonus (once past ``aging_grace_days``)``

    The item is then bucketed against ``critical`` / ``high`` / ``medium``
    thresholds. Defaults reproduce the original ``ItemService`` behavior.
    """

    name = "weighted"

    def __init__(
        self,
        *,
        urgency_weight: float = 10.0,
        critical_bonus: float = 50.0,
        aging_grace_days: float = 30.0,
        aging_per_day: float = 0.5,
        critical_threshold: float = 80.0,
        high_threshold: float = 50.0,
        medium_threshold: float = 20.0,
    ):
        self.urgency_weight = urgency_weight
        self.critical_bonus = critical_bonus
        self.aging_grace_days = aging_grace_days
        self.aging_per_day = aging_per_day
        self.critical_threshold = critical_threshold
        self.high_threshold = high_threshold
        self.medium_threshold = medium_threshold

    def assess(self, item: Item) -> PriorityResult:
        reference = coerce.now_utc()
        urgency = coerce.as_float(item.get("urgency"), field="urgency", default=0.0)
        score = urgency * self.urgency_weight
        reasons = [f"urgency {urgency:g}x{self.urgency_weight:g}={score:g}"]

        if item.get("is_critical"):
            score += self.critical_bonus
            reasons.append(f"+{self.critical_bonus:g} critical")

        age = coerce.age_days(item, reference=reference)
        if age > self.aging_grace_days:
            aging = age * self.aging_per_day
            score += aging
            reasons.append(f"+{aging:g} aging({age:.0f}d)")

        level = self._bucket(score)
        return PriorityResult(
            level=level,
            score=score,
            reason=f"{level.value}: " + ", ".join(reasons),
        )

    def _bucket(self, score: float) -> PriorityLevel:
        if score >= self.critical_threshold:
            return PriorityLevel.CRITICAL
        if score >= self.high_threshold:
            return PriorityLevel.HIGH
        if score >= self.medium_threshold:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW


class DeadlineAwareStrategy:
    """SLA model driven by time remaining until the due date.

    An item with no due date falls back to ``no_due_date_level`` (default
    ``LOW``) because nothing is pulling it forward in time. A ``is_critical``
    flag pins the item to ``CRITICAL`` regardless of its deadline, since a
    critical item should never be allowed to sit.

    ``score`` is the negative number of days remaining, so that sorting by
    descending score puts the most overdue item first and keeps the ordering
    consistent with :class:`WeightedScoreStrategy` (higher = more urgent).
    """

    name = "deadline"

    def __init__(
        self,
        *,
        critical_within_days: float = 1.0,
        high_within_days: float = 3.0,
        medium_within_days: float = 7.0,
        no_due_date_level: PriorityLevel = PriorityLevel.LOW,
    ):
        if not (critical_within_days <= high_within_days <= medium_within_days):
            raise ValueError(
                "deadline thresholds must satisfy "
                "critical <= high <= medium"
            )
        self.critical_within_days = critical_within_days
        self.high_within_days = high_within_days
        self.medium_within_days = medium_within_days
        self.no_due_date_level = no_due_date_level

    def assess(self, item: Item) -> PriorityResult:
        reference = coerce.now_utc()
        remaining = coerce.time_to_due_days(item, reference=reference)

        if item.get("is_critical"):
            return PriorityResult(
                level=PriorityLevel.CRITICAL,
                score=float("inf") if remaining is None else -remaining,
                reason="critical: flagged critical",
            )

        if remaining is None:
            return PriorityResult(
                level=self.no_due_date_level,
                score=float("-inf"),
                reason=f"{self.no_due_date_level.value}: no due date",
            )

        score = -remaining
        level = self._bucket(remaining)
        if remaining < 0:
            detail = f"overdue by {-remaining:.1f}d"
        else:
            detail = f"due in {remaining:.1f}d"
        return PriorityResult(
            level=level, score=score, reason=f"{level.value}: {detail}"
        )

    def _bucket(self, remaining: float) -> PriorityLevel:
        # Overdue items are always critical.
        if remaining <= self.critical_within_days:
            return PriorityLevel.CRITICAL
        if remaining <= self.high_within_days:
            return PriorityLevel.HIGH
        if remaining <= self.medium_within_days:
            return PriorityLevel.MEDIUM
        return PriorityLevel.LOW
