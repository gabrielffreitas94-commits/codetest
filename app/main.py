from fastapi import FastAPI
from mangum import Mangum
from app.api.v1.router import api_router
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.include_router(api_router, prefix=settings.API_V1_STR)

# AWS Lambda Handler via Mangum ASGI adapter
handler = Mangum(app)
