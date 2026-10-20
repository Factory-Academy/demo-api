from fastapi import FastAPI
from src.events import get_audit_log, get_event_bus
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.on_event("startup")
async def _subscribe_audit_log() -> None:
    """Attach the audit log to the default event bus when the app starts."""
    get_audit_log().attach(get_event_bus())


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
