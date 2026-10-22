from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from src.domain.models import ItemRecord
from src.models.item import Item, ItemCreate, ItemUpdate

router = APIRouter()

items_db: List[ItemRecord] = []
next_id = 1


def _find(item_id: int) -> int:
    for index, record in enumerate(items_db):
        if record.id == item_id:
            return index
    raise HTTPException(status_code=404, detail="Item not found")


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return items_db[_find(item_id)]


@router.post("/", response_model=Item, status_code=201)
async def create_item(item: ItemCreate):
    global next_id
    record = ItemRecord.create(next_id, item.model_dump(), now=datetime.utcnow())
    items_db.append(record)
    next_id += 1
    return record


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    index = _find(item_id)
    changes = item.model_dump(exclude_unset=True)
    items_db[index].apply_update(changes, now=datetime.utcnow())
    return items_db[index]


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    items_db.pop(_find(item_id))
    return {"status": "deleted"}
