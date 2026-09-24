from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.routes.item_routes import router as item_router
from src.routes.widget_routes import router as widget_router
from src.utils.exceptions import APIException

app = FastAPI(
    title="{{COMPANY_NAME}} API",
    description="{{PROJECT_DESCRIPTION}}",
    version="0.1.0",
)

@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

app.include_router(item_router, prefix="/items", tags=["items"])
app.include_router(widget_router, prefix="/widgets", tags=["widgets"])


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
