"""Tests for the SLA / deadline strategy."""

from datetime import datetime, timedelta

import pytest

from src.services.priority import (
    PriorityInput,
    PriorityLevel,
    SlaDeadlineConfig,
    SlaDeadlineStrategy,
)

NOW = datetime(2026, 6, 1, 12, 0, 0)


def make_strategy(config=None):
    return SlaDeadlineStrategy(config=config, clock=lambda: NOW)


def assess(strategy, **fields):
    return strategy.assess(PriorityInput(**fields))


def test_name_is_sla():
    assert make_strategy().name == "sla"


def test_overdue_is_critical():
    result = assess(make_strategy(), due_date=NOW - timedelta(hours=1))
    assert result.level is PriorityLevel.CRITICAL
    assert result.score < 0
    assert "overdue" in result.reason


def test_due_soon_is_high():
    result = assess(make_strategy(), due_date=NOW + timedelta(hours=10))
    assert result.level is PriorityLevel.HIGH
    assert result.score == pytest.approx(10.0)


def test_due_this_week_is_medium():
    result = assess(make_strategy(), due_date=NOW + timedelta(hours=48))
    assert result.level is PriorityLevel.MEDIUM


def test_far_future_is_low():
    result = assess(make_strategy(), due_date=NOW + timedelta(days=30))
    assert result.level is PriorityLevel.LOW


def test_boundary_exactly_at_high_window_is_high():
    # Exactly 24h out is inclusive of the HIGH bucket.
    result = assess(make_strategy(), due_date=NOW + timedelta(hours=24))
    assert result.level is PriorityLevel.HIGH


def test_missing_due_date_defaults_to_low():
    result = assess(make_strategy(), due_date=None)
    assert result.level is PriorityLevel.LOW
    assert result.score == float("inf")
    assert "no due date" in result.reason


def test_missing_due_date_level_is_configurable():
    config = SlaDeadlineConfig(missing_due_date_level=PriorityLevel.MEDIUM)
    result = assess(make_strategy(config), due_date=None)
    assert result.level is PriorityLevel.MEDIUM


def test_critical_flag_escalates_one_bucket():
    # 48h out is normally MEDIUM; the critical flag bumps it to HIGH.
    result = assess(make_strategy(), due_date=NOW + timedelta(hours=48), is_critical=True)
    assert result.level is PriorityLevel.HIGH


def test_critical_escalation_caps_at_critical():
    result = assess(make_strategy(), due_date=NOW - timedelta(hours=1), is_critical=True)
    assert result.level is PriorityLevel.CRITICAL


def test_escalation_can_be_disabled():
    config = SlaDeadlineConfig(escalate_critical=False)
    result = assess(make_strategy(config), due_date=NOW + timedelta(hours=48), is_critical=True)
    assert result.level is PriorityLevel.MEDIUM


def test_config_validation_rejects_inverted_windows():
    with pytest.raises(ValueError):
        SlaDeadlineConfig(high_within_hours=72, medium_within_hours=24)
