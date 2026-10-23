from datetime import datetime, timedelta

from src.services.items import validation


NOW = datetime(2026, 6, 1, 12, 0, 0)


class TestValidateName:
    def test_valid(self):
        assert validation.validate_name({"name": "Widget"}) is None

    def test_missing(self):
        assert validation.validate_name({}) == "Name is required"

    def test_blank(self):
        assert validation.validate_name({"name": "   "}) == "Name is required"

    def test_non_string_does_not_raise(self):
        assert validation.validate_name({"name": 42}) == "Name must be a string"


class TestValidateQuantity:
    def test_absent_is_ok(self):
        assert validation.validate_quantity({}) is None

    def test_valid(self):
        assert validation.validate_quantity({"quantity": 3}) is None

    def test_negative(self):
        assert validation.validate_quantity({"quantity": -1}) == (
            "Quantity cannot be negative"
        )

    def test_non_numeric_does_not_raise(self):
        assert validation.validate_quantity({"quantity": "lots"}) == (
            "Quantity must be a number"
        )

    def test_bool_rejected(self):
        assert validation.validate_quantity({"quantity": True}) == (
            "Quantity must be a number"
        )


class TestValidateDueDate:
    def test_absent_is_ok(self):
        assert validation.validate_due_date({}, now=NOW) is None

    def test_empty_string_is_ok(self):
        assert validation.validate_due_date({"due_date": ""}, now=NOW) is None

    def test_future_ok(self):
        future = (NOW + timedelta(days=5)).isoformat()
        assert validation.validate_due_date({"due_date": future}, now=NOW) is None

    def test_past_rejected(self):
        past = (NOW - timedelta(days=5)).isoformat()
        assert validation.validate_due_date({"due_date": past}, now=NOW) == (
            "Due date cannot be in the past"
        )

    def test_malformed_rejected(self):
        assert validation.validate_due_date(
            {"due_date": "31/12/2026"}, now=NOW
        ) == "Invalid date format"

    def test_datetime_object_accepted(self):
        future = NOW + timedelta(days=1)
        assert validation.validate_due_date({"due_date": future}, now=NOW) is None

    def test_non_string_non_datetime_rejected(self):
        assert validation.validate_due_date({"due_date": 12345}, now=NOW) == (
            "Invalid date format"
        )


class TestValidateItem:
    def test_valid_payload(self):
        ok, errors = validation.validate_item(
            {"name": "Widget", "quantity": 2}, now=NOW
        )
        assert ok is True
        assert errors == []

    def test_collects_multiple_errors(self):
        ok, errors = validation.validate_item(
            {"name": "", "quantity": -1}, now=NOW
        )
        assert ok is False
        assert "Name is required" in errors
        assert "Quantity cannot be negative" in errors

    def test_non_mapping_payload(self):
        ok, errors = validation.validate_item(None, now=NOW)
        assert ok is False
        assert errors == ["Invalid payload"]
