from fastapi import FastAPI, Query
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router
from src.utils.feature_flags import feature_flags

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.get("/health")
async def health_check(include_flags: bool = Query(False)):
    payload = {"status": "healthy"}
    if include_flags:
        payload["feature_flags"] = {
            "widgets_v2_api": feature_flags.is_enabled("widgets_v2_api")
        }
    return payload
