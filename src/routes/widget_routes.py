from fastapi import APIRouter
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.utils.db_helpers import create_with_timestamps, find_by_id

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    return find_by_id(widgets_db, widget_id, "Widget")


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id
    db_widget, next_id = create_with_timestamps(
        widgets_db, widget.model_dump(), next_id
    )
    return db_widget
