from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"{settings.app_name} starting...")
    print(f"Environment: {settings.environment}")

    yield

    print(f"{settings.app_name} shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="VIRA MOBILE - Professional Mobile Store Platform",
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "VIRA MOBILE",
        "version": settings.app_version,
        "environment": settings.environment,
    }


@app.get("/health")
async def health():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": "VIRA MOBILE",
            "version": settings.app_version,
        },
    )


@app.get("/api")
async def api_status():
    return {
        "status": "online",
        "service": "VIRA MOBILE API",
        "version": settings.app_version,
    }
