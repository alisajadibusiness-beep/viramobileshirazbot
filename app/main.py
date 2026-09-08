from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.database.connection import close_db, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application startup and shutdown lifecycle.
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


# ============================================================
# HOME
# ============================================================

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "message": "VIRA MOBILE is running.",
    }


@app.head("/")
async def root_head():
    """
    HEAD support for monitoring services.
    """
    return Response(status_code=200)


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
async def health():
    """
    Health check endpoint for Render and UptimeRobot.
    """

    return JSONResponse(
        status_code=200,
        content={
            "status": "ok",
            "service": settings.app_name,
            "version": settings.app_version,
        },
    )


@app.head("/health")
async def health_head():
    """
    HEAD health check endpoint.

    UptimeRobot can use HEAD instead of GET.
    """

    return Response(
        status_code=200,
        headers={
            "X-Service": "VIRA MOBILE",
            "X-Health": "ok",
            "X-Version": settings.app_version,
        },
    )


# ============================================================
# API STATUS
# ============================================================

@app.get("/api")
async def api_status():
    return {
        "status": "online",
        "service": "VIRA MOBILE API",
        "version": settings.app_version,
    }


@app.head("/api")
async def api_head():
    """
    HEAD support for API endpoint.
    """

    return Response(status_code=200)


# ============================================================
# DETAILED STATUS
# ============================================================

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


@app.head("/api/status")
async def detailed_status_head():
    """
    HEAD support for detailed status endpoint.
    """

    return Response(status_code=200)
