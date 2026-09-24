from datetime import datetime

import pytest

from src.services.items import batch
from src.services.items.errors import ItemDataError


class TestNormalizeIds:
    def test_none_is_empty(self):
        assert batch.normalize_ids(None) == []

    def test_list_preserved(self):
        assert batch.normalize_ids([1, 2, 3]) == [1, 2, 3]

    def test_deduplicates_preserving_order(self):
        assert batch.normalize_ids([1, 2, 1, 3, 2]) == [1, 2, 3]

    def test_tuple_and_set_supported(self):
        assert batch.normalize_ids((1, 2)) == [1, 2]
        assert sorted(batch.normalize_ids({1, 2, 3})) == [1, 2, 3]

    def test_mapping_uses_keys(self):
        assert batch.normalize_ids({1: "a", 2: "b"}) == [1, 2]

    @pytest.mark.parametrize("value", ["42", b"42"])
    def test_string_rejected(self, value):
        # Regression: a bare string id must not be split into characters.
        with pytest.raises(ItemDataError):
            batch.normalize_ids(value)

    def test_non_iterable_rejected(self):
        with pytest.raises(ItemDataError):
            batch.normalize_ids(42)


class TestEnforceBatchLimit:
    def test_within_limit_ok(self):
        batch.enforce_batch_limit(list(range(10)), limit=10)

    def test_over_limit_raises(self):
        with pytest.raises(ItemDataError):
            batch.enforce_batch_limit(list(range(11)), limit=10)


class TestPlanUpdate:
    def test_missing_record_fails(self):
        assert batch.plan_update(None, "done") == (batch.ACTION_FAILED, "not found")

    def test_already_in_state_skipped(self):
        assert batch.plan_update({"status": "done"}, "done") == (
            batch.ACTION_SKIPPED,
            "already in state",
        )

    def test_transition_planned(self):
        assert batch.plan_update({"status": "open"}, "done") == (
            batch.ACTION_UPDATE,
            None,
        )

    def test_record_without_status(self):
        assert batch.plan_update({}, "done") == (batch.ACTION_UPDATE, None)


class TestApplyUpdate:
    def test_returns_new_dict_without_mutating(self):
        original = {"id": 1, "status": "open"}
        now = datetime(2026, 9, 24, 12, 0, 0)
        updated = batch.apply_update(original, "done", "alice", now=now)

        assert updated["status"] == "done"
        assert updated["updated_by"] == "alice"
        assert updated["updated_at"] == now
        # Original untouched (no aliasing of the caller's stored record).
        assert original == {"id": 1, "status": "open"}
