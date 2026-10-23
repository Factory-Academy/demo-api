from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.error_handling import ResourceNotFoundError
from src.events import AuditLog, get_event_bus
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])

# Record every domain event published during the app's lifetime.
audit_log = AuditLog()
audit_log.attach(get_event_bus())


@app.exception_handler(ResourceNotFoundError)
async def handle_resource_not_found(_: Request, exc: ResourceNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
