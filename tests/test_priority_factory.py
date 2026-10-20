import pytest

from src.services.priority import (
    DeadlineStrategy,
    PriorityContext,
    PriorityLevel,
    PriorityResult,
    PriorityStrategy,
    WeightedScoreStrategy,
    available_strategies,
    create_priority_strategy,
    register_strategy,
)
from src.services.priority import factory as factory_module


@pytest.fixture
def clean_registry():
    """Snapshot and restore the global registry around a test."""
    snapshot = dict(factory_module._REGISTRY)
    yield
    factory_module._REGISTRY.clear()
    factory_module._REGISTRY.update(snapshot)


def test_create_default_is_weighted():
    strategy = create_priority_strategy()
    assert isinstance(strategy, WeightedScoreStrategy)
    assert strategy.name == "weighted"


def test_create_named_strategies():
    assert isinstance(create_priority_strategy("weighted"), WeightedScoreStrategy)
    assert isinstance(create_priority_strategy("deadline"), DeadlineStrategy)


def test_create_is_case_and_whitespace_insensitive():
    assert isinstance(create_priority_strategy("  DEADLINE  "), DeadlineStrategy)


def test_create_forwards_kwargs():
    strategy = create_priority_strategy("deadline", critical_within_days=2.0)
    assert strategy.critical_within_days == 2.0


def test_create_unknown_strategy_lists_available():
    with pytest.raises(ValueError, match="unknown priority strategy"):
        create_priority_strategy("nope")

    with pytest.raises(ValueError, match="weighted"):
        create_priority_strategy("nope")


def test_available_strategies_sorted_and_complete():
    names = available_strategies()
    assert names == sorted(names)
    assert {"weighted", "deadline"} <= set(names)


def test_created_strategies_satisfy_protocol():
    for name in ("weighted", "deadline"):
        assert isinstance(create_priority_strategy(name), PriorityStrategy)


def test_register_new_strategy(clean_registry):
    class ConstantStrategy:
        name = "constant"

        def evaluate(self, context: PriorityContext) -> PriorityResult:
            return PriorityResult(level=PriorityLevel.LOW, score=0.0)

    register_strategy("constant", ConstantStrategy)

    assert "constant" in available_strategies()
    strategy = create_priority_strategy("constant")
    assert isinstance(strategy, ConstantStrategy)
    result = strategy.evaluate(PriorityContext.from_item({}))
    assert result.level is PriorityLevel.LOW


def test_register_duplicate_without_overwrite_raises(clean_registry):
    with pytest.raises(ValueError, match="already registered"):
        register_strategy("weighted", WeightedScoreStrategy)


def test_register_duplicate_with_overwrite(clean_registry):
    sentinel = object()

    def make_sentinel(**kwargs):
        return sentinel

    register_strategy("weighted", make_sentinel, overwrite=True)
    assert create_priority_strategy("weighted") is sentinel


def test_register_empty_name_raises(clean_registry):
    with pytest.raises(ValueError, match="non-empty"):
        register_strategy("   ", WeightedScoreStrategy)
