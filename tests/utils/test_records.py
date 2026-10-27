from datetime import datetime
from src.utils.records import prepare_new_record, mark_updated, utcnow


def test_utcnow():
    now = utcnow()
    assert isinstance(now, datetime)
    # Check that it's close to current time
    assert (datetime.utcnow() - now).total_seconds() < 1


def test_prepare_new_record():
    data = {"name": "Test", "value": 123}
    next_id = 42
    record = prepare_new_record(data, next_id)
    
    assert record["id"] == 42
    assert record["name"] == "Test"
    assert record["value"] == 123
    assert isinstance(record["created_at"], datetime)
    assert isinstance(record["updated_at"], datetime)
    assert record["created_at"] == record["updated_at"]


def test_mark_updated():
    record = {"id": 1, "name": "Old", "updated_at": datetime(2000, 1, 1)}
    updated_record = mark_updated(record)
    
    assert updated_record["id"] == 1
    assert updated_record["name"] == "Old"
    assert updated_record["updated_at"] > datetime(2000, 1, 1)
    assert (datetime.utcnow() - updated_record["updated_at"]).total_seconds() < 1
