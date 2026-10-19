from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from src.domain import ItemRecord
from src.models.item import Item, ItemCreate, ItemUpdate

router = APIRouter()

items_db: List[ItemRecord] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.id == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id

    now = datetime.utcnow()
    db_item = ItemRecord(
        id=next_id,
        created_at=now,
        updated_at=now,
        **item.model_dump(),
    )
    items_db.append(db_item)
    next_id += 1
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    for i, existing in enumerate(items_db):
        if existing.id == item_id:
            update_data = item.model_dump(exclude_unset=True)
            items_db[i] = existing.with_changes(**update_data)
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.id == item_id:
            items_db.pop(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Item not found")
