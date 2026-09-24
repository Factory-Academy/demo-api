from src.services.items.dedup import dedupe_preserving_order


class TestDedupePreservingOrder:
    def test_empty(self):
        assert list(dedupe_preserving_order([])) == []

    def test_preserves_first_seen_order(self):
        assert list(dedupe_preserving_order([3, 1, 2])) == [3, 1, 2]

    def test_collapses_hashable_duplicates(self):
        assert list(dedupe_preserving_order([1, 2, 1, 3, 2, 1])) == [1, 2, 3]

    def test_consumes_generators_in_one_pass(self):
        assert list(dedupe_preserving_order(x % 3 for x in range(9))) == [0, 1, 2]

    def test_unhashable_elements_do_not_raise(self):
        # Regression: a plain set-based de-dup raised TypeError here.
        items = [[1], {"a": 1}, [1], {"a": 1}]
        assert list(dedupe_preserving_order(items)) == [[1], {"a": 1}]

    def test_mixed_hashable_and_unhashable(self):
        items = [1, [1], 1, [1], 2, {"k": "v"}]
        assert list(dedupe_preserving_order(items)) == [1, [1], 2, {"k": "v"}]

    def test_hashable_and_equal_unhashable_kept_separate(self):
        # Distinct types that never compare equal are all preserved.
        items = [1, (1,), [1]]
        assert list(dedupe_preserving_order(items)) == [1, (1,), [1]]
