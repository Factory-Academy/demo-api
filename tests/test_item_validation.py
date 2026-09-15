from datetime import datetime, timedelta

from src.services.items.validation import validate_item

NOW = datetime(2026, 1, 1, 12, 0, 0)


def _iso(days_from_now):
    return (NOW + timedelta(days=days_from_now)).isoformat()


class TestValidName:
    def test_valid_minimal_payload(self):
        ok, errors = validate_item({"name": "Widget"}, now=NOW)
        assert ok is True
        assert errors == []

    def test_missing_name(self):
        ok, errors = validate_item({}, now=NOW)
        assert ok is False
        assert "Name is required" in errors

    def test_blank_name(self):
        ok, errors = validate_item({"name": "   "}, now=NOW)
        assert ok is False
        assert "Name is required" in errors

    def test_empty_string_name(self):
        ok, errors = validate_item({"name": ""}, now=NOW)
        assert ok is False
        assert "Name is required" in errors


class TestQuantity:
    def test_zero_quantity_is_allowed(self):
        ok, errors = validate_item({"name": "x", "quantity": 0}, now=NOW)
        assert ok is True

    def test_positive_quantity_is_allowed(self):
        ok, errors = validate_item({"name": "x", "quantity": 5}, now=NOW)
        assert ok is True

    def test_negative_quantity_rejected(self):
        ok, errors = validate_item({"name": "x", "quantity": -1}, now=NOW)
        assert ok is False
        assert "Quantity cannot be negative" in errors

    def test_none_quantity_is_treated_as_unset(self):
        ok, errors = validate_item({"name": "x", "quantity": None}, now=NOW)
        assert ok is True
        assert errors == []

    def test_non_numeric_quantity_rejected(self):
        ok, errors = validate_item({"name": "x", "quantity": "lots"}, now=NOW)
        assert ok is False
        assert "Quantity must be a number" in errors

    def test_boolean_quantity_rejected(self):
        ok, errors = validate_item({"name": "x", "quantity": True}, now=NOW)
        assert ok is False
        assert "Quantity must be a number" in errors


class TestDueDate:
    def test_future_due_date_is_allowed(self):
        ok, errors = validate_item(
            {"name": "x", "due_date": _iso(5)}, now=NOW
        )
        assert ok is True

    def test_past_due_date_rejected(self):
        ok, errors = validate_item(
            {"name": "x", "due_date": _iso(-5)}, now=NOW
        )
        assert ok is False
        assert "Due date cannot be in the past" in errors

    def test_invalid_date_format_rejected(self):
        ok, errors = validate_item(
            {"name": "x", "due_date": "not-a-date"}, now=NOW
        )
        assert ok is False
        assert "Invalid date format" in errors

    def test_non_string_due_date_rejected(self):
        # A non-string value reaches ``fromisoformat`` and raises TypeError,
        # which must surface as the same "Invalid date format" error.
        ok, errors = validate_item(
            {"name": "x", "due_date": 20260101}, now=NOW
        )
        assert ok is False
        assert "Invalid date format" in errors

    def test_empty_due_date_is_ignored(self):
        ok, errors = validate_item({"name": "x", "due_date": ""}, now=NOW)
        assert ok is True

    def test_missing_due_date_is_ignored(self):
        ok, errors = validate_item({"name": "x"}, now=NOW)
        assert ok is True


class TestMultipleErrors:
    def test_all_errors_accumulate(self):
        ok, errors = validate_item(
            {"name": "  ", "quantity": -3, "due_date": _iso(-1)}, now=NOW
        )
        assert ok is False
        assert errors == [
            "Name is required",
            "Quantity cannot be negative",
            "Due date cannot be in the past",
        ]

    def test_now_defaults_to_utcnow(self):
        # A due date comfortably in the future must pass against the real clock.
        future = (datetime.utcnow() + timedelta(days=365)).isoformat()
        ok, errors = validate_item({"name": "x", "due_date": future})
        assert ok is True
