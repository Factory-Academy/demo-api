from fastapi import APIRouter, HTTPException
from typing import List
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.crud_helpers import InMemoryStore

router = APIRouter()

items_db: List[dict] = []
store = InMemoryStore(items_db)


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    item = store.get_by_id(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    db_item = store.create(item.model_dump())
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    update_data = item.model_dump(exclude_unset=True)
    updated = store.update_by_id(item_id, update_data)
    if updated is None:
        raise HTTPException(status_code=404, detail="Item not found")
    return updated


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    deleted = store.delete_by_id(item_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Item not found")
    return {"status": "deleted"}
