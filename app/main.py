import asyncio
import contextlib
import logging
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from aiogram import Bot, Dispatcher
from app.config import settings
from app.database.connection import init_db, close_db
from app.bot.handlers import router as bot_router
from app.bot.admin_handlers import router as admin_router
from app.api.products import router as products_router
# ============================================================
# LOGGING
# ============================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger("vira_mobile")
# ============================================================
# FASTAPI APPLICATION
# ============================================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="VIRA MOBILE API & Telegram Bot",
)
# ============================================================
# GLOBAL BOT OBJECTS
# ============================================================
bot: Bot | None = None
dp: Dispatcher | None = None
polling_task: asyncio.Task | None = None
# ============================================================
# START TELEGRAM BOT
# ============================================================
async def start_telegram_bot() -> None:
    global bot, dp
    if not settings.bot_token:
        logger.warning(
            "BOT_TOKEN is not configured. Telegram bot will not start."
        )
        return
    try:
        bot = Bot(token=settings.bot_token)
        dp = Dispatcher()
        # ----------------------------------------------------
        # Router registration
        # ----------------------------------------------------
        #
        # Admin router MUST be registered before the general
        # bot router so that admin callbacks are handled by
        # their dedicated handlers.
        #
        # Security is also enforced inside admin_handlers.py.
        # ----------------------------------------------------
        dp.include_router(admin_router)
        dp.include_router(bot_router)
        # ----------------------------------------------------
        # Remove previous webhook before polling
        # ----------------------------------------------------
        await bot.delete_webhook(drop_pending_updates=False)
        logger.info("Telegram bot polling started.")
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    except asyncio.CancelledError:
        logger.info("Telegram polling task cancelled.")
        raise
    except Exception:
        logger.exception("Telegram bot stopped because of an error.")
    finally:
        if bot is not None:
            with contextlib.suppress(Exception):
                await bot.session.close()
        bot = None
        dp = None
        logger.info("Telegram bot resources released.")
# ============================================================
# FASTAPI LIFESPAN
# ============================================================
@contextlib.asynccontextmanager
async def lifespan(application: FastAPI):
    global polling_task
    logger.info("Starting %s...", settings.app_name)
    # --------------------------------------------------------
    # Initialize database
    # --------------------------------------------------------
    try:
        await init_db()
        logger.info("Database initialized successfully.")
    except Exception:
        logger.exception("Database initialization failed.")
    # --------------------------------------------------------
    # Start Telegram polling in background
    # --------------------------------------------------------
    if settings.bot_token:
        polling_task = asyncio.create_task(
            start_telegram_bot()
        )
        logger.info("Telegram polling background task created.")
    else:
        logger.warning(
            "BOT_TOKEN is empty. Application will run without Telegram bot."
        )
    # --------------------------------------------------------
    # Application is ready
    # --------------------------------------------------------
    yield
    # ========================================================
    # SHUTDOWN
    # ========================================================
    logger.info("Shutting down %s...", settings.app_name)
    # --------------------------------------------------------
    # Stop Telegram polling
    # --------------------------------------------------------
    if polling_task is not None:
        polling_task.cancel()
        with contextlib.suppress(
            asyncio.CancelledError,
            Exception,
        ):
            await polling_task
        polling_task = None
    # --------------------------------------------------------
    # Close bot session if still active
    # --------------------------------------------------------
    global bot
    if bot is not None:
        with contextlib.suppress(Exception):
            await bot.session.close()
        bot = None
    # --------------------------------------------------------
    # Close database
    # --------------------------------------------------------
    try:
        await close_db()
        logger.info("Database connection closed.")
    except Exception:
        logger.exception("Failed to close database cleanly.")
    logger.info("Application shutdown completed.")
# Apply lifespan to FastAPI
app.router.lifespan_context = lifespan
# ============================================================
# API ROUTERS
# ============================================================
# Product API
app.include_router(products_router)
# ============================================================
# ROOT
# ============================================================
@app.get("/")
async def root():
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "telegram_bot": bool(settings.bot_token),
    }
# ============================================================
# HEALTH CHECK
# ============================================================
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }
# ============================================================
# API INFORMATION
# ============================================================
@app.get("/api")
async def api_info():
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "online",
        "services": {
            "fastapi": True,
            "database": True,
            "telegram_bot": bool(settings.bot_token),
        },
    }
# ============================================================
# SYSTEM STATUS
# ============================================================
@app.get("/api/status")
async def system_status():
    return JSONResponse(
        content={
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "running",
            "database": {
                "configured": bool(settings.database_url),
            },
            "telegram": {
                "configured": bool(settings.bot_token),
                "admin_configured": bool(settings.admin_id),
                "polling": polling_task is not None
                and not polling_task.done(),
            },
        }
    )
# ============================================================
# APPLICATION ENTRY POINT
# ============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
