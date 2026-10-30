"""Tests for the shared value types: PriorityLevel and PriorityInput."""

from datetime import date, datetime

import pytest

from src.services.priority import PriorityInput, PriorityLevel, PriorityError


def test_level_is_string_comparable():
    assert PriorityLevel.HIGH == "high"
    assert PriorityLevel.HIGH.value == "high"


def test_level_rank_is_ordered():
    assert PriorityLevel.LOW.rank < PriorityLevel.MEDIUM.rank
    assert PriorityLevel.MEDIUM.rank < PriorityLevel.HIGH.rank
    assert PriorityLevel.HIGH.rank < PriorityLevel.CRITICAL.rank


def test_escalate_caps_at_critical():
    assert PriorityLevel.LOW.escalate() is PriorityLevel.MEDIUM
    assert PriorityLevel.HIGH.escalate() is PriorityLevel.CRITICAL
    assert PriorityLevel.CRITICAL.escalate() is PriorityLevel.CRITICAL
    assert PriorityLevel.LOW.escalate(2) is PriorityLevel.HIGH


def test_from_rank_clamps_out_of_range():
    assert PriorityLevel.from_rank(-5) is PriorityLevel.LOW
    assert PriorityLevel.from_rank(99) is PriorityLevel.CRITICAL


def test_from_item_fills_defaults_for_empty_dict():
    pi = PriorityInput.from_item({})
    assert pi.created_at is None
    assert pi.urgency == 0
    assert pi.is_critical is False
    assert pi.due_date is None


def test_from_item_parses_iso_datetime_strings():
    pi = PriorityInput.from_item(
        {"created_at": "2026-01-01T00:00:00", "due_date": "2026-02-01T12:30:00"}
    )
    assert pi.created_at == datetime(2026, 1, 1, 0, 0, 0)
    assert pi.due_date == datetime(2026, 2, 1, 12, 30, 0)


def test_from_item_accepts_date_objects():
    pi = PriorityInput.from_item({"created_at": date(2026, 3, 4)})
    assert pi.created_at == datetime(2026, 3, 4, 0, 0, 0)


def test_from_item_coerces_missing_urgency_to_zero():
    assert PriorityInput.from_item({"urgency": None}).urgency == 0


def test_from_item_rejects_unparseable_date():
    with pytest.raises(PriorityError):
        PriorityInput.from_item({"due_date": "not-a-date"})


def test_from_item_rejects_wrong_typed_date():
    with pytest.raises(PriorityError):
        PriorityInput.from_item({"created_at": [1, 2, 3]})


def test_from_item_rejects_non_integer_urgency():
    with pytest.raises(PriorityError):
        PriorityInput.from_item({"urgency": "lots"})
