from datetime import datetime, timedelta, timezone

import pytest

from src.services.priority import (
    DeadlineStrategy,
    PriorityContext,
    PriorityLevel,
    PriorityResult,
    WeightedScoreStrategy,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def ctx(**kwargs):
    kwargs.setdefault("now", NOW)
    return PriorityContext(**kwargs)


# --- PriorityLevel -------------------------------------------------------


def test_level_rank_order():
    assert PriorityLevel.LOW.rank < PriorityLevel.MEDIUM.rank
    assert PriorityLevel.MEDIUM.rank < PriorityLevel.HIGH.rank
    assert PriorityLevel.HIGH.rank < PriorityLevel.CRITICAL.rank


def test_level_escalate_steps_up_and_clamps():
    assert PriorityLevel.LOW.escalate() is PriorityLevel.MEDIUM
    assert PriorityLevel.MEDIUM.escalate() is PriorityLevel.HIGH
    assert PriorityLevel.HIGH.escalate() is PriorityLevel.CRITICAL
    assert PriorityLevel.CRITICAL.escalate() is PriorityLevel.CRITICAL


def test_level_is_str_valued():
    assert PriorityLevel.HIGH == "high"
    assert str(PriorityLevel.HIGH) == "high"


# --- PriorityContext.from_item ------------------------------------------


def test_from_item_parses_iso_string_due_date():
    context = PriorityContext.from_item(
        {"due_date": "2026-01-05T12:00:00+00:00"}, now=NOW
    )
    assert context.due_date == datetime(2026, 1, 5, 12, tzinfo=timezone.utc)
    assert context.days_until_due == pytest.approx(4.0)


def test_from_item_treats_naive_datetime_as_utc():
    context = PriorityContext.from_item(
        {"created_at": datetime(2025, 12, 2, 12, 0, 0)}, now=NOW
    )
    assert context.created_at.tzinfo is not None
    assert int(context.age_days) == 30


def test_from_item_clamps_negative_urgency():
    assert PriorityContext.from_item({"urgency": -5}, now=NOW).urgency == 0.0


def test_from_item_handles_bad_values_gracefully():
    context = PriorityContext.from_item(
        {"urgency": "oops", "due_date": "not-a-date", "created_at": 12345},
        now=NOW,
    )
    assert context.urgency == 0.0
    assert context.due_date is None
    assert context.created_at is None


def test_from_item_defaults_for_empty_payload():
    context = PriorityContext.from_item({}, now=NOW)
    assert context.urgency == 0.0
    assert context.is_critical is False
    assert context.age_days == 0.0
    assert context.days_until_due is None
    assert context.is_overdue is False


def test_age_days_never_negative_for_future_created_at():
    context = ctx(created_at=NOW + timedelta(days=5))
    assert context.age_days == 0.0


def test_is_overdue_detects_past_due_date():
    assert ctx(due_date=NOW - timedelta(hours=1)).is_overdue is True
    assert ctx(due_date=NOW + timedelta(hours=1)).is_overdue is False


# --- WeightedScoreStrategy ----------------------------------------------


@pytest.mark.parametrize(
    "urgency, expected_level",
    [
        (10, PriorityLevel.CRITICAL),  # 100
        (5, PriorityLevel.HIGH),       # 50
        (2, PriorityLevel.MEDIUM),     # 20
        (1, PriorityLevel.LOW),        # 10
        (0, PriorityLevel.LOW),        # 0
    ],
)
def test_weighted_urgency_thresholds(urgency, expected_level):
    result = WeightedScoreStrategy().evaluate(ctx(urgency=urgency))
    assert result.level is expected_level
    assert result.score == urgency * 10


def test_weighted_critical_bonus():
    result = WeightedScoreStrategy().evaluate(ctx(urgency=3, is_critical=True))
    assert result.score == 80  # 30 + 50
    assert result.level is PriorityLevel.CRITICAL
    assert any("critical" in reason for reason in result.reasons)


def test_weighted_age_penalty_applies_past_threshold():
    result = WeightedScoreStrategy().evaluate(
        ctx(urgency=2, created_at=NOW - timedelta(days=60))
    )
    # 20 (urgency) + 60 * 0.5 (age) = 50 -> high
    assert result.score == 50
    assert result.level is PriorityLevel.HIGH


def test_weighted_no_age_penalty_at_or_below_threshold():
    result = WeightedScoreStrategy().evaluate(
        ctx(urgency=2, created_at=NOW - timedelta(days=30))
    )
    assert result.score == 20
    assert result.level is PriorityLevel.MEDIUM


def test_weighted_custom_weights_and_thresholds():
    strategy = WeightedScoreStrategy(
        urgency_weight=1.0,
        critical_bonus=0.0,
        thresholds={
            PriorityLevel.CRITICAL: 9.0,
            PriorityLevel.HIGH: 5.0,
            PriorityLevel.MEDIUM: 2.0,
        },
    )
    assert strategy.evaluate(ctx(urgency=9)).level is PriorityLevel.CRITICAL
    assert strategy.evaluate(ctx(urgency=5)).level is PriorityLevel.HIGH


def test_weighted_rejects_misordered_thresholds():
    with pytest.raises(ValueError, match="critical >= high >= medium"):
        WeightedScoreStrategy(
            thresholds={
                PriorityLevel.CRITICAL: 10.0,
                PriorityLevel.HIGH: 50.0,
                PriorityLevel.MEDIUM: 20.0,
            }
        )


def test_weighted_rejects_missing_threshold():
    with pytest.raises(ValueError, match="missing threshold"):
        WeightedScoreStrategy(thresholds={PriorityLevel.CRITICAL: 80.0})


def test_weighted_returns_priority_result():
    result = WeightedScoreStrategy().evaluate(ctx(urgency=1))
    assert isinstance(result, PriorityResult)
    assert result.reasons  # non-empty audit trail


# --- DeadlineStrategy ----------------------------------------------------


@pytest.mark.parametrize(
    "days_out, expected_level",
    [
        (0.5, PriorityLevel.CRITICAL),
        (1.0, PriorityLevel.CRITICAL),  # boundary inclusive
        (2.0, PriorityLevel.HIGH),
        (3.0, PriorityLevel.HIGH),
        (5.0, PriorityLevel.MEDIUM),
        (7.0, PriorityLevel.MEDIUM),
        (30.0, PriorityLevel.LOW),
    ],
)
def test_deadline_windows(days_out, expected_level):
    result = DeadlineStrategy().evaluate(ctx(due_date=NOW + timedelta(days=days_out)))
    assert result.level is expected_level


def test_deadline_overdue_is_critical():
    result = DeadlineStrategy().evaluate(ctx(due_date=NOW - timedelta(days=2)))
    assert result.level is PriorityLevel.CRITICAL
    assert result.score == 100.0
    assert any("overdue" in reason for reason in result.reasons)


def test_deadline_without_due_date_uses_criticality():
    strategy = DeadlineStrategy()
    assert strategy.evaluate(ctx()).level is PriorityLevel.LOW
    assert strategy.evaluate(ctx(is_critical=True)).level is PriorityLevel.HIGH


def test_deadline_escalates_critical_items():
    result = DeadlineStrategy().evaluate(
        ctx(due_date=NOW + timedelta(days=5), is_critical=True)
    )
    # 5 days -> medium, escalated to high by the critical flag
    assert result.level is PriorityLevel.HIGH
    assert any("escalated" in reason for reason in result.reasons)


def test_deadline_escalation_can_be_disabled():
    result = DeadlineStrategy(escalate_critical=False).evaluate(
        ctx(due_date=NOW + timedelta(days=5), is_critical=True)
    )
    assert result.level is PriorityLevel.MEDIUM


def test_deadline_custom_windows():
    strategy = DeadlineStrategy(
        critical_within_days=2.0, high_within_days=4.0, medium_within_days=10.0
    )
    assert strategy.evaluate(
        ctx(due_date=NOW + timedelta(days=2))
    ).level is PriorityLevel.CRITICAL
    assert strategy.evaluate(
        ctx(due_date=NOW + timedelta(days=8))
    ).level is PriorityLevel.MEDIUM


def test_deadline_rejects_misordered_windows():
    with pytest.raises(ValueError, match="non-decreasing"):
        DeadlineStrategy(critical_within_days=5.0, high_within_days=1.0)
