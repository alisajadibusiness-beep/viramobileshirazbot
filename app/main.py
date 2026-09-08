import asyncio
from contextlib import asynccontextmanager

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from fastapi import FastAPI
from fastapi.responses import JSONResponse, Response

from app.config import settings
from app.database.connection import close_db, init_db
from app.bot.handlers import router


bot: Bot | None = None
dispatcher: Dispatcher | None = None
bot_task: asyncio.Task | None = None


async def telegram_worker():
    """
    Start Telegram bot using long polling.
    """

    global bot
    global dispatcher

    if not settings.bot_token:
        print("ERROR: BOT_TOKEN is empty.")
        print("Telegram bot cannot start.")
        return

    try:
        print("=" * 60)
        print("TELEGRAM INITIALIZATION")
        print("=" * 60)

        bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML
            ),
        )

        dispatcher = Dispatcher()

        dispatcher.include_router(router)

        # --------------------------------------------------
        # Test Telegram connection
        # --------------------------------------------------

        me = await bot.get_me()

        print(f"Telegram connection: OK")
        print(f"Bot ID: {me.id}")
        print(f"Bot username: @{me.username}")
        print(f"Bot name: {me.first_name}")

        # --------------------------------------------------
        # Remove any previous webhook
        # --------------------------------------------------

        webhook_info = await bot.get_webhook_info()

        print(f"Current webhook URL: {webhook_info.url or 'NONE'}")

        if webhook_info.url:
            print("Removing previous Telegram webhook...")

            await bot.delete_webhook(
                drop_pending_updates=False
            )

            print("Previous webhook removed successfully.")

        # --------------------------------------------------
        # Start polling
        # --------------------------------------------------

        print("=" * 60)
        print("TELEGRAM POLLING STARTED")
        print(f"Listening as: @{me.username}")
        print("=" * 60)

        await dispatcher.start_polling(
            bot,
            allowed_updates=dispatcher.resolve_used_update_types(),
        )

    except asyncio.CancelledError:
        print("Telegram worker cancelled.")
        raise

    except Exception as exc:
        print("=" * 60)
        print("TELEGRAM BOT ERROR")
        print(type(exc).__name__)
        print(str(exc))
        print("=" * 60)

    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass


async def stop_telegram():
    global bot_task
    global bot
    global dispatcher

    if bot_task is not None:
        bot_task.cancel()

        try:
            await bot_task
        except asyncio.CancelledError:
            pass
        except Exception:
            pass

        bot_task = None

    bot = None
    dispatcher = None


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("=" * 60)
    print("VIRA MOBILE STARTING")
    print("=" * 60)

    print(f"Application: {settings.app_name}")
    print(f"Version: {settings.app_version}")
    print(f"Environment: {settings.environment}")

    # ------------------------------------------------------
    # Database
    # ------------------------------------------------------

    try:
        await init_db()
        print("Database: OK")

    except Exception as exc:
        print("Database initialization error:")
        print(type(exc).__name__)
        print(str(exc))

    # ------------------------------------------------------
    # Telegram
    # ------------------------------------------------------

    global bot_task

    if settings.bot_token:
        print("BOT_TOKEN: FOUND")

        bot_task = asyncio.create_task(
            telegram_worker()
        )

    else:
        print("BOT_TOKEN: NOT FOUND")
        print("Telegram bot will NOT start.")

    yield

    # ------------------------------------------------------
    # Shutdown
    # ------------------------------------------------------

    print("Stopping VIRA MOBILE...")

    await stop_telegram()

    try:
        await close_db()
    except Exception as exc:
        print(f"Database shutdown warning: {exc}")

    print("VIRA MOBILE stopped.")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "VIRA MOBILE professional mobile store platform."
    ),
    lifespan=lifespan,
)


# ==========================================================
# HOME
# ==========================================================

@app.get("/")
async def root():

    return {
        "status": "online",
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "telegram": (
            "configured"
            if settings.bot_token
            else "not_configured"
        ),
    }


@app.head("/")
async def root_head():

    return Response(
        status_code=200
    )


# ==========================================================
# HEALTH
# ==========================================================

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


@app.head("/health")
async def health_head():

    return Response(
        status_code=200,
        headers={
            "X-Service": "VIRA MOBILE",
            "X-Health": "ok",
            "X-Version": settings.app_version,
        },
    )


# ==========================================================
# API
# ==========================================================

@app.get("/api")
async def api_status():

    return {
        "status": "online",
        "service": "VIRA MOBILE API",
        "version": settings.app_version,
    }


@app.head("/api")
async def api_head():

    return Response(
        status_code=200
    )


# ==========================================================
# STATUS
# ==========================================================

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

    return Response(
        status_code=200
    )
