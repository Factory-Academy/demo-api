from src.services.item_service import ItemService
from src.utils.rate_limiter import RateLimiter


class FakeClock:
    def __init__(self, start: float = 0.0) -> None:
        self._now = float(start)

    def __call__(self) -> float:
        return self._now

    def advance(self, seconds: float) -> None:
        self._now += seconds


class InMemoryDB:
    def __init__(self, records):
        self._records = {r["id"]: r for r in records}
        self.saved = []

    def get(self, id):
        return self._records.get(id)

    def save(self, record):
        self._records[record["id"]] = record
        self.saved.append(record["id"])


def _records(n, status="open"):
    return [{"id": i, "status": status} for i in range(1, n + 1)]


def test_batch_update_without_limiter_updates_all():
    db = InMemoryDB(_records(3))
    service = ItemService(db)
    result = service.batch_update_status([1, 2, 3], "closed", "alice")
    assert result["updated"] == [1, 2, 3]
    assert result["rate_limited"] == []


def test_batch_update_stops_user_at_token_limit():
    db = InMemoryDB(_records(5))
    limiter = RateLimiter(capacity=3, refill_rate=0)
    service = ItemService(db, rate_limiter=limiter)

    result = service.batch_update_status([1, 2, 3, 4, 5], "closed", "alice")

    assert result["updated"] == [1, 2, 3]
    assert [entry["id"] for entry in result["rate_limited"]] == [4, 5]
    assert db.saved == [1, 2, 3]


def test_rate_limit_is_per_user():
    db = InMemoryDB(_records(4))
    limiter = RateLimiter(capacity=2, refill_rate=0)
    service = ItemService(db, rate_limiter=limiter)

    alice = service.batch_update_status([1, 2, 3], "closed", "alice")
    bob = service.batch_update_status([4], "closed", "bob")

    assert alice["updated"] == [1, 2]
    assert [e["id"] for e in alice["rate_limited"]] == [3]
    assert bob["updated"] == [4]  # bob has his own allowance


def test_skips_and_missing_records_do_not_consume_tokens():
    # id 1 already closed (skipped), id 99 missing (failed); neither should burn
    # a token, leaving the full allowance for the real updates.
    db = InMemoryDB([{"id": 1, "status": "closed"}, {"id": 2, "status": "open"},
                     {"id": 3, "status": "open"}])
    limiter = RateLimiter(capacity=2, refill_rate=0)
    service = ItemService(db, rate_limiter=limiter)

    result = service.batch_update_status([1, 99, 2, 3], "closed", "alice")

    assert [e["id"] for e in result["skipped"]] == [1]
    assert [e["id"] for e in result["failed"]] == [99]
    assert result["updated"] == [2, 3]
    assert result["rate_limited"] == []


def test_allowance_recovers_after_refill():
    db = InMemoryDB(_records(4))
    clock = FakeClock()
    limiter = RateLimiter(capacity=2, refill_rate=1, time_func=clock)
    service = ItemService(db, rate_limiter=limiter)

    first = service.batch_update_status([1, 2, 3], "closed", "alice")
    assert first["updated"] == [1, 2]
    assert [e["id"] for e in first["rate_limited"]] == [3]

    clock.advance(2)  # two tokens restored
    second = service.batch_update_status([3, 4], "closed", "alice")
    assert second["updated"] == [3, 4]
    assert second["rate_limited"] == []
