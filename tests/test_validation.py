from datetime import datetime, timedelta

import pytest

from src.services.items import validation

NOW = datetime(2026, 9, 24, 12, 0, 0)


class TestValidateName:
    def test_valid(self):
        assert validation.validate_name("Widget") is None

    @pytest.mark.parametrize("value", [None, "", "   "])
    def test_missing_or_blank(self, value):
        assert validation.validate_name(value) == "Name is required"

    def test_non_string(self):
        # Regression: the old code called ``.strip()`` and raised AttributeError.
        assert validation.validate_name(123) == "Name must be a string"

    def test_too_long(self):
        assert validation.validate_name("x" * 256).startswith("Name must be at most")


class TestValidateQuantity:
    def test_absent_is_valid(self):
        assert validation.validate_quantity(None) is None

    def test_zero_and_positive_valid(self):
        assert validation.validate_quantity(0) is None
        assert validation.validate_quantity(5) is None

    def test_negative_rejected(self):
        assert validation.validate_quantity(-1) == "Quantity cannot be negative"

    @pytest.mark.parametrize("value", ["abc", [], {}])
    def test_non_numeric_rejected(self, value):
        # Regression: previously raised TypeError comparing str/None with 0.
        assert validation.validate_quantity(value) == "Quantity must be a number"

    def test_numeric_string_accepted(self):
        assert validation.validate_quantity("3") is None


class TestValidateDueDate:
    def test_absent_is_valid(self):
        assert validation.validate_due_date(None, now=NOW) is None
        assert validation.validate_due_date("", now=NOW) is None

    def test_future_valid(self):
        future = (NOW + timedelta(days=1)).isoformat()
        assert validation.validate_due_date(future, now=NOW) is None

    def test_past_rejected(self):
        past = (NOW - timedelta(days=1)).isoformat()
        assert validation.validate_due_date(past, now=NOW) == "Due date cannot be in the past"

    def test_bad_format_rejected(self):
        assert validation.validate_due_date("not-a-date", now=NOW) == "Invalid date format"

    def test_non_string_rejected(self):
        # Regression: an int due_date raised an uncaught TypeError before.
        assert validation.validate_due_date(12345, now=NOW) == "Invalid date format"


class TestValidateItem:
    def test_valid_payload(self):
        ok, errors = validation.validate_item(
            {"name": "Widget", "quantity": 2}, now=NOW
        )
        assert ok is True
        assert errors == []

    def test_collects_multiple_errors(self):
        ok, errors = validation.validate_item(
            {"name": "", "quantity": -1, "due_date": "bad"}, now=NOW
        )
        assert ok is False
        assert set(errors) == {
            "Name is required",
            "Quantity cannot be negative",
            "Invalid date format",
        }

    @pytest.mark.parametrize("bad", [None, [], "payload", 5])
    def test_non_mapping_payload(self, bad):
        ok, errors = validation.validate_item(bad, now=NOW)
        assert ok is False
        assert errors == ["Invalid item payload"]
