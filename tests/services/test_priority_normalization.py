from datetime import datetime, timedelta, timezone

import pytest

from src.services.priority import normalization as norm


class TestCoerceTimestamp:
    def test_passes_through_datetime(self):
        now = datetime(2026, 1, 1, 12, 0, 0)
        assert norm.coerce_timestamp(now) is now

    def test_parses_iso_string(self):
        assert norm.coerce_timestamp("2026-01-01T12:00:00") == datetime(
            2026, 1, 1, 12, 0, 0
        )

    def test_tolerates_trailing_z(self):
        parsed = norm.coerce_timestamp("2026-01-01T12:00:00Z")
        assert parsed == datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    @pytest.mark.parametrize("value", [None, "", "   ", "not-a-date", 12345, []])
    def test_returns_none_for_unparseable(self, value):
        assert norm.coerce_timestamp(value) is None


class TestComputeAgeDays:
    def test_counts_whole_days(self):
        now = datetime(2026, 1, 31)
        created = datetime(2026, 1, 1)
        assert norm.compute_age_days(created, now=now) == 30

    def test_accepts_iso_string(self):
        now = datetime(2026, 1, 11)
        assert norm.compute_age_days("2026-01-01T00:00:00", now=now) == 10

    def test_future_timestamp_clamps_to_zero(self):
        now = datetime(2026, 1, 1)
        future = now + timedelta(days=5)
        assert norm.compute_age_days(future, now=now) == 0

    def test_missing_timestamp_is_zero(self):
        assert norm.compute_age_days(None, now=datetime(2026, 1, 1)) == 0

    def test_mixed_awareness_does_not_raise(self):
        aware = datetime(2026, 1, 1, tzinfo=timezone.utc)
        assert norm.compute_age_days(aware, now=datetime(2026, 2, 1)) == 0


class TestCoerceNonNegativeNumber:
    @pytest.mark.parametrize(
        "value,expected",
        [(5, 5.0), (3.5, 3.5), ("7", 7.0), ("  2.5 ", 2.5)],
    )
    def test_numeric_inputs(self, value, expected):
        assert norm.coerce_non_negative_number(value) == expected

    def test_negative_clamps_to_zero(self):
        assert norm.coerce_non_negative_number(-10) == 0.0

    @pytest.mark.parametrize("value", [None, "abc", object(), True, False, float("nan")])
    def test_bad_inputs_use_default(self, value):
        assert norm.coerce_non_negative_number(value) == 0.0

    def test_custom_default(self):
        assert norm.coerce_non_negative_number(None, default=1.0) == 1.0


class TestCoerceFlag:
    @pytest.mark.parametrize("value", [True, 1, "true", "YES", "on", "1"])
    def test_truthy(self, value):
        assert norm.coerce_flag(value) is True

    @pytest.mark.parametrize("value", [False, 0, "false", "no", "", None, "random"])
    def test_falsy(self, value):
        assert norm.coerce_flag(value) is False
