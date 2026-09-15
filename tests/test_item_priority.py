from datetime import datetime, timedelta

import pytest

from src.services.items.priority import (
    calculate_priority,
    label_for_score,
    priority_score,
)

NOW = datetime(2026, 1, 1, 12, 0, 0)


def _item(created_days_ago=0, **extra):
    item = {"created_at": NOW - timedelta(days=created_days_ago)}
    item.update(extra)
    return item


class TestPriorityScore:
    def test_defaults_to_zero_when_no_signals(self):
        assert priority_score(_item(), now=NOW) == 0

    def test_urgency_is_weighted_by_ten(self):
        assert priority_score(_item(urgency=3), now=NOW) == 30

    def test_missing_urgency_treated_as_zero(self):
        assert priority_score(_item(is_critical=False), now=NOW) == 0

    def test_critical_flag_adds_fixed_bonus(self):
        assert priority_score(_item(urgency=1, is_critical=True), now=NOW) == 60

    def test_falsy_critical_flag_adds_nothing(self):
        assert priority_score(_item(urgency=1, is_critical=False), now=NOW) == 10

    def test_age_at_threshold_adds_no_bonus(self):
        assert priority_score(_item(created_days_ago=30, urgency=1), now=NOW) == 10

    def test_age_beyond_threshold_adds_daily_weight(self):
        # 31 days old: 31 * 0.5 = 15.5 on top of urgency 1 * 10.
        assert priority_score(_item(created_days_ago=31, urgency=1), now=NOW) == 25.5

    def test_future_created_at_never_adds_age_bonus(self):
        score = priority_score(_item(created_days_ago=-100, urgency=2), now=NOW)
        assert score == 20

    def test_now_defaults_to_utcnow(self):
        # Freshly created item, so only urgency contributes regardless of clock.
        item = {"created_at": datetime.utcnow(), "urgency": 4}
        assert priority_score(item) == 40


class TestLabelForScore:
    @pytest.mark.parametrize(
        "score, expected",
        [
            (80, "critical"),
            (200, "critical"),
            (79.999, "high"),
            (50, "high"),
            (49.999, "medium"),
            (20, "medium"),
            (19.999, "low"),
            (0, "low"),
        ],
    )
    def test_boundaries(self, score, expected):
        assert label_for_score(score) == expected


class TestCalculatePriority:
    def test_critical_item(self):
        item = _item(urgency=4, is_critical=True)  # 40 + 50 = 90
        assert calculate_priority(item, now=NOW) == "critical"

    def test_high_item(self):
        item = _item(urgency=5)  # 50
        assert calculate_priority(item, now=NOW) == "high"

    def test_medium_item(self):
        item = _item(urgency=2)  # 20
        assert calculate_priority(item, now=NOW) == "medium"

    def test_low_item(self):
        item = _item(urgency=1)  # 10
        assert calculate_priority(item, now=NOW) == "low"

    def test_stale_low_urgency_item_escalates(self):
        # urgency 1 (=10) + 100 days * 0.5 (=50) = 60 -> high
        item = _item(created_days_ago=100, urgency=1)
        assert calculate_priority(item, now=NOW) == "high"

    def test_missing_created_at_raises(self):
        with pytest.raises(KeyError):
            calculate_priority({"urgency": 1}, now=NOW)
