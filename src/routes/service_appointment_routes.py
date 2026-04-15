from fastapi import APIRouter, HTTPException
from typing import List
from src.models.service_appointment import ServiceAppointment, ServiceAppointmentCreate

router = APIRouter()

appointments_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[ServiceAppointment])
async def list_appointments():
    return appointments_db


@router.get("/{appointment_id}", response_model=ServiceAppointment)
async def get_appointment(appointment_id: int):
    for appointment in appointments_db:
        if appointment["id"] == appointment_id:
            return appointment
    raise HTTPException(status_code=404, detail="Service appointment not found")


@router.post("/", response_model=ServiceAppointment, status_code=201)
async def create_appointment(appointment: ServiceAppointmentCreate):
    global next_id
    from datetime import datetime

    db_appointment = {
        **appointment.model_dump(),
        "id": next_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    appointments_db.append(db_appointment)
    next_id += 1
    return db_appointment
