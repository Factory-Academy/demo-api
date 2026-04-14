from fastapi import APIRouter, HTTPException
from typing import List
from src.models.widget import Widget, WidgetCreate

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


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
