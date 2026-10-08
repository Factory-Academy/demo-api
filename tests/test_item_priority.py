from datetime import datetime, timedelta

import pytest

from src.services.items import priority
from src.services.items.priority import PriorityInputs

BASE = datetime(2024, 1, 1, 0, 0, 0)


def test_age_in_days_truncates_toward_zero():
    now = BASE + timedelta(days=5, hours=23, minutes=59)
    assert priority.age_in_days(BASE, now) == 5


def test_age_in_days_zero_when_not_yet_a_full_day():
    now = BASE + timedelta(hours=23)
    assert priority.age_in_days(BASE, now) == 0


@pytest.mark.parametrize(
    "urgency,expected",
    [
        (0, 0),
        (2, 20),
        (5, 50),
        (8, 80),
    ],
)
def test_score_scales_with_urgency(urgency, expected):
    inputs = PriorityInputs(created_at=BASE, urgency=urgency)
    assert priority.score(inputs, now=BASE) == expected


def test_score_adds_critical_bonus():
    inputs = PriorityInputs(created_at=BASE, urgency=3, is_critical=True)
    assert priority.score(inputs, now=BASE) == 30 + priority.CRITICAL_BONUS


def test_score_ignores_age_at_or_below_threshold():
    inputs = PriorityInputs(created_at=BASE, urgency=0)
    now = BASE + timedelta(days=priority.STALE_AGE_DAYS)  # exactly 30 days
    assert priority.score(inputs, now=now) == 0


def test_score_adds_staleness_beyond_threshold():
    inputs = PriorityInputs(created_at=BASE, urgency=0)
    now = BASE + timedelta(days=100)
    assert priority.score(inputs, now=now) == 100 * priority.STALE_AGE_WEIGHT


@pytest.mark.parametrize(
    "value,level",
    [
        (80, priority.CRITICAL),
        (79.9, priority.HIGH),
        (50, priority.HIGH),
        (49.9, priority.MEDIUM),
        (20, priority.MEDIUM),
        (19.9, priority.LOW),
        (0, priority.LOW),
        (-5, priority.LOW),
    ],
)
def test_level_for_score_boundaries(value, level):
    assert priority.level_for_score(value) == level


def test_classify_fresh_low_priority_item():
    item = {"created_at": BASE, "urgency": 0}
    assert priority.classify(item, now=BASE) == priority.LOW


def test_classify_critical_from_bonus_plus_urgency():
    item = {"created_at": BASE, "urgency": 3, "is_critical": True}
    # 30 + 50 = 80 -> critical
    assert priority.classify(item, now=BASE) == priority.CRITICAL


def test_classify_uses_defaults_for_missing_fields():
    item = {"created_at": BASE}
    assert priority.classify(item, now=BASE) == priority.LOW


def test_classify_treats_truthy_is_critical_loosely():
    item = {"created_at": BASE, "urgency": 0, "is_critical": "yes"}
    # 0 + 50 = 50 -> high
    assert priority.classify(item, now=BASE) == priority.HIGH


def test_classify_negative_urgency_stays_low():
    item = {"created_at": BASE, "urgency": -10}
    assert priority.classify(item, now=BASE) == priority.LOW


def test_classify_defaults_now_to_current_time():
    # No injected clock: a just-created, zero-urgency item is low priority.
    item = {"created_at": datetime.utcnow(), "urgency": 0}
    assert priority.classify(item) == priority.LOW


def test_inputs_from_item_coerces_is_critical_to_bool():
    inputs = priority.inputs_from_item({"created_at": BASE, "is_critical": 1})
    assert inputs.is_critical is True
    assert inputs.urgency == 0
