from datetime import datetime

import pytest

from src.domain.coercion import (
    coerce_bool,
    coerce_datetime,
    coerce_int,
    ensure_known_fields,
    require,
)
from src.domain import ItemRecord


class TestRequire:
    def test_returns_present_value(self):
        assert require({"id": 7}, "id") == 7

    def test_missing_raises_value_error(self):
        with pytest.raises(ValueError, match="Missing required field 'id'"):
            require({}, "id")


class TestCoerceInt:
    @pytest.mark.parametrize("value, expected", [(5, 5), ("5", 5), (5.0, 5), ("-3", -3)])
    def test_parses_numeric_values(self, value, expected):
        assert coerce_int(value, field="n") == expected

    def test_rejects_bool(self):
        # bool is an int subclass; accepting it would turn True into 1 silently.
        with pytest.raises(ValueError, match="not a bool"):
            coerce_int(True, field="n")

    @pytest.mark.parametrize("value", ["abc", None, "1.5", object()])
    def test_rejects_unparseable(self, value):
        with pytest.raises(ValueError, match="Invalid integer for 'n'"):
            coerce_int(value, field="n")


class TestCoerceBool:
    @pytest.mark.parametrize(
        "value, expected",
        [
            (True, True),
            (False, False),
            (1, True),
            (0, False),
            (None, False),
            ("true", True),
            ("TRUE", True),
            ("  yes ", True),
            ("1", True),
            ("on", True),
            ("false", False),
            ("FALSE", False),
            ("no", False),
            ("0", False),
            ("", False),
        ],
    )
    def test_known_spellings(self, value, expected):
        assert coerce_bool(value, field="flag") is expected

    @pytest.mark.parametrize("value", ["maybe", "truthy", "2x"])
    def test_rejects_unknown_strings(self, value):
        with pytest.raises(ValueError, match="Invalid boolean for 'flag'"):
            coerce_bool(value, field="flag")


class TestCoerceDatetime:
    def test_none_returns_default(self):
        default = datetime(2024, 1, 1)
        assert coerce_datetime(None, field="d", default=default) is default

    def test_blank_string_returns_default(self):
        default = datetime(2024, 1, 1)
        assert coerce_datetime("   ", field="d", default=default) is default

    def test_passes_through_datetime(self):
        value = datetime(2024, 5, 1)
        assert coerce_datetime(value, field="d", default=None) is value

    def test_parses_iso_string(self):
        assert coerce_datetime("2024-02-01T00:00:00", field="d", default=None) == datetime(
            2024, 2, 1
        )

    def test_rejects_bad_string(self):
        with pytest.raises(ValueError, match="Invalid date format for 'd'"):
            coerce_datetime("not-a-date", field="d", default=None)

    def test_rejects_wrong_type(self):
        with pytest.raises(ValueError, match="Invalid date value for 'd'"):
            coerce_datetime(123, field="d", default=None)


class TestEnsureKnownFields:
    def _record(self) -> ItemRecord:
        now = datetime(2024, 1, 1)
        return ItemRecord(id=1, name="x", created_at=now, updated_at=now)

    def test_accepts_known_fields(self):
        ensure_known_fields(self._record(), {"status": "closed"})  # no raise

    def test_rejects_unknown_field(self):
        with pytest.raises(ValueError, match="Unknown field for ItemRecord"):
            ensure_known_fields(self._record(), {"nope": 1})
