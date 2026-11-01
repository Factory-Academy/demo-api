"""Tests for how ItemService wires in the pluggable priority strategy."""

from datetime import datetime, timedelta

from src.services.item_service import ItemService
from src.services.priority import (
    PriorityLevel,
    SlaDeadlineStrategy,
    create_priority_strategy,
)


def make_service(strategy=None):
    return ItemService(db={}, priority_strategy=strategy)


def test_default_strategy_reproduces_legacy_scoring():
    # These are the exact buckets the old inline calculate_priority produced.
    service = make_service()
    now = datetime.utcnow()

    low = {"created_at": now, "urgency": 1}
    assert service.calculate_priority(low) == "low"

    medium = {"created_at": now, "urgency": 2}
    assert service.calculate_priority(medium) == "medium"

    critical = {"created_at": now, "urgency": 3, "is_critical": True}
    assert service.calculate_priority(critical) == "critical"


def test_calculate_priority_returns_plain_string():
    service = make_service()
    result = service.calculate_priority({"created_at": datetime.utcnow(), "urgency": 5})
    assert result == "high"
    assert isinstance(result, str)


def test_assess_priority_exposes_full_assessment():
    service = make_service()
    assessment = service.assess_priority({"created_at": datetime.utcnow(), "urgency": 5})
    assert assessment.level is PriorityLevel.HIGH
    assert assessment.strategy == "weighted"
    assert assessment.reason


def test_missing_created_at_no_longer_raises():
    # The old implementation did item["created_at"] and raised KeyError.
    service = make_service()
    assert service.calculate_priority({"urgency": 1}) == "low"


def test_service_honours_an_injected_sla_strategy():
    fixed_now = datetime(2026, 6, 1, 12, 0, 0)
    strategy = SlaDeadlineStrategy(clock=lambda: fixed_now)
    service = make_service(strategy)

    overdue = {"due_date": (fixed_now - timedelta(hours=1)).isoformat()}
    assert service.calculate_priority(overdue) == "critical"

    far_off = {"due_date": (fixed_now + timedelta(days=30)).isoformat()}
    assert service.calculate_priority(far_off) == "low"


def test_service_defaults_match_factory_default():
    service = make_service()
    assert service.priority_strategy.name == create_priority_strategy("default").name
