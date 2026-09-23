"""Tests for the pluggable priority-strategy package."""

from datetime import datetime, timedelta, timezone

import pytest

from src.services.item_service import ItemService
from src.services.priority import (
    DEFAULT_STRATEGY,
    DeadlineAwareStrategy,
    InvalidItemError,
    PriorityLevel,
    PriorityResult,
    PriorityStrategy,
    UnknownStrategyError,
    WeightedScoreStrategy,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from src.services.priority import coerce, factory


def days_ago(n: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(days=n)


def days_ahead(n: float) -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=n)


# --------------------------------------------------------------------------- #
# Factory / registry
# --------------------------------------------------------------------------- #


def test_default_strategy_is_weighted():
    strategy = create_priority_strategy()
    assert strategy.name == DEFAULT_STRATEGY == "weighted"
    assert isinstance(strategy, WeightedScoreStrategy)


def test_factory_builds_each_registered_strategy():
    assert set(available_strategies()) >= {"weighted", "deadline"}
    for name in available_strategies():
        assert create_priority_strategy(name).name == name


def test_factory_forwards_options():
    strategy = create_priority_strategy("deadline", high_within_days=5)
    assert strategy.high_within_days == 5


def test_unknown_strategy_raises_with_helpful_message():
    with pytest.raises(UnknownStrategyError) as exc:
        create_priority_strategy("does-not-exist")
    assert "does-not-exist" in str(exc.value)
    assert "weighted" in str(exc.value)
    assert exc.value.available == available_strategies()


def test_registered_strategies_satisfy_protocol():
    for name in available_strategies():
        assert isinstance(create_priority_strategy(name), PriorityStrategy)


def test_register_and_use_custom_strategy():
    class AlwaysCritical:
        name = "always-critical"

        def assess(self, item):
            return PriorityResult(PriorityLevel.CRITICAL, 999.0, "custom")

    register_strategy("always-critical", AlwaysCritical)
    try:
        strategy = create_priority_strategy("always-critical")
        assert strategy.assess({}).level is PriorityLevel.CRITICAL
    finally:
        factory._REGISTRY.pop("always-critical", None)


def test_register_rejects_duplicate_without_replace():
    with pytest.raises(ValueError):
        register_strategy("weighted", WeightedScoreStrategy)


def test_register_allows_replace():
    original = factory._REGISTRY["weighted"]
    try:
        register_strategy("weighted", DeadlineAwareStrategy, replace=True)
        assert isinstance(
            create_priority_strategy("weighted"), DeadlineAwareStrategy
        )
    finally:
        factory._REGISTRY["weighted"] = original


def test_register_rejects_empty_name():
    with pytest.raises(ValueError):
        register_strategy("", WeightedScoreStrategy)


# --------------------------------------------------------------------------- #
# WeightedScoreStrategy
# --------------------------------------------------------------------------- #


class TestWeightedScoreStrategy:
    def setup_method(self):
        self.strategy = WeightedScoreStrategy()

    def test_low_when_no_signal(self):
        result = self.strategy.assess({"created_at": days_ago(1), "urgency": 0})
        assert result.level is PriorityLevel.LOW
        assert result.score == 0.0

    def test_medium_threshold(self):
        # urgency 2 -> 20 points -> medium
        result = self.strategy.assess({"created_at": days_ago(1), "urgency": 2})
        assert result.level is PriorityLevel.MEDIUM
        assert result.score == 20.0

    def test_high_threshold(self):
        result = self.strategy.assess({"created_at": days_ago(1), "urgency": 5})
        assert result.level is PriorityLevel.HIGH
        assert result.score == 50.0

    def test_critical_flag_adds_bonus(self):
        # urgency 3 -> 30, +50 critical -> 80 -> critical
        result = self.strategy.assess(
            {"created_at": days_ago(1), "urgency": 3, "is_critical": True}
        )
        assert result.level is PriorityLevel.CRITICAL
        assert result.score == 80.0

    def test_aging_bonus_applies_past_grace(self):
        result = self.strategy.assess({"created_at": days_ago(100), "urgency": 0})
        # 100 days * 0.5 = 50 points from aging alone
        assert result.score == pytest.approx(50.0, abs=1.0)
        assert result.level is PriorityLevel.HIGH

    def test_no_aging_within_grace(self):
        result = self.strategy.assess({"created_at": days_ago(10), "urgency": 0})
        assert result.score == 0.0

    def test_missing_created_at_treated_as_new(self):
        result = self.strategy.assess({"urgency": 1})
        assert result.score == 10.0

    def test_reason_is_populated(self):
        result = self.strategy.assess({"created_at": days_ago(1), "urgency": 5})
        assert "urgency" in result.reason
        assert result.reason.startswith("high")

    def test_custom_thresholds(self):
        strategy = WeightedScoreStrategy(medium_threshold=5, urgency_weight=1)
        result = strategy.assess({"created_at": days_ago(1), "urgency": 6})
        assert result.level is PriorityLevel.MEDIUM

    def test_matches_original_behavior(self):
        # Regression guard: reproduce the pre-refactor additive model exactly.
        def legacy(item):
            age = (datetime.utcnow() - item["created_at"]).days
            score = item.get("urgency", 0) * 10
            if item.get("is_critical"):
                score += 50
            if age > 30:
                score += age * 0.5
            if score >= 80:
                return "critical"
            if score >= 50:
                return "high"
            if score >= 20:
                return "medium"
            return "low"

        cases = [
            {"created_at": days_ago(1), "urgency": 0},
            {"created_at": days_ago(1), "urgency": 2},
            {"created_at": days_ago(1), "urgency": 5},
            {"created_at": days_ago(1), "urgency": 3, "is_critical": True},
            {"created_at": days_ago(60), "urgency": 1},
            {"created_at": days_ago(200), "urgency": 0},
        ]
        for case in cases:
            # Compare against a naive-datetime copy for the legacy function.
            naive = dict(case)
            naive["created_at"] = case["created_at"].replace(tzinfo=None)
            assert self.strategy.assess(case).level.value == legacy(naive)


# --------------------------------------------------------------------------- #
# DeadlineAwareStrategy
# --------------------------------------------------------------------------- #


class TestDeadlineAwareStrategy:
    def setup_method(self):
        self.strategy = DeadlineAwareStrategy()

    def test_no_due_date_defaults_low(self):
        result = self.strategy.assess({})
        assert result.level is PriorityLevel.LOW
        assert result.score == float("-inf")

    def test_configurable_no_due_date_level(self):
        strategy = DeadlineAwareStrategy(no_due_date_level=PriorityLevel.MEDIUM)
        assert strategy.assess({}).level is PriorityLevel.MEDIUM

    def test_due_far_out_is_low(self):
        result = self.strategy.assess({"due_date": days_ahead(30)})
        assert result.level is PriorityLevel.LOW

    def test_due_this_week_is_medium(self):
        result = self.strategy.assess({"due_date": days_ahead(5)})
        assert result.level is PriorityLevel.MEDIUM

    def test_due_soon_is_high(self):
        result = self.strategy.assess({"due_date": days_ahead(2)})
        assert result.level is PriorityLevel.HIGH

    def test_due_tomorrow_is_critical(self):
        result = self.strategy.assess({"due_date": days_ahead(0.5)})
        assert result.level is PriorityLevel.CRITICAL

    def test_overdue_is_critical(self):
        result = self.strategy.assess({"due_date": days_ago(3)})
        assert result.level is PriorityLevel.CRITICAL
        assert result.score > 0  # negative-remaining => positive score
        assert "overdue" in result.reason

    def test_critical_flag_overrides_deadline(self):
        result = self.strategy.assess(
            {"due_date": days_ahead(365), "is_critical": True}
        )
        assert result.level is PriorityLevel.CRITICAL

    def test_score_orders_by_urgency(self):
        soon = self.strategy.assess({"due_date": days_ahead(1)})
        later = self.strategy.assess({"due_date": days_ahead(10)})
        assert soon.score > later.score

    def test_invalid_threshold_ordering_rejected(self):
        with pytest.raises(ValueError):
            DeadlineAwareStrategy(critical_within_days=10, high_within_days=1)


# --------------------------------------------------------------------------- #
# Coercion / edge cases
# --------------------------------------------------------------------------- #


class TestCoercion:
    def test_iso_string_created_at(self):
        strategy = WeightedScoreStrategy()
        iso = days_ago(200).isoformat()
        result = strategy.assess({"created_at": iso, "urgency": 0})
        assert result.score > 0  # aging kicked in

    def test_trailing_z_iso_string(self):
        parsed = coerce.as_utc("2020-01-01T00:00:00Z", field="due_date")
        assert parsed.tzinfo is not None
        assert parsed.year == 2020

    def test_naive_datetime_assumed_utc(self):
        naive = datetime(2020, 1, 1, 12, 0, 0)
        parsed = coerce.as_utc(naive, field="created_at")
        assert parsed.tzinfo == timezone.utc

    def test_empty_string_is_none(self):
        assert coerce.as_utc("", field="due_date") is None
        assert coerce.as_utc("   ", field="due_date") is None

    def test_invalid_date_raises(self):
        with pytest.raises(InvalidItemError) as exc:
            coerce.as_utc("not-a-date", field="due_date")
        assert exc.value.field == "due_date"

    def test_wrong_type_date_raises(self):
        with pytest.raises(InvalidItemError):
            coerce.as_utc(12345, field="created_at")

    def test_future_created_at_does_not_reduce_score(self):
        strategy = WeightedScoreStrategy()
        result = strategy.assess({"created_at": days_ahead(50), "urgency": 1})
        assert result.score == 10.0  # aging clamped to zero

    def test_urgency_numeric_string(self):
        assert coerce.as_float("3.5", field="urgency") == 3.5

    def test_urgency_bool_is_numeric(self):
        assert coerce.as_float(True, field="urgency") == 1.0

    def test_urgency_invalid_string_raises(self):
        with pytest.raises(InvalidItemError):
            coerce.as_float("high", field="urgency")

    def test_urgency_wrong_type_raises(self):
        with pytest.raises(InvalidItemError):
            coerce.as_float(["nope"], field="urgency")

    def test_missing_numeric_uses_default(self):
        assert coerce.as_float(None, field="urgency", default=7.0) == 7.0


# --------------------------------------------------------------------------- #
# Integration with ItemService
# --------------------------------------------------------------------------- #


class TestItemServiceIntegration:
    def test_default_service_uses_weighted(self):
        service = ItemService(db=None)
        assert isinstance(service.priority_strategy, WeightedScoreStrategy)

    def test_calculate_priority_returns_string_label(self):
        service = ItemService(db=None)
        label = service.calculate_priority(
            {"created_at": days_ago(1), "urgency": 5}
        )
        assert label == "high"
        assert isinstance(label, str)

    def test_injected_strategy_changes_result(self):
        service = ItemService(
            db=None, priority_strategy=DeadlineAwareStrategy()
        )
        label = service.calculate_priority({"due_date": days_ahead(0.5)})
        assert label == "critical"

    def test_priority_level_values_are_plain_strings(self):
        # The service contract returns bare strings the API already uses.
        for level in PriorityLevel:
            assert level.value == str(level.value)
