from __future__ import annotations

from aiogram import Router
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from app.config import settings


router = Router()


# ==========================================================
# ADMIN ACCESS
# ==========================================================

def is_admin(user_id: int | None) -> bool:
    """
    Check whether Telegram user is the configured administrator.
    """

    if not user_id:
        return False

    if not settings.admin_id:
        return False

    return user_id == settings.admin_id


# ==========================================================
# ADMIN MENU
# ==========================================================

def admin_menu() -> InlineKeyboardMarkup:

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
            ],
            [
                InlineKeyboardButton(
                    text="📦 مدیریت موجودی",
                    callback_data="admin:inventory",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🛒 مدیریت سفارش‌ها",
                    callback_data="admin:orders",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 مشتریان",
                    callback_data="admin:customers",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 مدیریت قیمت‌ها",
                    callback_data="admin:prices",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 آمار فروش",
                    callback_data="admin:stats",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🏠 منوی اصلی",
                    callback_data="home",
                ),
            ],
        ]
    )


# ==========================================================
# ADMIN BUTTON
# ==========================================================

def admin_button() -> InlineKeyboardButton:

    return InlineKeyboardButton(
        text="⚙️ پنل مدیریت",
        callback_data="admin:panel",
    )


# ==========================================================
# ADMIN PANEL
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:panel"
)
async def admin_panel_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "⚙️ پنل مدیریت VIRA MOBILE\n\n"
        "به بخش مدیریت فروشگاه خوش آمدید.\n\n"
        "لطفاً بخش موردنظر را انتخاب کنید:",
        reply_markup=admin_menu(),
    )


# ==========================================================
# DASHBOARD
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:dashboard"
)
async def admin_dashboard_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "📊 داشبورد مدیریت\n\n"
        "📱 محصولات: در حال اتصال\n"
        "📦 موجودی: در حال اتصال\n"
        "🛒 سفارش‌ها: در حال اتصال\n"
        "👥 مشتریان: در حال اتصال\n"
        "💰 فروش: در حال اتصال\n\n"
        "این بخش در مرحله بعد به دیتابیس متصل می‌شود.",
        reply_markup=admin_menu(),
    )


# ==========================================================
# PRODUCTS
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:products"
)
async def admin_products_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

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
                    text="🔙 پنل مدیریت",
                    callback_data="admin:panel",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        "📱 مدیریت محصولات\n\n"
        "عملیات موردنظر را انتخاب کنید:",
        reply_markup=keyboard,
    )


# ==========================================================
# INVENTORY
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:inventory"
)
async def admin_inventory_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن موجودی",
                    callback_data="admin:inventory:add",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📋 مشاهده موجودی",
                    callback_data="admin:inventory:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="⚠️ موجودی کم",
                    callback_data="admin:inventory:low",
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
        "📦 مدیریت موجودی\n\n"
        "عملیات موردنظر را انتخاب کنید:",
        reply_markup=keyboard,
    )


# ==========================================================
# ORDERS
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:orders"
)
async def admin_orders_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "🛒 مدیریت سفارش‌ها\n\n"
        "📋 سفارش‌های جدید\n"
        "💳 در انتظار پرداخت\n"
        "⚙️ در حال پردازش\n"
        "🚚 ارسال‌شده\n"
        "✅ تحویل‌شده\n"
        "❌ لغوشده\n\n"
        "مدیریت سفارش‌ها در مرحله بعد فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    )
                ]
            ]
        ),
    )


# ==========================================================
# CUSTOMERS
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:customers"
)
async def admin_customers_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "👥 مدیریت مشتریان\n\n"
        "مشاهده مشتریان، اطلاعات حساب، "
        "سابقه سفارش و وضعیت مشتری در این بخش قرار می‌گیرد.\n\n"
        "این بخش در مرحله بعد به دیتابیس متصل می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    )
                ]
            ]
        ),
    )


# ==========================================================
# PRICES
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:prices"
)
async def admin_prices_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "💰 مدیریت قیمت‌ها\n\n"
        "در این بخش امکان مشاهده و تغییر قیمت "
        "محصولات و ثبت تاریخچه قیمت وجود خواهد داشت.\n\n"
        "سیستم قیمت‌گذاری در مرحله بعد فعال می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    )
                ]
            ]
        ),
    )


# ==========================================================
# STATISTICS
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:stats"
)
async def admin_stats_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer()

    await callback.message.edit_text(
        "📈 آمار فروش\n\n"
        "فروش امروز: در حال اتصال\n"
        "فروش این ماه: در حال اتصال\n"
        "تعداد سفارش‌ها: در حال اتصال\n"
        "مبلغ فروش: در حال اتصال\n\n"
        "گزارش‌های آماری پس از اتصال سرویس سفارش‌ها "
        "فعال خواهند شد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 پنل مدیریت",
                        callback_data="admin:panel",
                    )
                ]
            ]
        ),
    )


# ==========================================================
# PRODUCT PLACEHOLDERS
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "admin:product:add"
)
async def admin_product_add_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer(
        "➕ فرم افزودن محصول در مرحله بعد ساخته می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    lambda callback: callback.data == "admin:product:list"
)
async def admin_product_list_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer(
        "📋 لیست مدیریت محصولات در مرحله بعد ساخته می‌شود.",
        show_alert=True,
    )


@router.callback_query(
    lambda callback: callback.data == "admin:product:featured"
)
async def admin_product_featured_handler(
    callback: CallbackQuery,
):

    if not is_admin(callback.from_user.id):

        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )

        return

    await callback.answer(
        "⭐ مدیریت محصولات ویژه در مرحله بعد ساخته می‌شود.",
        show_alert=True,
    )
