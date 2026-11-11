from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz():
    return "ok"
