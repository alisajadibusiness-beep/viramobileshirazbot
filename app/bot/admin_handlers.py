from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.services.admin_dashboard import get_admin_dashboard
from app.services.admin_products import (
    count_admin_products,
    create_product,
    get_admin_products,
    get_product,
    set_product_active,
    set_product_featured,
)


router = Router()


# ============================================================
# Admin Security
# ============================================================


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False

    return (
        settings.admin_id != 0
        and user_id == settings.admin_id
    )


# ============================================================
# Helpers
# ============================================================


def format_number(value: int | float) -> str:
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "0"


def format_money(value) -> str:
    try:
        amount = Decimal(str(value or 0))
    except Exception:
        amount = Decimal("0")

    return f"{amount:,.0f} تومان"


# ============================================================
# Product Creation FSM
# ============================================================


class ProductCreateStates(StatesGroup):
    sku = State()
    brand = State()
    model = State()
    category = State()
    condition = State()
    price = State()
    short_description = State()
    description = State()
    image = State()


# ============================================================
# Main Admin Menu
# ============================================================


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
    return InlineKeyboardButton(
        text="⚙️ پنل مدیریت",
        callback_data="admin:panel",
    )


# ============================================================
# Admin Panel
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:panel"
)
async def admin_panel(
    callback: CallbackQuery,
) -> None:

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

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            dashboard = await get_admin_dashboard(
                session
            )

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

    text = (
        "📊 <b>داشبورد مدیریت VIRA MOBILE</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"

        "📱 <b>محصولات</b>\n"
        f"├ کل: <b>{format_number(products.get('total', 0))}</b>\n"
        f"├ فعال: <b>{format_number(products.get('active', 0))}</b>\n"
        f"├ غیرفعال: <b>{format_number(products.get('inactive', 0))}</b>\n"
        f"└ ⭐ ویژه: <b>{format_number(products.get('featured', 0))}</b>\n\n"

        "📦 <b>موجودی</b>\n"
        f"├ کل: <b>{format_number(inventory.get('total', 0))}</b>\n"
        f"├ موجود: <b>{format_number(inventory.get('available', 0))}</b>\n"
        f"├ رزرو: <b>{format_number(inventory.get('reserved', 0))}</b>\n"
        f"└ فروخته‌شده: <b>{format_number(inventory.get('sold', 0))}</b>\n\n"

        "🛒 <b>سفارش‌ها</b>\n"
        f"├ کل: <b>{format_number(orders.get('total', 0))}</b>\n"
        f"├ در انتظار: <b>{format_number(orders.get('pending', 0))}</b>\n"
        f"├ پرداخت شده: <b>{format_number(orders.get('paid', 0))}</b>\n"
        f"├ در حال پردازش: <b>{format_number(orders.get('processing', 0))}</b>\n"
        f"├ ارسال شده: <b>{format_number(orders.get('shipped', 0))}</b>\n"
        f"└ تحویل شده: <b>{format_number(orders.get('delivered', 0))}</b>\n\n"

        "👥 <b>مشتریان</b>\n"
        f"└ تعداد: <b>{format_number(customers.get('total', 0))}</b>\n\n"

        "💰 <b>فروش</b>\n"
        f"├ امروز: <b>{format_money(sales.get('today_sales', 0))}</b>\n"
        f"├ سفارش امروز: <b>{format_number(sales.get('today_orders', 0))}</b>\n"
        f"└ فروش کل: <b>{format_money(sales.get('total_sales', 0))}</b>\n\n"

        f"⚠️ <b>کم‌موجودی:</b> "
        f"<b>{format_number(len(low_stock))}</b>\n"
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
# Product Management Menu
# ============================================================


def product_management_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
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


@router.callback_query(
    lambda callback: callback.data == "admin:products"
)
async def admin_products(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📱 <b>مدیریت محصولات</b>\n\n"
        "از گزینه‌های زیر استفاده کنید:",
        reply_markup=product_management_menu(),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# CREATE PRODUCT
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:product:add"
)
async def admin_product_add(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        ProductCreateStates.sku
    )

    await callback.message.edit_text(
        "➕ <b>افزودن محصول جدید</b>\n\n"
        "مرحله ۱ از ۹\n\n"
        "🏷 <b>کد SKU محصول را وارد کنید:</b>\n\n"
        "مثال:\n"
        "<code>IPH15PM-256-BLK</code>",
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# SKU
# ============================================================


@router.message(ProductCreateStates.sku)
async def product_create_sku(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    sku = (message.text or "").strip()

    if not sku:
        await message.answer(
            "❌ SKU نمی‌تواند خالی باشد.\n"
            "دوباره وارد کنید:"
        )
        return

    await state.update_data(
        sku=sku
    )

    await state.set_state(
        ProductCreateStates.brand
    )

    await message.answer(
        "مرحله ۲ از ۹\n\n"
        "🏷 <b>برند محصول را وارد کنید:</b>\n\n"
        "مثال: Apple",
        parse_mode="HTML",
    )


# ============================================================
# BRAND
# ============================================================


@router.message(ProductCreateStates.brand)
async def product_create_brand(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    brand = (message.text or "").strip()

    if not brand:
        await message.answer(
            "❌ برند نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        brand=brand
    )

    await state.set_state(
        ProductCreateStates.model
    )

    await message.answer(
        "مرحله ۳ از ۹\n\n"
        "📱 <b>مدل گوشی را وارد کنید:</b>\n\n"
        "مثال: iPhone 15 Pro Max 256GB",
        parse_mode="HTML",
    )


# ============================================================
# MODEL
# ============================================================


@router.message(ProductCreateStates.model)
async def product_create_model(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    model = (message.text or "").strip()

    if not model:
        await message.answer(
            "❌ مدل نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        model=model
    )

    await state.set_state(
        ProductCreateStates.category
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍎 آیفون",
                    callback_data="product_category:iphone",
                ),
                InlineKeyboardButton(
                    text="📱 سامسونگ",
                    callback_data="product_category:samsung",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 شیائومی",
                    callback_data="product_category:xiaomi",
                ),
                InlineKeyboardButton(
                    text="📱 سایر",
                    callback_data="product_category:other",
                ),
            ],
        ]
    )

    await message.answer(
        "مرحله ۴ از ۹\n\n"
        "📂 <b>دسته‌بندی محصول را انتخاب کنید:</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# CATEGORY
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith(
            "product_category:"
        )
    )
)
async def product_create_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    category = callback.data.split(
        ":",
        1,
    )[1]

    category_names = {
        "iphone": "آیفون",
        "samsung": "سامسونگ",
        "xiaomi": "شیائومی",
        "other": "سایر",
    }

    await state.update_data(
        category=category
    )

    await state.set_state(
        ProductCreateStates.condition
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🆕 نو",
                    callback_data="product_condition:NEW",
                ),
                InlineKeyboardButton(
                    text="♻️ کارکرده",
                    callback_data="product_condition:USED",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        "مرحله ۵ از ۹\n\n"
        "📦 <b>وضعیت محصول را انتخاب کنید:</b>\n\n"
        f"دسته‌بندی انتخاب‌شده: "
        f"<b>{category_names.get(category, category)}</b>",
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# CONDITION
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith(
            "product_condition:"
        )
    )
)
async def product_create_condition(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    condition = callback.data.split(
        ":",
        1,
    )[1]

    await state.update_data(
        condition=condition
    )

    await state.set_state(
        ProductCreateStates.price
    )

    await callback.message.edit_text(
        "مرحله ۶ از ۹\n\n"
        "💰 <b>قیمت محصول را به تومان وارد کنید:</b>\n\n"
        "مثال:\n"
        "<code>45900000</code>",
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# PRICE
# ============================================================


@router.message(ProductCreateStates.price)
async def product_create_price(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    raw_price = (
        (message.text or "")
        .strip()
        .replace(",", "")
        .replace("٬", "")
        .replace("تومان", "")
        .strip()
    )

    try:
        price = Decimal(raw_price)

        if price < 0:
            raise InvalidOperation

    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ قیمت نامعتبر است.\n\n"
            "لطفاً فقط عدد وارد کنید.\n"
            "مثال: <code>45900000</code>",
            parse_mode="HTML",
        )
        return

    await state.update_data(
        base_price=price
    )

    await state.set_state(
        ProductCreateStates.short_description
    )

    await message.answer(
        "مرحله ۷ از ۹\n\n"
        "📝 <b>توضیح کوتاه محصول را وارد کنید:</b>\n\n"
        "مثال:\n"
        "آیفون ۱۵ پرو مکس ظرفیت ۲۵۶ گیگ",
        parse_mode="HTML",
    )


# ============================================================
# SHORT DESCRIPTION
# ============================================================


@router.message(
    ProductCreateStates.short_description
)
async def product_create_short_description(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    short_description = (
        message.text or ""
    ).strip()

    await state.update_data(
        short_description=short_description
    )

    await state.set_state(
        ProductCreateStates.description
    )

    await message.answer(
        "مرحله ۸ از ۹\n\n"
        "📄 <b>توضیحات کامل محصول را وارد کنید:</b>\n\n"
        "می‌توانید مشخصات، گارانتی، شرایط فروش و توضیحات "
        "تکمیلی را وارد کنید.\n\n"
        "اگر توضیحی ندارید، بنویسید:\n"
        "<code>-</code>",
        parse_mode="HTML",
    )


# ============================================================
# DESCRIPTION
# ============================================================


@router.message(
    ProductCreateStates.description
)
async def product_create_description(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    description = (
        message.text or ""
    ).strip()

    if description == "-":
        description = ""

    await state.update_data(
        description=description
    )

    await state.set_state(
        ProductCreateStates.image
    )

    await message.answer(
        "مرحله ۹ از ۹\n\n"
        "🖼 <b>عکس محصول را ارسال کنید.</b>\n\n"
        "عکس را به‌صورت Photo در تلگرام ارسال کنید.\n\n"
        "اگر فعلاً عکس ندارید، کلمه زیر را بفرستید:\n"
        "<code>skip</code>",
        parse_mode="HTML",
    )


# ============================================================
# IMAGE
# ============================================================


@router.message(ProductCreateStates.image)
async def product_create_image(
    message: Message,
    state: FSMContext,
) -> None:

    if not is_admin(message.from_user.id):
        return

    image_url = ""

    if message.photo:
        image_url = (
            message.photo[-1].file_id
        )

    elif message.text:
        text = message.text.strip()

        if text.lower() == "skip":
            image_url = ""

        else:
            await message.answer(
                "❌ لطفاً عکس را به‌صورت Photo ارسال کنید.\n\n"
                "اگر عکس ندارید، <code>skip</code> را بفرستید.",
                parse_mode="HTML",
            )
            return

    else:
        await message.answer(
            "❌ عکس محصول دریافت نشد."
        )
        return

    await state.update_data(
        image_url=image_url
    )

    data = await state.get_data()

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ ثبت محصول",
                    callback_data="admin:product:create:confirm",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="admin:product:create:cancel",
                ),
            ],
        ]
    )

    condition_text = {
        "NEW": "نو",
        "USED": "کارکرده",
    }.get(
        data.get("condition"),
        data.get("condition", "-"),
    )

    category_text = {
        "iphone": "آیفون",
        "samsung": "سامسونگ",
        "xiaomi": "شیائومی",
        "other": "سایر",
    }.get(
        data.get("category"),
        data.get("category", "-"),
    )

    preview = (
        "📋 <b>پیش‌نمایش محصول</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷 SKU: <code>{data.get('sku')}</code>\n"
        f"🏢 برند: <b>{data.get('brand')}</b>\n"
        f"📱 مدل: <b>{data.get('model')}</b>\n"
        f"📂 دسته: <b>{category_text}</b>\n"
        f"📦 وضعیت: <b>{condition_text}</b>\n"
        f"💰 قیمت: <b>{format_money(data.get('base_price'))}</b>\n"
        f"📝 توضیح کوتاه: <b>{data.get('short_description') or '-'}</b>\n"
        f"📄 توضیحات: <b>{data.get('description') or '-'}</b>\n"
        f"🖼 عکس: <b>{'دارد' if image_url else 'ندارد'}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "آیا اطلاعات صحیح است؟"
    )

    await message.answer(
        preview,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# CONFIRM CREATE
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        == "admin:product:create:confirm"
    )
)
async def product_create_confirm(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    data = await state.get_data()

    required_fields = [
        "sku",
        "brand",
        "model",
        "category",
        "condition",
        "base_price",
    ]

    missing = [
        field
        for field in required_fields
        if not data.get(field)
    ]

    if missing:
        await callback.answer(
            "❌ اطلاعات محصول ناقص است.",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:

            product = await create_product(
                session,
                sku=data["sku"],
                brand=data["brand"],
                model=data["model"],
                category=data["category"],
                condition=data["condition"],
                base_price=Decimal(
                    str(data["base_price"])
                ),
                short_description=data.get(
                    "short_description",
                    "",
                ),
                description=data.get(
                    "description",
                    "",
                ),
                image_url=data.get(
                    "image_url",
                    "",
                ),
                is_active=True,
                is_featured=False,
            )

    except Exception as exc:
        error_text = str(exc)

        await callback.message.edit_text(
            "❌ <b>ثبت محصول انجام نشد.</b>\n\n"
            f"خطا: <code>{error_text[:500]}</code>",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت محصولات",
                            callback_data="admin:products",
                        ),
                    ],
                ]
            ),
        )

        await state.clear()
        await callback.answer()
        return

    await state.clear()

    await callback.message.edit_text(
        "✅ <b>محصول با موفقیت ثبت شد.</b>\n\n"
        f"🆔 شناسه محصول: <code>{product.id}</code>\n"
        f"🏷 SKU: <code>{product.sku}</code>\n"
        f"📱 {product.brand} {product.model}\n"
        f"💰 {format_money(product.base_price)}\n\n"
        "محصول در دیتابیس ذخیره شد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="➕ افزودن محصول دیگر",
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
                        text="🔙 مدیریت محصولات",
                        callback_data="admin:products",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer(
        "✅ محصول ثبت شد"
    )


# ============================================================
# CANCEL CREATE
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        == "admin:product:create:cancel"
    )
)
async def product_create_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_text(
        "❌ <b>افزودن محصول لغو شد.</b>",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مدیریت محصولات",
                        callback_data="admin:products",
                    ),
                ],
            ]
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# PRODUCT LIST
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:product:list"
)
async def admin_product_list(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:

            products = await get_admin_products(
                session,
                limit=30,
            )

            total = await count_admin_products(
                session
            )

    except Exception:
        await callback.answer(
            "❌ خطا در دریافت محصولات",
            show_alert=True,
        )
        return

    if not products:
        text = (
            "📋 <b>لیست محصولات</b>\n\n"
            "هنوز هیچ محصولی ثبت نشده است."
        )

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
                        text="🔙 مدیریت محصولات",
                        callback_data="admin:products",
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
        return

    text = (
        "📋 <b>لیست محصولات</b>\n"
        f"تعداد کل: <b>{format_number(total)}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
    )

    buttons = []

    for product in products:

        status = (
            "🟢"
            if product.is_active
            else "🔴"
        )

        featured = (
            " ⭐"
            if product.is_featured
            else ""
        )

        text += (
            f"{status} <b>{product.brand} "
            f"{product.model}</b>{featured}\n"
            f"   🆔 {product.id} | "
            f"💰 {format_money(product.base_price)}\n\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{status} "
                        f"{product.brand} "
                        f"{product.model}"
                    ),
                    callback_data=(
                        f"admin:product:view:"
                        f"{product.id}"
                    ),
                )
            ]
        )

    buttons.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ افزودن محصول",
                    callback_data="admin:product:add",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 بروزرسانی",
                    callback_data="admin:product:list",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 مدیریت محصولات",
                    callback_data="admin:products",
                ),
            ],
        ]
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=buttons
        ),
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# PRODUCT VIEW
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith(
            "admin:product:view:"
        )
    )
)
async def admin_product_view(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        product_id = int(
            callback.data.rsplit(":", 1)[1]
        )
    except (ValueError, TypeError):
        await callback.answer(
            "❌ شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            product = await get_product(
                session,
                product_id,
            )

    except Exception:
        await callback.answer(
            "❌ خطا در دریافت محصول",
            show_alert=True,
        )
        return

    if product is None:
        await callback.answer(
            "❌ محصول پیدا نشد.",
            show_alert=True,
        )
        return

    status = (
        "🟢 فعال"
        if product.is_active
        else "🔴 غیرفعال"
    )

    featured = (
        "⭐ بله"
        if product.is_featured
        else "▫️ خیر"
    )

    condition = {
        "NEW": "🆕 نو",
        "USED": "♻️ کارکرده",
    }.get(
        getattr(
            product.condition,
            "value",
            product.condition,
        ),
        str(product.condition),
    )

    text = (
        "📱 <b>جزئیات محصول</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 شناسه: <code>{product.id}</code>\n"
        f"🏷 SKU: <code>{product.sku}</code>\n"
        f"🏢 برند: <b>{product.brand}</b>\n"
        f"📱 مدل: <b>{product.model}</b>\n"
        f"📂 دسته: <b>{product.category}</b>\n"
        f"📦 وضعیت: <b>{condition}</b>\n"
        f"💰 قیمت: <b>{format_money(product.base_price)}</b>\n"
        f"🔘 وضعیت فروش: <b>{status}</b>\n"
        f"⭐ ویژه: <b>{featured}</b>\n"
        f"📝 توضیح کوتاه:\n"
        f"{product.short_description or '-'}\n\n"
        f"📄 توضیحات:\n"
        f"{product.description or '-'}\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    active_callback = (
        f"admin:product:deactivate:{product.id}"
        if product.is_active
        else f"admin:product:activate:{product.id}"
    )

    featured_callback = (
        f"admin:product:unfeatured:{product.id}"
        if product.is_featured
        else f"admin:product:featured:{product.id}"
    )

    active_text = (
        "🔴 غیرفعال کردن"
        if product.is_active
        else "🟢 فعال کردن"
    )

    featured_text = (
        "⭐ حذف از ویژه"
        if product.is_featured
        else "⭐ ویژه کردن"
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=active_text,
                    callback_data=active_callback,
                ),
            ],
            [
                InlineKeyboardButton(
                    text=featured_text,
                    callback_data=featured_callback,
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
                    text="🔙 مدیریت محصولات",
                    callback_data="admin:products",
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
# ACTIVATE / DEACTIVATE
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        and (
            callback.data.startswith(
                "admin:product:activate:"
            )
            or callback.data.startswith(
                "admin:product:deactivate:"
            )
        )
    )
)
async def admin_product_active_toggle(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        parts = callback.data.split(":")

        action = parts[2]
        product_id = int(parts[3])

    except (ValueError, IndexError, TypeError):
        await callback.answer(
            "❌ اطلاعات نامعتبر است.",
            show_alert=True,
        )
        return

    active = action == "activate"

    try:
        async with AsyncSessionLocal() as session:

            product = await set_product_active(
                session,
                product_id,
                active,
            )

    except Exception:
        await callback.answer(
            "❌ خطا در تغییر وضعیت محصول",
            show_alert=True,
        )
        return

    if product is None:
        await callback.answer(
            "❌ محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(
        "✅ وضعیت محصول تغییر کرد."
    )

    # Refresh product view
    await admin_product_view(callback)


# ============================================================
# FEATURED TOGGLE
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        and (
            callback.data.startswith(
                "admin:product:featured:"
            )
            or callback.data.startswith(
                "admin:product:unfeatured:"
            )
        )
    )
)
async def admin_product_featured_toggle(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        parts = callback.data.split(":")

        action = parts[2]
        product_id = int(parts[3])

    except (ValueError, IndexError, TypeError):
        await callback.answer(
            "❌ اطلاعات نامعتبر است.",
            show_alert=True,
        )
        return

    featured = action == "featured"

    try:
        async with AsyncSessionLocal() as session:

            product = await set_product_featured(
                session,
                product_id,
                featured,
            )

    except Exception:
        await callback.answer(
            "❌ خطا در تغییر وضعیت ویژه",
            show_alert=True,
        )
        return

    if product is None:
        await callback.answer(
            "❌ محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.answer(
        "⭐ وضعیت ویژه محصول تغییر کرد."
    )

    await admin_product_view(callback)


# ============================================================
# FEATURED PRODUCTS
# ============================================================


@router.callback_query(
    lambda callback: (
        callback.data
        == "admin:product:featured"
    )
)
async def admin_product_featured(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:

            products = await get_admin_products(
                session,
                limit=100,
            )

    except Exception:
        await callback.answer(
            "❌ خطا در دریافت محصولات",
            show_alert=True,
        )
        return

    featured_products = [
        product
        for product in products
        if product.is_featured
    ]

    if not featured_products:
        text = (
            "⭐ <b>محصولات ویژه</b>\n\n"
            "هنوز محصول ویژه‌ای ثبت نشده است."
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📋 لیست محصولات",
                        callback_data="admin:product:list",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت محصولات",
                        callback_data="admin:products",
                    ),
                ],
            ]
        )

    else:
        text = (
            "⭐ <b>محصولات ویژه</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
        )

        buttons = []

        for product in featured_products:

            text += (
                f"⭐ <b>{product.brand} "
                f"{product.model}</b>\n"
                f"💰 {format_money(product.base_price)}\n\n"
            )

            buttons.append(
                [
                    InlineKeyboardButton(
                        text=(
                            f"⭐ {product.brand} "
                            f"{product.model}"
                        ),
                        callback_data=(
                            f"admin:product:view:"
                            f"{product.id}"
                        ),
                    )
                ]
            )

        buttons.append(
            [
                InlineKeyboardButton(
                    text="🔙 مدیریت محصولات",
                    callback_data="admin:products",
                )
            ]
        )

        keyboard = InlineKeyboardMarkup(
            inline_keyboard=buttons
        )

    await callback.message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )

    await callback.answer()


# ============================================================
# Inventory
# ============================================================


@router.callback_query(
    lambda callback: callback.data == "admin:inventory"
)
async def admin_inventory(
    callback: CallbackQuery,
) -> None:

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📦 <b>مدیریت موجودی</b>\n\n"
        "آمار موجودی در داشبورد به دیتابیس متصل است.\n\n"
        "🚧 مدیریت واحدهای موجودی در مرحله بعد اضافه می‌شود.",
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

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🛒 <b>مدیریت سفارش‌ها</b>\n\n"
        "آمار سفارش‌ها به دیتابیس متصل است.\n\n"
        "🚧 مدیریت کامل سفارش‌ها در مرحله بعد اضافه می‌شود.",
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

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "👥 <b>مدیریت مشتریان</b>\n\n"
        "تعداد مشتریان از دیتابیس دریافت می‌شود.\n\n"
        "🚧 لیست و مدیریت مشتریان در مرحله بعد اضافه می‌شود.",
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

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "💰 <b>مدیریت قیمت‌ها</b>\n\n"
        "قیمت پایه محصولات از دیتابیس خوانده می‌شود.\n\n"
        "🚧 ویرایش قیمت و تاریخچه قیمت در مرحله بعد اضافه می‌شود.",
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

    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز",
            show_alert=True,
        )
        return

    try:
        async with AsyncSessionLocal() as session:
            dashboard = await get_admin_dashboard(
                session
            )

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
        f"├ امروز: <b>{format_money(sales.get('today_sales', 0))}</b>\n"
        f"├ کل: <b>{format_money(sales.get('total_sales', 0))}</b>\n"
        f"├ سفارش موفق امروز: <b>{format_number(sales.get('today_orders', 0))}</b>\n"
        f"└ سفارش موفق کل: <b>{format_number(sales.get('successful_orders', 0))}</b>\n\n"

        "🛒 <b>سفارش‌ها</b>\n"
        f"├ در انتظار: <b>{format_number(orders.get('pending', 0))}</b>\n"
        f"├ پرداخت شده: <b>{format_number(orders.get('paid', 0))}</b>\n"
        f"├ پردازش: <b>{format_number(orders.get('processing', 0))}</b>\n"
        f"├ ارسال شده: <b>{format_number(orders.get('shipped', 0))}</b>\n"
        f"└ تحویل شده: <b>{format_number(orders.get('delivered', 0))}</b>\n\n"
        "━━━━━━━━━━━━━━━━━━"
    )

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(
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
        ),
        parse_mode="HTML",
    )

    await callback.answer()
