"""Tests for the weighted-score strategy."""

from datetime import datetime, timedelta

import pytest

from src.services.priority import (
    PriorityInput,
    PriorityLevel,
    WeightedScoreConfig,
    WeightedScoreStrategy,
)

# A fixed "now" so age-based scoring is deterministic.
NOW = datetime(2026, 6, 1, 12, 0, 0)


def make_strategy(config=None):
    return WeightedScoreStrategy(config=config, clock=lambda: NOW)


def assess(strategy, **fields):
    return strategy.assess(PriorityInput(**fields))


def test_name_is_weighted():
    assert make_strategy().name == "weighted"


def test_low_priority_for_quiet_item():
    result = assess(make_strategy(), urgency=1)
    assert result.level is PriorityLevel.LOW
    assert result.score == 10.0


def test_medium_threshold():
    assert assess(make_strategy(), urgency=2).level is PriorityLevel.MEDIUM  # 20


def test_high_threshold():
    assert assess(make_strategy(), urgency=5).level is PriorityLevel.HIGH  # 50


def test_critical_flag_adds_bonus():
    # urgency 3 -> 30, +50 critical bonus -> 80 -> critical.
    result = assess(make_strategy(), urgency=3, is_critical=True)
    assert result.score == 80.0
    assert result.level is PriorityLevel.CRITICAL


def test_age_adds_to_score_only_beyond_threshold():
    strategy = make_strategy()
    # 40 days old: base 10 + (40 * 0.5) = 30 -> medium.
    old = assess(strategy, urgency=1, created_at=NOW - timedelta(days=40))
    assert old.score == pytest.approx(30.0)
    assert old.level is PriorityLevel.MEDIUM

    # 20 days old is within the 30-day threshold: no age contribution.
    recent = assess(strategy, urgency=1, created_at=NOW - timedelta(days=20))
    assert recent.score == 10.0


def test_missing_created_at_scores_as_brand_new():
    # No created_at must not raise; age contribution is simply zero.
    result = assess(make_strategy(), urgency=1, created_at=None)
    assert result.score == 10.0


def test_future_created_at_has_no_age_contribution():
    result = assess(make_strategy(), urgency=1, created_at=NOW + timedelta(days=10))
    assert result.score == 10.0


def test_reason_is_populated():
    result = assess(make_strategy(), urgency=2)
    assert "weighted score" in result.reason
    assert result.strategy == "weighted"


def test_custom_config_changes_buckets():
    config = WeightedScoreConfig(urgency_weight=1.0, medium_at=1.0, high_at=2.0, critical_at=3.0)
    strategy = make_strategy(config)
    assert assess(strategy, urgency=2).level is PriorityLevel.HIGH


def test_config_validation_rejects_bad_thresholds():
    with pytest.raises(ValueError):
        WeightedScoreConfig(critical_at=10, high_at=20)  # high above critical


def test_config_validation_rejects_negative_weight():
    with pytest.raises(ValueError):
        WeightedScoreConfig(urgency_weight=-1)
