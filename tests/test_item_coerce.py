from src.services.items.coerce import as_number, is_number


class TestIsNumber:
    def test_ints_are_numbers(self):
        assert is_number(0) is True
        assert is_number(-3) is True

    def test_floats_are_numbers(self):
        assert is_number(2.5) is True

    def test_none_is_not_a_number(self):
        assert is_number(None) is False

    def test_strings_are_not_numbers(self):
        assert is_number("5") is False

    def test_bools_are_not_numbers(self):
        # bool subclasses int, but a boolean in a numeric field is a bug.
        assert is_number(True) is False
        assert is_number(False) is False


class TestAsNumber:
    def test_passes_numbers_through(self):
        assert as_number(7) == 7
        assert as_number(-1.5) == -1.5

    def test_falls_back_on_none(self):
        assert as_number(None) == 0.0

    def test_falls_back_on_non_numeric(self):
        assert as_number("nope") == 0.0

    def test_falls_back_on_bool(self):
        assert as_number(True) == 0.0

    def test_honours_custom_default(self):
        assert as_number(None, default=10) == 10
        assert as_number("x", default=-1) == -1
