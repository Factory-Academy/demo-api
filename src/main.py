from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router
from src.utils.exceptions import ResourceNotFoundError, ValidationError

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

@app.exception_handler(ResourceNotFoundError)
async def resource_not_found_handler(request: Request, exc: ResourceNotFoundError):
    return JSONResponse(
        status_code=404,
        content={"detail": str(exc)},
    )

@app.exception_handler(ValidationError)
async def validation_error_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc), "errors": exc.errors},
    )

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
