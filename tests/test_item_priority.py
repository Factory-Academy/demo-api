from datetime import datetime, timedelta, timezone

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


def test_age_in_days_none_created_at_is_zero():
    assert priority.age_in_days(None, BASE) == 0


def test_age_in_days_handles_mixed_tz_awareness():
    created = BASE.replace(tzinfo=timezone.utc)  # aware
    now = BASE + timedelta(days=10)  # naive
    # Must not raise comparing aware vs naive, and UTC values line up.
    assert priority.age_in_days(created, now) == 10


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


def test_inputs_from_item_missing_created_at_is_none():
    inputs = priority.inputs_from_item({"urgency": 1})
    assert inputs.created_at is None


def test_inputs_from_item_parses_iso_created_at():
    inputs = priority.inputs_from_item({"created_at": "2024-01-01T00:00:00"})
    assert inputs.created_at == BASE


def test_inputs_from_item_coerces_numeric_string_urgency():
    inputs = priority.inputs_from_item({"created_at": BASE, "urgency": "5"})
    assert inputs.urgency == 5


def test_inputs_from_item_defaults_junk_urgency_to_zero():
    inputs = priority.inputs_from_item({"created_at": BASE, "urgency": "abc"})
    assert inputs.urgency == 0


def test_classify_missing_created_at_scores_without_staleness():
    # No created_at -> no staleness bonus; urgency alone decides the level.
    item = {"urgency": 2}  # 2 * 10 = 20 -> medium
    assert priority.classify(item, now=BASE) == priority.MEDIUM


def test_classify_numeric_string_urgency_is_scored():
    item = {"created_at": BASE, "urgency": "5"}  # 50 -> high
    assert priority.classify(item, now=BASE) == priority.HIGH


def test_classify_junk_urgency_falls_back_to_low():
    item = {"created_at": BASE, "urgency": object()}
    assert priority.classify(item, now=BASE) == priority.LOW


def test_classify_tolerates_mixed_tz_created_at():
    item = {"created_at": BASE.replace(tzinfo=timezone.utc), "urgency": 0}
    now = BASE + timedelta(days=100)  # naive; 100 days stale
    # 100 * 0.5 = 50 -> high, and the aware/naive mix must not raise.
    assert priority.classify(item, now=now) == priority.HIGH
