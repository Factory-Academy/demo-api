"""Tests that ItemService pushes status changes through the notifier."""

from src.services.item_service import ItemService


class FakeDB:
    def __init__(self, records):
        self._records = {r["id"]: r for r in records}
        self.saved = []

    def get(self, id):
        return self._records.get(id)

    def save(self, record):
        self._records[record["id"]] = record
        self.saved.append(record["id"])


class RecordingNotifier:
    """Captures notifications and returns a scripted delivery result."""

    def __init__(self, delivered=True):
        self._delivered = delivered
        self.calls = []

    def notify_status_change(self, *, item_id, old_status, new_status, updated_by):
        self.calls.append(
            {
                "item_id": item_id,
                "old_status": old_status,
                "new_status": new_status,
                "updated_by": updated_by,
            }
        )
        return self._delivered


def test_batch_update_without_notifier_still_works():
    db = FakeDB([{"id": 1, "status": "open"}])
    service = ItemService(db)
    result = service.batch_update_status([1], "closed", "alice")
    assert result["updated"] == [1]
    assert result["notified"] == []


def test_batch_update_notifies_on_each_change():
    db = FakeDB([{"id": 1, "status": "open"}, {"id": 2, "status": "pending"}])
    notifier = RecordingNotifier(delivered=True)
    service = ItemService(db, notifier=notifier)

    result = service.batch_update_status([1, 2], "closed", "alice")

    assert result["updated"] == [1, 2]
    assert result["notified"] == [1, 2]
    assert len(notifier.calls) == 2
    assert notifier.calls[0] == {
        "item_id": 1,
        "old_status": "open",
        "new_status": "closed",
        "updated_by": "alice",
    }


def test_skipped_and_missing_records_are_not_notified():
    db = FakeDB([{"id": 1, "status": "closed"}])  # already in target state
    notifier = RecordingNotifier(delivered=True)
    service = ItemService(db, notifier=notifier)

    result = service.batch_update_status([1, 999], "closed", "bob")

    assert result["updated"] == []
    assert result["skipped"] == [{"id": 1, "reason": "already in state"}]
    assert result["failed"] == [{"id": 999, "reason": "not found"}]
    assert notifier.calls == []  # nothing changed, nothing notified


def test_failed_delivery_updates_record_but_not_notified_list():
    db = FakeDB([{"id": 1, "status": "open"}])
    notifier = RecordingNotifier(delivered=False)  # notifier dropped the message
    service = ItemService(db, notifier=notifier)

    result = service.batch_update_status([1], "closed", "alice")

    # The local update still succeeds; only the notification bookkeeping differs.
    assert result["updated"] == [1]
    assert result["notified"] == []
    assert len(notifier.calls) == 1
