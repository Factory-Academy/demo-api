from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router
from src.utils.exceptions import AppError

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
