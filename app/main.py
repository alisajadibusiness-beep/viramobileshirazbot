from __future__ import annotations

import asyncio
import contextlib
import logging
from contextlib import asynccontextmanager

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from fastapi import FastAPI

from app.bot.admin_handlers import router as admin_router
from app.bot.handlers import router as bot_router
from app.bot.smart_pricing_handlers import router as smart_pricing_router
from app.config import settings
from app.database.connection import close_db, init_db


# ============================================================
# Logging
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format=(
        "%(asctime)s | "
        "%(levelname)s | "
        "%(name)s | "
        "%(message)s"
    ),
)

logger = logging.getLogger("vira_mobile")


# ============================================================
# Global objects
# ============================================================

bot: Bot | None = None
dp: Dispatcher | None = None
polling_task: asyncio.Task | None = None


# ============================================================
# Bot commands
# ============================================================

async def setup_bot_commands(current_bot: Bot) -> None:
    """
    Register Telegram bot commands.
    """

    commands = [
        BotCommand(
            command="start",
            description="شروع / منوی اصلی",
        ),
        BotCommand(
            command="admin",
            description="پنل مدیریت",
        ),
    ]

    await current_bot.set_my_commands(commands)


# ============================================================
# Polling
# ============================================================

async def start_polling(
    current_bot: Bot,
    current_dp: Dispatcher,
) -> None:
    """
    Start aiogram polling.
    """

    try:
        logger.info("Starting Telegram bot polling...")

        await current_dp.start_polling(
            current_bot,
            allowed_updates=current_dp.resolve_used_update_types(),
        )

    except asyncio.CancelledError:
        logger.info("Telegram polling cancelled.")
        raise

    except Exception:
        logger.exception(
            "Telegram polling stopped because of an error."
        )


# ============================================================
# Application lifespan
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    global dp
    global polling_task

    logger.info("Starting %s...", settings.app_name)

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    try:
        await init_db()
        logger.info("Database initialized successfully.")

    except Exception:
        logger.exception(
            "Database initialization failed."
        )
        raise

    # --------------------------------------------------------
    # Bot initialization
    # --------------------------------------------------------

    if not settings.bot_token:
        logger.warning(
            "BOT_TOKEN is not configured. "
            "Telegram bot polling will not start."
        )

    else:
        bot = Bot(
            token=settings.bot_token,
        )

        dp = Dispatcher()

        # ----------------------------------------------------
        # Router order
        #
        # 1. Admin
        # 2. Smart Pricing
        # 3. General Bot
        #
        # Smart Pricing must be registered before the generic
        # bot handlers so its FSM handlers receive the messages.
        # ----------------------------------------------------

        dp.include_router(admin_router)

        dp.include_router(smart_pricing_router)

        dp.include_router(bot_router)

        try:
            await setup_bot_commands(bot)

        except Exception:
            logger.exception(
                "Failed to configure Telegram bot commands."
            )

        polling_task = asyncio.create_task(
            start_polling(
                bot,
                dp,
            )
        )

        logger.info(
            "Telegram bot polling task started."
        )

    # --------------------------------------------------------
    # Application is ready
    # --------------------------------------------------------

    yield

    # ========================================================
    # Shutdown
    # ========================================================

    logger.info(
        "Shutting down %s...",
        settings.app_name,
    )

    # --------------------------------------------------------
    # Stop polling
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
    # Close bot
    # --------------------------------------------------------

    if bot is not None:
        try:
            await bot.session.close()

        except Exception:
            logger.exception(
                "Failed to close Telegram bot session."
            )

        bot = None

    dp = None

    # --------------------------------------------------------
    # Close database
    # --------------------------------------------------------

    try:
        await close_db()
        logger.info(
            "Database connection closed."
        )

    except Exception:
        logger.exception(
            "Failed to close database connection."
        )

    logger.info(
        "%s shutdown completed.",
        settings.app_name,
    )


# ============================================================
# FastAPI application
# ============================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "VIRA MOBILE API and Telegram Bot"
    ),
    lifespan=lifespan,
)


# ============================================================
# Root
# ============================================================

@app.get("/")
async def root() -> dict:
    return {
        "success": True,
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
    }


# ============================================================
# Health
# ============================================================

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# ============================================================
# API information
# ============================================================

@app.get("/api")
async def api_root() -> dict:
    return {
        "success": True,
        "name": settings.app_name,
        "version": settings.app_version,
        "services": {
            "telegram_bot": bool(settings.bot_token),
            "database": True,
            "smart_pricing": True,
            "admin_panel": True,
        },
    }


# ============================================================
# Application status
# ============================================================

@app.get("/api/status")
async def api_status() -> dict:
    telegram_status = (
        "running"
        if bot is not None and polling_task is not None
        else "stopped"
    )

    return {
        "success": True,
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "telegram_bot": telegram_status,
        "database": "configured",
        "smart_pricing": "enabled",
        "admin_panel": "enabled",
    }


# ============================================================
# Uvicorn entry point
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
