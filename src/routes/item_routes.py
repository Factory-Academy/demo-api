from fastapi import APIRouter, HTTPException
from typing import List
from src.error_handling import get_resource_by_id
from src.events import ItemCreated, ItemDeleted, ItemUpdated, get_event_bus
from src.models.item import Item, ItemCreate, ItemUpdate

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items():
    return items_db


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    return get_resource_by_id(items_db, resource="Item", resource_id=item_id)


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
    get_event_bus().publish(
        ItemCreated(
            item_id=db_item["id"],
            name=db_item["name"],
            status=db_item["status"],
        )
    )
    return db_item


@router.put("/{item_id}", response_model=Item)
async def update_item(item_id: int, item: ItemUpdate):
    from datetime import datetime

    for i, existing in enumerate(items_db):
        if existing["id"] == item_id:
            update_data = item.model_dump(exclude_unset=True)
            changed_fields = tuple(update_data.keys())
            update_data["updated_at"] = datetime.utcnow()
            items_db[i] = {**existing, **update_data}
            get_event_bus().publish(
                ItemUpdated(
                    item_id=item_id,
                    changed_fields=changed_fields,
                    status=items_db[i].get("status"),
                )
            )
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            get_event_bus().publish(ItemDeleted(item_id=item_id))
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Item not found")
