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
from app.bot.smart_pricing_admin_handlers import (
    router as smart_pricing_admin_router,
)
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
# Global bot state
# ============================================================

bot: Bot | None = None
dp: Dispatcher | None = None
polling_task: asyncio.Task | None = None


# ============================================================
# Telegram commands
# ============================================================

async def setup_bot_commands(current_bot: Bot) -> None:
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
# Telegram polling
# ============================================================

async def start_polling(
    current_bot: Bot,
    current_dp: Dispatcher,
) -> None:
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

    logger.info(
        "Starting %s...",
        settings.app_name,
    )

    # --------------------------------------------------------
    # Database
    # --------------------------------------------------------

    try:
        await init_db()

        logger.info(
            "Database initialized successfully."
        )

    except Exception:
        logger.exception(
            "Database initialization failed."
        )
        raise

    # --------------------------------------------------------
    # Telegram
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

        # Admin
        dp.include_router(admin_router)

        # Smart Pricing Admin
        dp.include_router(
            smart_pricing_admin_router
        )

        # Customer Smart Pricing
        dp.include_router(
            smart_pricing_router
        )

        # General bot handlers
        dp.include_router(bot_router)

        try:
            await setup_bot_commands(bot)

            logger.info(
                "Telegram bot commands configured."
            )

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
    # Application running
    # --------------------------------------------------------

    yield

    # --------------------------------------------------------
    # Shutdown
    # --------------------------------------------------------

    logger.info(
        "Shutting down %s...",
        settings.app_name,
    )

    if polling_task is not None:
        polling_task.cancel()

        with contextlib.suppress(
            asyncio.CancelledError,
            Exception,
        ):
            await polling_task

        polling_task = None

    if bot is not None:
        try:
            await bot.session.close()

        except Exception:
            logger.exception(
                "Failed to close Telegram bot session."
            )

        bot = None

    dp = None

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
# FastAPI
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
# Health Check
# ============================================================

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
    }


# ============================================================
# API Root
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
# API Status
# ============================================================

@app.get("/api/status")
async def api_status() -> dict:
    telegram_status = (
        "running"
        if (
            bot is not None
            and polling_task is not None
            and not polling_task.done()
        )
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
# Local execution
# ============================================================

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
