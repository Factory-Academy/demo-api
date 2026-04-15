from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class VehicleBase(BaseModel):
    vin: str
    model_name: str
    model_year: int
    status: str = "active"
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(BaseModel):
    vin: Optional[str] = None
    model_name: Optional[str] = None
    model_year: Optional[int] = None
    status: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None


class Vehicle(VehicleBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
