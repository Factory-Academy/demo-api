from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from src.domain import WidgetRecord
from src.models.widget import Widget, WidgetCreate

router = APIRouter()

widgets_db: List[WidgetRecord] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    for widget in widgets_db:
        if widget.id == widget_id:
            return widget
    raise HTTPException(status_code=404, detail="Widget not found")


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id

    now = datetime.utcnow()
    db_widget = WidgetRecord(
        id=next_id,
        created_at=now,
        updated_at=now,
        **widget.model_dump(),
    )
    widgets_db.append(db_widget)
    next_id += 1
    return db_widget


@router.get("/{widget_id}/stats")
async def get_widget_stats(widget_id: int):
    from src.services.widget_service import WidgetService
    service = WidgetService()

    # Verify widget exists
    found = any(widget.id == widget_id for widget in widgets_db)

    if not found:
        raise HTTPException(status_code=404, detail="Widget not found")

    return service.get_complex_widget_stats(widget_id)
