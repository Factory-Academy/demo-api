"""Tests for the strategy factory and its registry."""

import pytest

from src.services.priority import (
    PriorityInput,
    PriorityLevel,
    PriorityStrategy,
    SlaDeadlineStrategy,
    UnknownStrategyError,
    WeightedScoreStrategy,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from src.services.priority.factory import _REGISTRY


def test_builtins_are_registered():
    assert "weighted" in available_strategies()
    assert "sla" in available_strategies()


def test_create_returns_correct_types():
    assert isinstance(create_priority_strategy("weighted"), WeightedScoreStrategy)
    assert isinstance(create_priority_strategy("sla"), SlaDeadlineStrategy)


def test_default_name_maps_to_weighted():
    assert create_priority_strategy("default").name == "weighted"
    assert create_priority_strategy().name == "weighted"


def test_created_strategies_satisfy_the_protocol():
    # runtime_checkable protocol: structural conformance, no base class needed.
    assert isinstance(create_priority_strategy("weighted"), PriorityStrategy)
    assert isinstance(create_priority_strategy("sla"), PriorityStrategy)


def test_unknown_strategy_raises_with_suggestions():
    with pytest.raises(UnknownStrategyError) as exc_info:
        create_priority_strategy("nope")
    assert exc_info.value.name == "nope"
    assert "weighted" in exc_info.value.available


def test_kwargs_are_forwarded_to_factory():
    fixed_clock = lambda: None  # noqa: E731 - never called, just identity-checked
    strategy = create_priority_strategy("weighted", clock=fixed_clock)
    assert strategy._clock is fixed_clock


def test_register_custom_strategy_roundtrips():
    class AlwaysCritical:
        name = "always-critical"

        def assess(self, item):
            from src.services.priority import PriorityAssessment

            return PriorityAssessment(PriorityLevel.CRITICAL, 0.0, "always", self.name)

    try:
        register_strategy("always-critical", lambda **kw: AlwaysCritical())
        strategy = create_priority_strategy("always-critical")
        result = strategy.assess(PriorityInput.from_item({}))
        assert result.level is PriorityLevel.CRITICAL
    finally:
        _REGISTRY.pop("always-critical", None)


def test_register_refuses_to_clobber_without_replace():
    with pytest.raises(ValueError):
        register_strategy("weighted", lambda **kw: None)


def test_register_allows_replace():
    original = _REGISTRY["sla"]
    try:
        register_strategy("sla", lambda **kw: SlaDeadlineStrategy(), replace=True)
        assert create_priority_strategy("sla").name == "sla"
    finally:
        _REGISTRY["sla"] = original


def test_register_rejects_empty_name():
    with pytest.raises(ValueError):
        register_strategy("", lambda **kw: None)
