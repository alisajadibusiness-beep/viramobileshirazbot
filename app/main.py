from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.config import settings
from app.database.connection import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup/shutdown lifecycle.
    """

    print("=" * 60)
    print(f"{settings.app_name} starting...")
    print(f"Version: {settings.app_version}")
    print(f"Environment: {settings.environment}")
    print("=" * 60)

    try:
        await init_db()
        print("Database initialized successfully.")
    except Exception as exc:
        print(f"Database initialization warning: {exc}")

    yield

    print(f"{settings.app_name} shutting down...")

    try:
        await close_db()
    except Exception as exc:
        print(f"Database shutdown warning: {exc}")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "VIRA MOBILE - Professional mobile store platform "
        "with product catalog, inventory, orders, CRM and Telegram integration."
    ),
    lifespan=lifespan,
)


@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "message": "VIRA MOBILE is running.",
    }


@app.get("/health")
async def health():
    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": settings.app_name,
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


@app.get("/api/status")
async def detailed_status():
    return {
        "application": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "configured",
        "telegram": (
            "configured"
            if settings.bot_token
            else "not_configured"
        ),
    }
