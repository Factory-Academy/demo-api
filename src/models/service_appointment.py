from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ServiceAppointmentBase(BaseModel):
    service_type: str
    vehicle_id: int
    priority: int = 0
    notes: Optional[str] = None
    scheduled_date: Optional[str] = None


class ServiceAppointmentCreate(ServiceAppointmentBase):
    pass


class ServiceAppointment(ServiceAppointmentBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
