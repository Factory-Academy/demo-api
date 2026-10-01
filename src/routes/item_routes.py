from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from src.models.item import Item, ItemCreate, ItemUpdate
from src.utils.filters import (
    filter_items_by_criteria,
    apply_transformations,
    build_query_filter,
)

router = APIRouter()

items_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Item])
async def list_items(
    status: Optional[str] = Query(None, description="Filter by status"),
    exclude_fields: Optional[List[str]] = Query(None, description="Fields to exclude"),
):
    """List all items with optional filtering."""
    if status is None and exclude_fields is None:
        return items_db

    # Build filter criteria
    criteria = {}
    if status:
        criteria["status"] = status

    # Apply filters
    filtered = filter_items_by_criteria(
        items_db, criteria=criteria, exclude_fields=exclude_fields
    )
    return filtered


@router.get("/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item["id"] == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")


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

    for i, existing in enumerate(items_db):
        if existing["id"] == item_id:
            update_data = item.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            items_db[i] = {**existing, **update_data}
            return items_db[i]
    raise HTTPException(status_code=404, detail="Item not found")


@router.delete("/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item["id"] == item_id:
            items_db.pop(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Item not found")


@router.post("/batch-transform", response_model=List[Item])
async def batch_transform_items(
    item_ids: List[int],
    set_defaults: Optional[dict] = None,
):
    """Apply transformations and defaults to a batch of items.

    This endpoint demonstrates the proper use of mutable default handling
    in the filter utilities.
    """
    from datetime import datetime

    transformed = []
    for item_id in item_ids:
        # Find the item
        item = None
        for db_item in items_db:
            if db_item["id"] == item_id:
                item = db_item
                break

        if item is None:
            raise HTTPException(
                status_code=404, detail=f"Item {item_id} not found"
            )

        # Apply transformations with proper default handling
        transformations = {
            "name": lambda x: x.strip().upper() if isinstance(x, str) else x,
        }

        # Use the utility function with proper mutable default handling
        transformed_item = apply_transformations(
            item, transformations=transformations, defaults=set_defaults
        )

        # Update timestamp
        transformed_item["updated_at"] = datetime.utcnow()

        # Update in database
        for i, db_item in enumerate(items_db):
            if db_item["id"] == item_id:
                items_db[i] = transformed_item
                break

        transformed.append(transformed_item)

    return transformed
