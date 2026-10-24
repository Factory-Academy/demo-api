from datetime import datetime
from src.services.item_service import ItemService


class MockDB:
    def get(self, id):
        return None

    def save(self, record):
        pass


def test_calculate_priority_critical():
    """Test calculate_priority example from docstring."""
    db = MockDB()
    service = ItemService(db)
    item = {
        "created_at": datetime.utcnow(),
        "urgency": 5,
        "is_critical": True,
    }
    priority = service.calculate_priority(item)
    assert priority == "critical"
