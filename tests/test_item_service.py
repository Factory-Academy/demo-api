from src.services.item_service import ItemService


def test_validate_item_requires_name():
    service = ItemService(db={})

    is_valid, errors = service.validate_item({"name": "   "})

    assert is_valid is False
    assert "Name is required" in errors
