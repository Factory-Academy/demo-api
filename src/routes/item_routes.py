from fastapi import APIRouter, HTTPException
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.db_helpers import find_by_id, create_record

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = find_by_id(items_db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id
    db_item = create_record(item.model_dump(), next_id)
    items_db.append(db_item)
    next_id += 1
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    from datetime import datetime

    for i, existing in enumerate(items_db):
        if existing["id"] == item_id:
            update_data = item.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            items_db[i] = {**existing, **update_data}
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    item = find_by_id(items_db, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    items_db.remove(item)
    return {"status": "deleted"}
