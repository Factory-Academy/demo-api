from fastapi import APIRouter, HTTPException
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.routes.record_helpers import build_timestamped_record, find_record_by_id

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    widget = find_record_by_id(widgets_db, widget_id)
    if widget:
        return widget
    raise HTTPException(status_code=404, detail="Widget not found")


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id
    db_widget = build_timestamped_record(widget.model_dump(), next_id)
    widgets_db.append(db_widget)
    next_id += 1
    return db_widget
