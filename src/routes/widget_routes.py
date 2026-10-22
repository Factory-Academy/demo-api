from datetime import datetime
from typing import List

from fastapi import APIRouter, HTTPException

from src.domain.models import WidgetRecord
from src.models.widget import Widget, WidgetCreate

router = APIRouter()

widgets_db: List[WidgetRecord] = []
next_id = 1


def _find(widget_id: int) -> int:
    for index, record in enumerate(widgets_db):
        if record.id == widget_id:
            return index
    raise HTTPException(status_code=404, detail="Widget not found")


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    return widgets_db[_find(widget_id)]


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id
    record = WidgetRecord.create(next_id, widget.model_dump(), now=datetime.utcnow())
    widgets_db.append(record)
    next_id += 1
    return record
