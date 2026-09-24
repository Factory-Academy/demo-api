from fastapi import APIRouter
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.utils.helpers import find_entity_or_404

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    return find_entity_or_404(widgets_db, "id", widget_id, "Widget")


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
