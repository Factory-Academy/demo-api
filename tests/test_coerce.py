from datetime import datetime, timezone
from decimal import Decimal
from fractions import Fraction

import pytest

from src.services.items import coerce


class TestAsNumber:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (5, 5.0),
            (2.5, 2.5),
            ("7", 7.0),
            ("  3.5  ", 3.5),
            (-4, -4.0),
        ],
    )
    def test_parses_numbers(self, value, expected):
        assert coerce.as_number(value) == expected

    @pytest.mark.parametrize("value", [None, "", "   ", "abc", [], {}, object()])
    def test_falls_back_to_default(self, value):
        assert coerce.as_number(value, default=0.0) == 0.0

    def test_booleans_are_not_numbers(self):
        # A stray bool must not silently score as 1/0.
        assert coerce.as_number(True, default=99.0) == 99.0
        assert coerce.as_number(False, default=99.0) == 99.0

    @pytest.mark.parametrize(
        "value,expected",
        [
            (Decimal("3.5"), 3.5),
            (Decimal("-4"), -4.0),
            (Fraction(1, 2), 0.5),
            (Fraction(7, 1), 7.0),
        ],
    )
    def test_accepts_real_numeric_types(self, value, expected):
        # Regression: Decimal/Fraction fell through to the default before.
        assert coerce.as_number(value) == expected

    @pytest.mark.parametrize("value", [Decimal("nan"), Decimal("inf"), Decimal("-inf")])
    def test_rejects_non_finite_decimals(self, value):
        assert coerce.as_number(value, default=0.0) == 0.0

    def test_rejects_overflowing_decimal(self):
        # float(Decimal("1e400")) -> inf, which _finite rejects.
        assert coerce.as_number(Decimal("1e400"), default=0.0) == 0.0

    @pytest.mark.parametrize("value", ["nan", "inf", "-inf", float("nan"), float("inf")])
    def test_rejects_non_finite(self, value):
        assert coerce.as_number(value, default=0.0) == 0.0

    def test_custom_default_sentinel(self):
        assert coerce.as_number("nope", default=None) is None


class TestAsText:
    def test_strips_strings(self):
        assert coerce.as_text("  hi  ") == "hi"

    @pytest.mark.parametrize("value", [None, 5, [], {}])
    def test_non_strings_use_default(self, value):
        assert coerce.as_text(value, default="fallback") == "fallback"


class TestAsDatetime:
    def test_passes_through_naive_datetime(self):
        dt = datetime(2026, 1, 1, 12, 0, 0)
        assert coerce.as_datetime(dt) == dt

    def test_normalises_aware_to_naive_utc(self):
        aware = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        result = coerce.as_datetime(aware)
        assert result.tzinfo is None
        assert result == datetime(2026, 1, 1, 12, 0, 0)

    def test_parses_iso_string(self):
        assert coerce.as_datetime("2026-01-01T12:00:00") == datetime(2026, 1, 1, 12, 0, 0)

    def test_parses_trailing_z(self):
        assert coerce.as_datetime("2026-01-01T12:00:00Z") == datetime(2026, 1, 1, 12, 0, 0)

    @pytest.mark.parametrize("value", [None, "", "   ", "not-a-date", 12345, []])
    def test_bad_values_use_default(self, value):
        assert coerce.as_datetime(value) is None
