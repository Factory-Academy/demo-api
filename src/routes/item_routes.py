from fastapi import APIRouter
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.helpers import find_entity_or_404

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return find_entity_or_404(items_db, "id", item_id, "Item")


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id
    from datetime import datetime

    db_item = {
        **item.model_dump(),
        "id": next_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    items_db.append(db_item)
    next_id += 1
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    from datetime import datetime

    existing = find_entity_or_404(items_db, "id", item_id, "Item")
    update_data = item.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    existing.update(update_data)
    return existing


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    existing = find_entity_or_404(items_db, "id", item_id, "Item")
    items_db.remove(existing)
    return {"status": "deleted"}
