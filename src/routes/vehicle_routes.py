from fastapi import APIRouter, HTTPException
from typing import List
from src.models.vehicle import Vehicle, VehicleCreate, VehicleUpdate

router = APIRouter()

vehicles_db: List[dict] = []
next_id = 1


@router.get("/", response_model=List[Vehicle])
async def list_vehicles():
    return vehicles_db


@router.get("/{vehicle_id}", response_model=Vehicle)
async def get_vehicle(vehicle_id: int):
    for vehicle in vehicles_db:
        if vehicle["id"] == vehicle_id:
            return vehicle
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.post("/", response_model=Vehicle, status_code=201)
async def create_vehicle(vehicle: VehicleCreate):
    global next_id
    from datetime import datetime

    db_vehicle = {
        **vehicle.model_dump(),
        "id": next_id,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    }
    vehicles_db.append(db_vehicle)
    next_id += 1
    return db_vehicle


@router.put("/{vehicle_id}", response_model=Vehicle)
async def update_vehicle(vehicle_id: int, vehicle: VehicleUpdate):
    from datetime import datetime

    for i, existing in enumerate(vehicles_db):
        if existing["id"] == vehicle_id:
            update_data = vehicle.model_dump(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow()
            vehicles_db[i] = {**existing, **update_data}
            return vehicles_db[i]
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.delete("/{vehicle_id}")
async def delete_vehicle(vehicle_id: int):
    for i, vehicle in enumerate(vehicles_db):
        if vehicle["id"] == vehicle_id:
            vehicles_db.pop(i)
            return {"status": "deleted"}
    raise HTTPException(status_code=404, detail="Vehicle not found")
