from datetime import datetime, timedelta, timezone

from src.services.item_service import ItemService
from src.services.priority import (
    DeadlineStrategy,
    PriorityContext,
    PriorityLevel,
    PriorityResult,
    create_priority_strategy,
)

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_default_service_uses_weighted_strategy():
    service = ItemService(db=None)
    assert service.priority_strategy.name == "weighted"


def test_calculate_priority_returns_string_level():
    service = ItemService(db=None)
    level = service.calculate_priority({"urgency": 10}, now=NOW)
    assert level == "critical"
    assert isinstance(level, str)


def test_calculate_priority_matches_legacy_algorithm():
    # Mirrors the original urgency*10 + 50-critical + age scoring.
    service = ItemService(db=None)
    item = {
        "urgency": 3,
        "is_critical": True,
        "created_at": NOW - timedelta(days=10),
    }
    assert service.calculate_priority(item, now=NOW) == "critical"  # 30 + 50 = 80


def test_evaluate_priority_returns_full_result():
    service = ItemService(db=None)
    result = service.evaluate_priority({"urgency": 2}, now=NOW)
    assert isinstance(result, PriorityResult)
    assert result.level is PriorityLevel.MEDIUM
    assert result.reasons


def test_injected_strategy_changes_behavior():
    weighted = ItemService(db=None)
    deadline = ItemService(db=None, priority_strategy=DeadlineStrategy())

    item = {"urgency": 0, "due_date": (NOW + timedelta(hours=6)).isoformat()}

    # Weighted sees urgency 0 -> low; deadline sees a near deadline -> critical.
    assert weighted.calculate_priority(item, now=NOW) == "low"
    assert deadline.calculate_priority(item, now=NOW) == "critical"


def test_service_accepts_strategy_from_factory():
    service = ItemService(
        db=None, priority_strategy=create_priority_strategy("deadline")
    )
    item = {"due_date": (NOW + timedelta(days=5)).isoformat()}
    assert service.calculate_priority(item, now=NOW) == "medium"


def test_service_accepts_duck_typed_strategy():
    class AlwaysHigh:
        name = "always-high"

        def evaluate(self, context: PriorityContext) -> PriorityResult:
            return PriorityResult(level=PriorityLevel.HIGH, score=1.0)

    service = ItemService(db=None, priority_strategy=AlwaysHigh())
    assert service.calculate_priority({}, now=NOW) == "high"
