from datetime import datetime, timedelta

from src.services.priority import scoring


class TestComponents:
    def test_urgency_component(self):
        assert scoring.urgency_component(3) == 30.0

    def test_urgency_component_bad_input_is_zero(self):
        assert scoring.urgency_component("oops") == 0.0

    def test_critical_component_on(self):
        assert scoring.critical_component(True) == scoring.CRITICAL_BONUS

    def test_critical_component_off(self):
        assert scoring.critical_component(False) == 0.0

    def test_age_component_below_threshold(self):
        assert scoring.age_component(scoring.AGE_THRESHOLD_DAYS) == 0.0

    def test_age_component_above_threshold(self):
        assert scoring.age_component(40) == 40 * scoring.AGE_WEIGHT


class TestComputeScore:
    def test_combines_components(self):
        score = scoring.compute_score(urgency=4, is_critical=True, age_days=40)
        assert score == 40.0 + 50.0 + 20.0

    def test_clamps_at_zero(self):
        assert scoring.compute_score(urgency=-100) == 0.0

    def test_clamps_at_ceiling(self):
        huge = scoring.compute_score(urgency=10**9)
        assert huge == scoring.MAX_SCORE


class TestScoreItem:
    def test_malformed_item_scores_zero(self):
        assert scoring.score_item(None) == 0.0
        assert scoring.score_item("not a mapping") == 0.0

    def test_missing_created_at_does_not_raise(self):
        assert scoring.score_item({"urgency": 2}) == 20.0

    def test_iso_string_created_at(self):
        now = datetime(2026, 2, 15)
        item = {"urgency": 1, "created_at": "2026-01-01T00:00:00"}
        # 45 days old: 10 + (45 * 0.5) = 32.5
        assert scoring.score_item(item, now=now) == 32.5

    def test_string_urgency_is_coerced(self):
        assert scoring.score_item({"urgency": "5"}) == 50.0

    def test_future_created_at_adds_nothing(self):
        now = datetime(2026, 1, 1)
        item = {"urgency": 1, "created_at": now + timedelta(days=90)}
        assert scoring.score_item(item, now=now) == 10.0
