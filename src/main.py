from fastapi import FastAPI
from src.routes.vehicle_routes import router as vehicle_router
from src.routes.service_appointment_routes import router as appointment_router

app = FastAPI(
    title="Rivian API",
    description="Fleet and vehicle management platform for Rivian's connected vehicle ecosystem",
    version="0.1.0",
)

app.include_router(vehicle_router, prefix="/vehicles", tags=["vehicles"])
app.include_router(appointment_router, prefix="/service-appointments", tags=["service-appointments"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
