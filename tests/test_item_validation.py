from datetime import datetime

import pytest

from src.services.items import validation
from src.services.items.validation import ValidationResult

NOW = datetime(2024, 6, 1, 0, 0, 0)


def test_valid_payload():
    result = validation.validate({"name": "Widget", "quantity": 1}, now=NOW)
    assert result == (True, [])
    assert result.is_valid is True
    assert result.errors == []


def test_result_is_tuple_compatible():
    result = validation.validate({"name": "ok"}, now=NOW)
    ok, errors = result  # unpacks like the legacy tuple
    assert ok is True
    assert errors == []
    assert isinstance(result, tuple)


def test_missing_name_key():
    result = validation.validate({}, now=NOW)
    assert result.is_valid is False
    assert validation.NAME_REQUIRED in result.errors


def test_empty_name():
    result = validation.validate({"name": ""}, now=NOW)
    assert validation.NAME_REQUIRED in result.errors


def test_whitespace_only_name():
    result = validation.validate({"name": "   "}, now=NOW)
    assert validation.NAME_REQUIRED in result.errors


def test_none_name_is_required_not_wrong_type():
    result = validation.validate({"name": None}, now=NOW)
    assert result.errors == [validation.NAME_REQUIRED]


@pytest.mark.parametrize("name", [123, 4.5, True, ["x"], {"a": 1}])
def test_non_text_name_is_rejected_without_raising(name):
    result = validation.validate({"name": name}, now=NOW)
    assert result.errors == [validation.NAME_MUST_BE_TEXT]


def test_negative_quantity():
    result = validation.validate({"name": "x", "quantity": -1}, now=NOW)
    assert result.errors == [validation.NEGATIVE_QUANTITY]


def test_zero_quantity_is_allowed():
    result = validation.validate({"name": "x", "quantity": 0}, now=NOW)
    assert result.is_valid is True


def test_float_quantity_is_allowed():
    result = validation.validate({"name": "x", "quantity": 2.5}, now=NOW)
    assert result.is_valid is True


@pytest.mark.parametrize("quantity", ["5", None, [1], {"n": 1}, True, False])
def test_non_numeric_quantity_is_rejected_without_raising(quantity):
    result = validation.validate({"name": "x", "quantity": quantity}, now=NOW)
    assert result.errors == [validation.NON_NUMERIC_QUANTITY]


def test_missing_quantity_is_not_checked():
    result = validation.validate({"name": "x"}, now=NOW)
    assert result.is_valid is True


def test_due_date_in_past():
    result = validation.validate(
        {"name": "x", "due_date": "2024-01-01T00:00:00"}, now=NOW
    )
    assert result.errors == [validation.DUE_DATE_IN_PAST]


def test_due_date_in_future_is_allowed():
    result = validation.validate(
        {"name": "x", "due_date": "2024-12-01T00:00:00"}, now=NOW
    )
    assert result.is_valid is True


def test_due_date_equal_to_now_is_not_past():
    result = validation.validate(
        {"name": "x", "due_date": NOW.isoformat()}, now=NOW
    )
    assert result.is_valid is True


def test_invalid_due_date_format():
    result = validation.validate(
        {"name": "x", "due_date": "not-a-date"}, now=NOW
    )
    assert result.errors == [validation.INVALID_DATE_FORMAT]


def test_non_string_due_date_is_invalid_format_not_a_crash():
    result = validation.validate({"name": "x", "due_date": 20240101}, now=NOW)
    assert result.errors == [validation.INVALID_DATE_FORMAT]


def test_due_date_with_z_suffix_in_future_is_allowed():
    result = validation.validate(
        {"name": "x", "due_date": "2024-12-01T00:00:00Z"}, now=NOW
    )
    assert result.is_valid is True


def test_timezone_aware_due_date_in_past_is_rejected():
    # NOW is naive; a tz-aware past timestamp must not raise when compared.
    result = validation.validate(
        {"name": "x", "due_date": "2024-01-01T00:00:00+00:00"}, now=NOW
    )
    assert result.errors == [validation.DUE_DATE_IN_PAST]


def test_empty_due_date_string_is_skipped():
    result = validation.validate({"name": "x", "due_date": ""}, now=NOW)
    assert result.is_valid is True


def test_whitespace_only_due_date_is_treated_as_invalid():
    # The string is truthy, so it is parsed and found unusable rather than skipped.
    result = validation.validate({"name": "x", "due_date": "   "}, now=NOW)
    assert result.errors == [validation.INVALID_DATE_FORMAT]


def test_multiple_errors_accumulate_in_order():
    result = validation.validate(
        {"name": "", "quantity": -5, "due_date": "2000-01-01T00:00:00"},
        now=NOW,
    )
    assert result.errors == [
        validation.NAME_REQUIRED,
        validation.NEGATIVE_QUANTITY,
        validation.DUE_DATE_IN_PAST,
    ]


def test_returns_validation_result_type():
    result = validation.validate({"name": "x"}, now=NOW)
    assert isinstance(result, ValidationResult)
