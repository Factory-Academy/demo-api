from datetime import datetime, timedelta
from src.services.item_service import ItemService

def test_calculate_priority():
    service = ItemService(db=None)
    
    # Test low priority
    item_low = {
        "created_at": datetime.utcnow(),
        "urgency": 1,
        "is_critical": False
    }
    assert service.calculate_priority(item_low) == "low"
    
    # Test critical priority
    item_critical = {
        "created_at": datetime.utcnow() - timedelta(days=40),
        "urgency": 5,
        "is_critical": True
    }
    # base_score = 5 * 10 (urgency) + 50 (critical) + 40 * 0.5 (age) = 50 + 50 + 20 = 120
    assert service.calculate_priority(item_critical) == "critical"

def test_validate_item():
    service = ItemService(db=None)
    
    valid_data = {"name": "Test", "quantity": 10}
    is_valid, errors = service.validate_item(valid_data)
    assert is_valid is True
    assert len(errors) == 0
    
    invalid_data = {"name": "", "quantity": -1}
    is_valid, errors = service.validate_item(invalid_data)
    assert is_valid is False
    assert "Name is required" in errors
    assert "Quantity cannot be negative" in errors
