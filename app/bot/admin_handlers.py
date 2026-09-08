from __future__ import annotations

from decimal import Decimal

from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.admin_dashboard import get_admin_dashboard


router = Router()


# ============================================================
# Admin Security
# ============================================================


def is_admin(user_id: int | None) -> bool:
    """
    Check whether the Telegram user is the configured admin.
    """

    if user_id is None:
        return False

    return (
        settings.admin_id != 0
        and user_id == settings.admin_id
    )


# ============================================================
# Helpers
# ============================================================


def format_number(value: int | float | Decimal) -> str:
    """
    Format numbers with Persian-friendly thousands separators.
    """

    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def format_money(value: Decimal | int | float) -> str:
    """
    Format money values in Toman.
    """

    try:
        amount = Decimal(str(value))
    except Exception:
        amount = Decimal("0")

    return f"{amount:,.0f} تومان"


# ============================================================
# Admin Main Menu
# ============================================================


def admin_menu() -> InlineKeyboardMarkup:
    """
    Main admin panel keyboard.
    """

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📊 داشبورد",
                    callback_data="admin:dashboard",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 مدیریت محصولات",
                    callback_data="admin:products",
                ),
                InlineKeyboardButton(
                    text="📦 مدیریت موجودی",
                    callback_data="admin:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 سفارش‌ها",
                    callback_data="admin:orders",
                ),
                InlineKeyboardButton(
                    text="👥 مشتریان",
                    callback_data="admin:customers",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 قیمت‌ها",
                    callback_data="admin:prices",
                ),
                InlineKeyboardButton(
                    text="📈 آمار فروش",
                    callback_data="admin:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="home",
                ),
            ],
        ]
    )


def admin_button() -> InlineKeyboardButton:
    """
    Admin button used by other keyboards.
    """

    return InlineKeyboardButton(
        text="⚙️ پنل مدیریت",
        callback_data="admin:panel",
    )


# ============================================================
# Admin Access
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:panel"
)
async def admin_panel(
    callback: CallbackQuery,
) -> None:
    """
    Open the admin panel.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "⚙️ <b>پنل مدیریت VIRA MOBILE</b>\n\n"
        "مدیریت فروشگاه را از این بخش انجام دهید.",
        reply_markup=admin_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Dashboard
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:dashboard"
)
async def admin_dashboard(
    callback: CallbackQuery,
) -> None:
    """
    Display real dashboard statistics from database.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            dashboard = await get_admin_dashboard(session)

    except Exception:
        await callback.answer(
            "❌ خطا در دریافت اطلاعات داشبورد",
            show_alert=True,
        )
        return

    products = dashboard.get("products", {})
    inventory = dashboard.get("inventory", {})
    orders = dashboard.get("orders", {})
    customers = dashboard.get("customers", {})
    sales = dashboard.get("sales", {})
    low_stock = dashboard.get("low_stock", [])

    low_stock_count = len(low_stock)

    text = (
        "📊 <b>داشبورد مدیریت VIRA MOBILE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📱 <b>محصولات</b>\n"
        f"   ├ کل محصولات: "
        f"<b>{format_number(products.get('total', 0))}</b>\n"
        f"   ├ فعال: "
        f"<b>{format_number(products.get('active', 0))}</b>\n"
        f"   ├ غیرفعال: "
        f"<b>{format_number(products.get('inactive', 0))}</b>\n"
        f"   └ ⭐ ویژه: "
        f"<b>{format_number(products.get('featured', 0))}</b>\n\n"

        "📦 <b>موجودی</b>\n"
        f"   ├ کل واحدها: "
        f"<b>{format_number(inventory.get('total', 0))}</b>\n"
        f"   ├ موجود: "
        f"<b>{format_number(inventory.get('available', 0))}</b>\n"
        f"   ├ رزرو شده: "
        f"<b>{format_number(inventory.get('reserved', 0))}</b>\n"
        f"   ├ فروخته شده: "
        f"<b>{format_number(inventory.get('sold', 0))}</b>\n"
        f"   └ ⚠️ آسیب‌دیده: "
        f"<b>{format_number(inventory.get('damaged', 0))}</b>\n\n"

        "🛒 <b>سفارش‌ها</b>\n"
        f"   ├ کل: "
        f"<b>{format_number(orders.get('total', 0))}</b>\n"
        f"   ├ در انتظار: "
        f"<b>{format_number(orders.get('pending', 0))}</b>\n"
        f"   ├ در انتظار پرداخت: "
        f"<b>{format_number(orders.get('payment_pending', 0))}</b>\n"
        f"   ├ پرداخت شده: "
        f"<b>{format_number(orders.get('paid', 0))}</b>\n"
        f"   ├ در حال پردازش: "
        f"<b>{format_number(orders.get('processing', 0))}</b>\n"
        f"   ├ آماده ارسال: "
        f"<b>{format_number(orders.get('ready', 0))}</b>\n"
        f"   ├ ارسال شده: "
        f"<b>{format_number(orders.get('shipped', 0))}</b>\n"
        f"   ├ تحویل شده: "
        f"<b>{format_number(orders.get('delivered', 0))}</b>\n"
        f"   └ لغو شده: "
        f"<b>{format_number(orders.get('cancelled', 0))}</b>\n\n"

        "👥 <b>مشتریان</b>\n"
        f"   └ تعداد مشتریان: "
        f"<b>{format_number(customers.get('total', 0))}</b>\n\n"

        "💰 <b>فروش</b>\n"
        f"   ├ فروش امروز: "
        f"<b>{format_money(sales.get('today_sales', 0))}</b>\n"
        f"   ├ سفارش موفق امروز: "
        f"<b>{format_number(sales.get('today_orders', 0))}</b>\n"
        f"   ├ فروش کل: "
        f"<b>{format_money(sales.get('total_sales', 0))}</b>\n"
        f"   └ سفارش موفق: "
        f"<b>{format_number(sales.get('successful_orders', 0))}</b>\n\n"

        f"⚠️ <b>محصولات کم‌موجودی:</b> "
        f"<b>{format_number(low_stock_count)}</b>\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data="admin:dashboard",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 محصولات",
                    callback_data="admin:products",
                ),
                InlineKeyboardButton(
                    text="📦 موجودی",
                    callback_data="admin:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 سفارش‌ها",
                    callback_data="admin:orders",
                ),
                InlineKeyboardButton(
                    text="👥 مشتریان",
                    callback_data="admin:customers",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 قیمت‌ها",
                    callback_data="admin:prices",
                ),
                InlineKeyboardButton(
                    text="📈 آمار فروش",
                    callback_data="admin:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 پنل مدیریت",
                    callback_data="admin:panel",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Product Management
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:products"
)
async def admin_products(
    callback: CallbackQuery,
) -> None:
    """
    Product management menu.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن محصول",
                    callback_data="admin:product:add",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست محصولات",
                    callback_data="admin:product:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⭐ محصولات ویژه",
                    callback_data="admin:product:featured",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 داشبورد",
                    callback_data="admin:dashboard",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        "📱 <b>مدیریت محصولات</b>\n\n"
        "از گزینه‌های زیر برای مدیریت محصولات فروشگاه استفاده کنید.",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


@router.callback_query(
    lambda callback: callback.data == "admin:product:add"
)
async def admin_product_add(
    callback: CallbackQuery,
) -> None:
    """
    Product creation placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.answer(
        "🚧 بخش افزودن محصول در مرحله بعد فعال می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    lambda callback: callback.data == "admin:product:list"
)
async def admin_product_list(
    callback: CallbackQuery,
) -> None:
    """
    Product list placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.answer(
        "🚧 لیست محصولات در مرحله بعد متصل می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    lambda callback: callback.data == "admin:product:featured"
)
async def admin_product_featured(
    callback: CallbackQuery,
) -> None:
    """
    Featured products placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.answer(
        "🚧 مدیریت محصولات ویژه در مرحله بعد فعال می‌شود.",
        show_alert=True,
    )


# ============================================================
# Inventory Management
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:inventory"
)
async def admin_inventory(
    callback: CallbackQuery,
) -> None:
    """
    Inventory management placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📦 <b>مدیریت موجودی</b>\n\n"
        "📊 موجودی فعلی از دیتابیس در داشبورد قابل مشاهده است.\n\n"
        "🚧 امکانات کامل مدیریت موجودی در مرحله بعد اضافه می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 داشبورد",
                        callback_data="admin:dashboard",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Orders
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:orders"
)
async def admin_orders(
    callback: CallbackQuery,
) -> None:
    """
    Order management placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🛒 <b>مدیریت سفارش‌ها</b>\n\n"
        "تعداد و وضعیت سفارش‌ها در داشبورد متصل شده است.\n\n"
        "🚧 لیست کامل سفارش‌ها و مدیریت وضعیت سفارش "
        "در مرحله بعد اضافه می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 داشبورد",
                        callback_data="admin:dashboard",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Customers
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:customers"
)
async def admin_customers(
    callback: CallbackQuery,
) -> None:
    """
    Customer management placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "👥 <b>مدیریت مشتریان</b>\n\n"
        "تعداد مشتریان از دیتابیس دریافت می‌شود.\n\n"
        "🚧 لیست مشتریان و جزئیات حساب آنها "
        "در مرحله بعد اضافه می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 داشبورد",
                        callback_data="admin:dashboard",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Prices
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:prices"
)
async def admin_prices(
    callback: CallbackQuery,
) -> None:
    """
    Price management placeholder.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "💰 <b>مدیریت قیمت‌ها</b>\n\n"
        "🚧 مدیریت قیمت محصولات، قیمت‌گذاری نسخه‌ها "
        "و تاریخچه قیمت در مرحله بعد اضافه می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📊 داشبورد",
                        callback_data="admin:dashboard",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Sales Statistics
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:stats"
)
async def admin_stats(
    callback: CallbackQuery,
) -> None:
    """
    Sales statistics.
    """

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            dashboard = await get_admin_dashboard(session)

    except Exception:
        await callback.answer(
            "❌ خطا در دریافت آمار فروش",
            show_alert=True,
        )
        return

    sales = dashboard.get("sales", {})
    orders = dashboard.get("orders", {})

    text = (
        "📈 <b>آمار فروش VIRA MOBILE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "💰 <b>فروش</b>\n"
        f"├ فروش امروز: "
        f"<b>{format_money(sales.get('today_sales', 0))}</b>\n"
        f"├ فروش کل: "
        f"<b>{format_money(sales.get('total_sales', 0))}</b>\n"
        f"├ سفارش موفق امروز: "
        f"<b>{format_number(sales.get('today_orders', 0))}</b>\n"
        f"└ کل سفارش‌های موفق: "
        f"<b>{format_number(sales.get('successful_orders', 0))}</b>\n\n"

        "🛒 <b>وضعیت سفارش‌ها</b>\n"
        f"├ در انتظار: "
        f"<b>{format_number(orders.get('pending', 0))}</b>\n"
        f"├ در انتظار پرداخت: "
        f"<b>{format_number(orders.get('payment_pending', 0))}</b>\n"
        f"├ پرداخت شده: "
        f"<b>{format_number(orders.get('paid', 0))}</b>\n"
        f"├ در حال پردازش: "
        f"<b>{format_number(orders.get('processing', 0))}</b>\n"
        f"├ آماده ارسال: "
        f"<b>{format_number(orders.get('ready', 0))}</b>\n"
        f"├ ارسال شده: "
        f"<b>{format_number(orders.get('shipped', 0))}</b>\n"
        f"├ تحویل شده: "
        f"<b>{format_number(orders.get('delivered', 0))}</b>\n"
        f"└ لغو شده: "
        f"<b>{format_number(orders.get('cancelled', 0))}</b>\n\n"

        "━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data="admin:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📊 داشبورد",
                    callback_data="admin:dashboard",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 پنل مدیریت",
                    callback_data="admin:panel",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()
