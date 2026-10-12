from fastapi import APIRouter, HTTPException, Query
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.utils import paginate

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets(
    offset: int = Query(0, ge=0, description="The number of items to skip"),
    limit: int = Query(100, gt=0, le=1000, description="The maximum number of items to return"),
):
    try:
        return paginate(widgets_db, offset=offset, limit=limit)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    for widget in widgets_db:
        if widget["id"] == widget_id:
            return widget
    raise HTTPException(status_code=404, detail="Widget not found")


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id
    from datetime import datetime

    db_widget = {
        **widget.model_dump(),
        "id": next_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    widgets_db.append(db_widget)
    next_id += 1
    return db_widget
