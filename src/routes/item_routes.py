from datetime import datetime
from fastapi import APIRouter, HTTPException
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.routes.record_helpers import (
    build_timestamped_record,
    find_record_by_id,
    find_record_index_by_id,
)

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = find_record_by_id(items_db, item_id)
    if item:
        return item
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id
    db_item = build_timestamped_record(item.model_dump(), next_id)
    items_db.append(db_item)
    next_id += 1
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    record_index = find_record_index_by_id(items_db, item_id)
    if record_index is not None:
        existing = items_db[record_index]
        update_data = item.model_dump(exclude_unset=True)
        update_data["updated_at"] = datetime.utcnow()
        items_db[record_index] = {**existing, **update_data}
        return items_db[record_index]
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Item not found")
