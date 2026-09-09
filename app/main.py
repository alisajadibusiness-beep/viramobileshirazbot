from __future__ import annotations

import asyncio
import contextlib
import logging

import uvicorn
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.bot.admin_handlers import router as admin_router
from app.bot.handlers import router as bot_router
from app.bot.smart_pricing_handlers import router as smart_pricing_router
from app.bot.smart_pricing_admin_handlers import (
    router as smart_pricing_admin_router,
)
from app.config import settings
from app.database.connection import close_db, init_db


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


bot: Bot | None = None
dp: Dispatcher | None = None
polling_task: asyncio.Task | None = None


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


async def start_polling(
    current_bot: Bot,
    current_dp: Dispatcher,
) -> None:
    try:
        logger.info(
            "Starting Telegram bot polling..."
        )

        await current_dp.start_polling(
            current_bot,
            allowed_updates=(
                current_dp.resolve_used_update_types()
            ),
        )

    except asyncio.CancelledError:
        logger.info(
            "Telegram polling cancelled."
        )
        raise

    except Exception:
        logger.exception(
            "Telegram polling stopped because of an error."
        )


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global bot
    global dp
    global polling_task

    logger.info(
        "Starting %s...",
        settings.app_name,
    )

    # ======================================================
    # DATABASE
    # ======================================================

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

    # ======================================================
    # TELEGRAM BOT
    # ======================================================

    if not settings.bot_token:

        logger.error(
            "BOT_TOKEN is not configured. "
            "Telegram bot polling will NOT start."
        )

    else:

        bot = Bot(
            token=settings.bot_token
        )

        dp = Dispatcher()

        # --------------------------------------------------
        # ROUTERS
        # --------------------------------------------------

        dp.include_router(
            admin_router
        )

        dp.include_router(
            smart_pricing_admin_router
        )

        dp.include_router(
            smart_pricing_router
        )

        dp.include_router(
            bot_router
        )

        logger.info(
            "All Telegram routers registered successfully."
        )

        # --------------------------------------------------
        # TELEGRAM AUTHENTICATION
        # --------------------------------------------------

        try:

            me = await bot.get_me()

            logger.info(
                "Telegram authentication successful: "
                "@%s (id=%s)",
                me.username,
                me.id,
            )

            await setup_bot_commands(
                bot
            )

            logger.info(
                "Telegram bot commands configured."
            )

        except Exception:

            logger.exception(
                "Telegram authentication/command setup failed. "
                "Check BOT_TOKEN in Render Environment Variables."
            )

            try:
                await bot.session.close()
            except Exception:
                logger.exception(
                    "Failed to close Telegram bot session."
                )

            bot = None
            dp = None

        else:

            # ------------------------------------------------
            # START POLLING
            # ------------------------------------------------

            polling_task = asyncio.create_task(
                start_polling(
                    bot,
                    dp,
                )
            )

            logger.info(
                "Telegram bot polling task started."
            )

    # ======================================================
    # APPLICATION RUNNING
    # ======================================================

    yield

    # ======================================================
    # SHUTDOWN
    # ======================================================

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


# ==========================================================
# FASTAPI
# ==========================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "VIRA MOBILE API and Telegram Bot"
    ),
    lifespan=lifespan,
)


# ==========================================================
# ROOT
# GET + HEAD
# ==========================================================

@app.api_route(
    "/",
    methods=[
        "GET",
        "HEAD",
    ],
)
async def root() -> JSONResponse:

    return JSONResponse(
        {
            "success": True,
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "status": "running",
        }
    )


# ==========================================================
# HEALTH
# GET + HEAD
# ==========================================================

@app.api_route(
    "/health",
    methods=[
        "GET",
        "HEAD",
    ],
)
async def health() -> JSONResponse:

    telegram_status = (
        "running"
        if (
            bot is not None
            and polling_task is not None
            and not polling_task.done()
        )
        else "stopped"
    )

    return JSONResponse(
        {
            "status": "ok",
            "app": settings.app_name,
            "version": settings.app_version,
            "telegram_bot": telegram_status,
        }
    )


# ==========================================================
# API
# GET + HEAD
# ==========================================================

@app.api_route(
    "/api",
    methods=[
        "GET",
        "HEAD",
    ],
)
async def api_root() -> JSONResponse:

    return JSONResponse(
        {
            "success": True,
            "name": settings.app_name,
            "version": settings.app_version,
            "services": {
                "telegram_bot": (
                    bot is not None
                ),
                "database": True,
                "smart_pricing": True,
                "admin_panel": True,
            },
        }
    )


# ==========================================================
# API STATUS
# GET + HEAD
# ==========================================================

@app.api_route(
    "/api/status",
    methods=[
        "GET",
        "HEAD",
    ],
)
async def api_status() -> JSONResponse:

    telegram_status = (
        "running"
        if (
            bot is not None
            and polling_task is not None
            and not polling_task.done()
        )
        else "stopped"
    )

    return JSONResponse(
        {
            "success": True,
            "app": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
            "telegram_bot": telegram_status,
            "database": "configured",
            "smart_pricing": "enabled",
            "admin_panel": "enabled",
        }
    )


# ==========================================================
# LOCAL RUN
# ==========================================================

if __name__ == "__main__":

    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )
