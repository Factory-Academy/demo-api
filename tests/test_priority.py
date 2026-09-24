from datetime import datetime, timedelta, timezone

import pytest

from src.services.items import priority

NOW = datetime(2026, 9, 24, 12, 0, 0)


def _created(days_ago):
    return NOW - timedelta(days=days_ago)


class TestAgeInDays:
    def test_counts_whole_days(self):
        assert priority.age_in_days(_created(10), now=NOW) == 10

    def test_future_dates_clamp_to_zero(self):
        assert priority.age_in_days(NOW + timedelta(days=5), now=NOW) == 0

    def test_missing_timestamp_is_zero(self):
        assert priority.age_in_days(None, now=NOW) == 0

    def test_iso_string_timestamp(self):
        assert priority.age_in_days("2026-09-14T12:00:00", now=NOW) == 10

    def test_timezone_aware_timestamp_does_not_raise(self):
        aware = datetime(2026, 9, 14, 12, 0, 0, tzinfo=timezone.utc)
        assert priority.age_in_days(aware, now=NOW) == 10


class TestScoreComponents:
    def test_urgency_weighted(self):
        assert priority.urgency_score(3) == 30.0

    def test_negative_urgency_clamped(self):
        assert priority.urgency_score(-5) == 0.0

    def test_urgency_none_is_zero(self):
        assert priority.urgency_score(None) == 0.0

    def test_criticality_bonus(self):
        assert priority.criticality_bonus(True) == 50.0
        assert priority.criticality_bonus(False) == 0.0
        assert priority.criticality_bonus(None) == 0.0

    def test_aging_bonus_only_past_threshold(self):
        assert priority.aging_bonus(30) == 0.0
        assert priority.aging_bonus(40) == 20.0


class TestPriorityScoreAndLabel:
    def test_low_when_empty(self):
        assert priority.calculate_priority({}, now=NOW) == "low"

    def test_critical_flag_pushes_high(self):
        item = {"created_at": _created(0), "urgency": 0, "is_critical": True}
        assert priority.calculate_priority(item, now=NOW) == "high"

    def test_urgency_reaches_critical(self):
        item = {"created_at": _created(0), "urgency": 8}
        assert priority.calculate_priority(item, now=NOW) == "critical"

    def test_thresholds(self):
        assert priority.score_to_label(80) == "critical"
        assert priority.score_to_label(79.9) == "high"
        assert priority.score_to_label(50) == "high"
        assert priority.score_to_label(20) == "medium"
        assert priority.score_to_label(19.9) == "low"

    @pytest.mark.parametrize("bad_item", [None, [], "item", 42])
    def test_malformed_item_scores_low(self, bad_item):
        assert priority.priority_score(bad_item, now=NOW) == 0.0
        assert priority.calculate_priority(bad_item, now=NOW) == "low"

    def test_missing_created_at_does_not_raise(self):
        assert priority.calculate_priority({"urgency": 2}, now=NOW) == "medium"

    def test_malformed_urgency_does_not_raise(self):
        item = {"created_at": _created(0), "urgency": "not-a-number"}
        assert priority.calculate_priority(item, now=NOW) == "low"

    def test_aging_contributes(self):
        # 100 days old * 0.5 = 50 -> high, with no urgency or critical flag.
        item = {"created_at": _created(100)}
        assert priority.calculate_priority(item, now=NOW) == "high"
