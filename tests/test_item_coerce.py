from datetime import datetime, timedelta, timezone

import pytest

from src.services.items import _coerce

BASE = datetime(2024, 1, 1, 0, 0, 0)


@pytest.mark.parametrize("value", [0, 1, -3, 2.5, -0.5])
def test_is_number_accepts_real_numbers(value):
    assert _coerce.is_number(value) is True


@pytest.mark.parametrize("value", [True, False, "5", None, [1], {"n": 1}, object()])
def test_is_number_rejects_non_numbers_and_bool(value):
    assert _coerce.is_number(value) is False


@pytest.mark.parametrize(
    "value,expected",
    [
        (5, 5.0),
        (-2, -2.0),
        (1.5, 1.5),
        ("7", 7.0),
        ("-3.5", -3.5),
    ],
)
def test_number_or_coerces_numbers_and_numeric_strings(value, expected):
    assert _coerce.number_or(value, default=0) == expected


@pytest.mark.parametrize("value", ["abc", None, [1], {"n": 1}, object()])
def test_number_or_falls_back_on_junk(value):
    assert _coerce.number_or(value, default=42) == 42


def test_parse_timestamp_reads_iso_string():
    assert _coerce.parse_timestamp("2024-01-01T00:00:00") == BASE


def test_parse_timestamp_accepts_trailing_z_as_utc():
    parsed = _coerce.parse_timestamp("2024-01-01T00:00:00Z")
    assert parsed == BASE.replace(tzinfo=timezone.utc)


def test_parse_timestamp_accepts_explicit_offset():
    parsed = _coerce.parse_timestamp("2024-01-01T00:00:00+00:00")
    assert parsed == BASE.replace(tzinfo=timezone.utc)


@pytest.mark.parametrize("value", ["", "   ", "not-a-date", 20240101, None, []])
def test_parse_timestamp_returns_none_for_unusable_input(value):
    assert _coerce.parse_timestamp(value) is None


def test_as_datetime_passes_through_existing_datetime():
    assert _coerce.as_datetime(BASE) is BASE


def test_as_datetime_parses_strings():
    assert _coerce.as_datetime("2024-01-01T00:00:00") == BASE


@pytest.mark.parametrize("value", [None, 123, [1]])
def test_as_datetime_returns_none_for_other_types(value):
    assert _coerce.as_datetime(value) is None


def test_make_naive_utc_leaves_naive_untouched():
    assert _coerce.make_naive_utc(BASE) == BASE
    assert _coerce.make_naive_utc(BASE).tzinfo is None


def test_make_naive_utc_converts_aware_to_utc_and_strips_tzinfo():
    eastern = timezone(timedelta(hours=-5))
    aware = BASE.replace(tzinfo=eastern)  # 00:00 at -05:00 == 05:00 UTC
    result = _coerce.make_naive_utc(aware)
    assert result.tzinfo is None
    assert result == datetime(2024, 1, 1, 5, 0, 0)


def test_make_naive_utc_allows_comparison_across_awareness():
    aware = BASE.replace(tzinfo=timezone.utc)
    naive = BASE
    # The point of the helper: this comparison would otherwise raise TypeError.
    assert _coerce.make_naive_utc(aware) == _coerce.make_naive_utc(naive)
