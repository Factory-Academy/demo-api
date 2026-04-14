from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class WidgetBase(BaseModel):
    name: str
    item_id: int
    priority: int = 0
    notes: Optional[str] = None


class WidgetCreate(WidgetBase):
    pass


class Widget(WidgetBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
