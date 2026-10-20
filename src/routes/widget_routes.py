from fastapi import APIRouter, HTTPException
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.utils.db_helpers import find_by_id, create_record

router = APIRouter()

widgets_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    widget = find_by_id(widgets_db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    global next_id
    db_widget = create_record(widget.model_dump(), next_id)
    widgets_db.append(db_widget)
    next_id += 1
    return db_widget


@router.get("/{widget_id}/stats")
async def get_widget_stats(widget_id: int):
    from src.services.widget_service import WidgetService
    
    # Verify widget exists
    widget = find_by_id(widgets_db, widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    
    service = WidgetService()
    return service.get_complex_widget_stats(widget_id)
