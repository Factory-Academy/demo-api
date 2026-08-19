from datetime import datetime, timedelta

from src.services.item_service import ItemService


def test_calculate_priority_age_bonus_threshold_boundary():
    service = ItemService(db=None)

    threshold_item = {
        "created_at": datetime.utcnow() - timedelta(days=30),
        "urgency": 1,
        "is_critical": False,
    }
    older_item = {
        "created_at": datetime.utcnow() - timedelta(days=31),
        "urgency": 1,
        "is_critical": False,
    }

    assert service.calculate_priority(threshold_item) == "low"
    assert service.calculate_priority(older_item) == "medium"
