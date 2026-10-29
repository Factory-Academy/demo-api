from datetime import datetime, timedelta
from src.services.item_service import ItemService

def test_validate_item_with_past_date():
    service = ItemService(db={})
    past_date = (datetime.utcnow() - timedelta(days=1)).isoformat()
    data = {
        "name": "Test Item",
        "quantity": 1,
        "due_date": past_date
    }
    
    # Default behavior: past date should fail
    is_valid, errors = service.validate_item(data)
    assert is_valid is False
    assert "Due date cannot be in the past" in errors
    
    # Optional argument: allow_past_dates=True should pass
    is_valid, errors = service.validate_item(data, allow_past_dates=True)
    assert is_valid is True
    assert len(errors) == 0
