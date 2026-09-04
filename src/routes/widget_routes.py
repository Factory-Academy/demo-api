from fastapi import APIRouter, HTTPException
from typing import List
from src.models.widget import Widget, WidgetCreate
from src.utils.crud_helpers import InMemoryStore

router = APIRouter()

widgets_db: List[dict] = []
store = InMemoryStore(widgets_db)


@router.get("/", response_model=List[Widget])
async def list_widgets():
    return widgets_db


@router.get("/{widget_id}", response_model=Widget)
async def get_widget(widget_id: int):
    widget = store.get_by_id(widget_id)
    if widget is None:
        raise HTTPException(status_code=404, detail="Widget not found")
    return widget


@router.post("/", response_model=Widget, status_code=201)
async def create_widget(widget: WidgetCreate):
    db_widget = store.create(widget.model_dump())
    return db_widget
