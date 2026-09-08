"""
Integration tests for rate limiting inside ItemService.batch_update_status.
"""
import pytest

from src.services.item_service import ItemService
from src.utils.rate_limiter import RateLimitExceeded, RateLimiter


class FakeClock:
    """Manually advanced clock so refill timing is deterministic."""

    def __init__(self, start: float = 0.0):
        self.now = float(start)

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


class InMemoryDB:
    """Minimal db stub matching the get/save interface ItemService expects."""

    def __init__(self, records=None):
        self.records = {r["id"]: r for r in (records or [])}
        self.saved = []

    def get(self, record_id):
        return self.records.get(record_id)

    def save(self, record):
        self.records[record["id"]] = record
        self.saved.append(record["id"])


def make_records(*ids, status="open"):
    return [{"id": i, "status": status} for i in ids]


def test_batch_update_without_limiter_is_unrestricted():
    """With no limiter the service should behave as before."""
    db = InMemoryDB(make_records(1, 2, 3))
    service = ItemService(db)
    result = service.batch_update_status([1, 2, 3], "done", "alice")
    assert result["updated"] == [1, 2, 3]


def test_batch_update_within_limit_succeeds():
    """A batch that fits inside the quota should update every record."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=5, refill_rate=0, time_func=clock)
    db = InMemoryDB(make_records(1, 2, 3))
    service = ItemService(db, rate_limiter=limiter)

    result = service.batch_update_status([1, 2, 3], "done", "alice")
    assert result["updated"] == [1, 2, 3]
    assert limiter.tokens_remaining("alice") == 2


def test_batch_update_charges_one_token_per_id():
    """Each requested id should consume a token, even missing/skipped ones."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=3, refill_rate=0, time_func=clock)
    # id 2 does not exist, id 3 is already in the target state.
    db = InMemoryDB(make_records(1, 3, status="open"))
    db.records[3]["status"] = "done"
    service = ItemService(db, rate_limiter=limiter)

    result = service.batch_update_status([1, 2, 3], "done", "alice")
    assert result["updated"] == [1]
    assert result["failed"][0]["id"] == 2
    assert result["skipped"][0]["id"] == 3
    # All three ids were charged regardless of outcome.
    assert limiter.tokens_remaining("alice") == 0


def test_batch_update_exceeding_limit_raises():
    """A batch larger than the remaining quota should be rejected wholesale."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_rate=0, time_func=clock)
    db = InMemoryDB(make_records(1, 2, 3))
    service = ItemService(db, rate_limiter=limiter)

    with pytest.raises(RateLimitExceeded) as exc_info:
        service.batch_update_status([1, 2, 3], "done", "alice")
    assert exc_info.value.key == "alice"
    # Nothing should have been written when the limit blocks the call.
    assert db.saved == []


def test_batch_update_is_per_user():
    """One user's quota should not affect another user."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_rate=0, time_func=clock)
    db = InMemoryDB(make_records(1, 2, 3, 4))
    service = ItemService(db, rate_limiter=limiter)

    service.batch_update_status([1, 2], "done", "alice")
    # Bob has his own full bucket.
    result = service.batch_update_status([3, 4], "done", "bob")
    assert result["updated"] == [3, 4]


def test_batch_update_quota_refills_over_time():
    """A refilling limiter should permit further batches after waiting."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_rate=1, time_func=clock)
    db = InMemoryDB(make_records(1, 2, 3))
    service = ItemService(db, rate_limiter=limiter)

    service.batch_update_status([1, 2], "done", "alice")
    with pytest.raises(RateLimitExceeded):
        service.batch_update_status([3], "done", "alice")

    clock.advance(1)  # one token refilled
    result = service.batch_update_status([3], "done", "alice")
    assert result["updated"] == [3]


def test_empty_batch_does_not_consume_quota():
    """An empty id list should not touch the limiter."""
    clock = FakeClock()
    limiter = RateLimiter(capacity=1, refill_rate=0, time_func=clock)
    db = InMemoryDB()
    service = ItemService(db, rate_limiter=limiter)

    result = service.batch_update_status([], "done", "alice")
    assert result == {"updated": [], "failed": [], "skipped": []}
    assert limiter.tokens_remaining("alice") == 1
