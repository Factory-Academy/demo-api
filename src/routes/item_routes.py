from fastapi import APIRouter
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.shortcuts import find_or_404, find_index_or_404

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return find_or_404(items_db, item_id, "Item")


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

    i = find_index_or_404(items_db, item_id, "Item")
    existing = items_db[i]
    update_data = item.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.utcnow()
    items_db[i] = {**existing, **update_data}
    return items_db[i]


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    i = find_index_or_404(items_db, item_id, "Item")
    items_db.pop(i)
    return {"status": "deleted"}
