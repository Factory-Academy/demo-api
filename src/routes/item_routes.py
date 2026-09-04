from fastapi import APIRouter
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.db_helpers import (
    create_with_timestamps,
    delete_by_id,
    find_by_id,
    update_by_id,
)

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return find_by_id(items_db, item_id, "Item")


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id
    db_item, next_id = create_with_timestamps(items_db, item.model_dump(), next_id)
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    update_data = item.model_dump(exclude_unset=True)
    return update_by_id(items_db, item_id, update_data, "Item")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    delete_by_id(items_db, item_id, "Item")
    return {"status": "deleted"}
