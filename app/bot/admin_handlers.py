from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.filters import Command
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
from app.services.admin_products import (
    create_product,
    get_admin_products,
    get_product,
    set_product_active,
    set_product_featured,
    update_product,
)
from app.services.admin_dashboard import get_admin_dashboard


router = Router()


# ==========================================================
# SECURITY
# ==========================================================


def is_admin(user_id: int | None) -> bool:
    if user_id is None:
        return False

    return (
        settings.admin_id != 0
        and user_id == settings.admin_id
    )


# ==========================================================
# HELPERS
# ==========================================================


def format_price(value) -> str:
    try:
        number = Decimal(str(value))
        return f"{number:,.0f}"
    except Exception:
        return str(value)


def parse_id(callback: CallbackQuery) -> int | None:
    try:
        return int(
            callback.data.split(":")[-1]
        )
    except (AttributeError, ValueError):
        return None


def condition_text(value) -> str:
    text = str(value).upper()

    if "USED" in text or "کارکرده" in text:
        return "کارکرده"

    return "نو"


def product_title(product) -> str:
    return (
        f"{product.brand} {product.model}"
    ).strip()


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
                )
            ],
            [
                InlineKeyboardButton(
                    text="📱 مدیریت محصولات",
                    callback_data="admin:products",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📦 مدیریت موجودی",
                    callback_data="admin:inventory",
                ),
                InlineKeyboardButton(
                    text="🛒 سفارش‌ها",
                    callback_data="admin:orders",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 مشتریان",
                    callback_data="admin:customers",
                ),
                InlineKeyboardButton(
                    text="💰 قیمت‌ها",
                    callback_data="admin:prices",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📈 آمار فروش",
                    callback_data="admin:stats",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data="home",
                )
            ],
        ]
    )


def admin_products_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="➕ افزودن محصول",
                    callback_data="admin:product:add",
                )
            ],
            [
                InlineKeyboardButton(
                    text="📋 لیست محصولات",
                    callback_data="admin:product:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⭐ محصولات ویژه",
                    callback_data="admin:product:featured",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 پنل مدیریت",
                    callback_data="admin:panel",
                )
            ],
        ]
    )


# ==========================================================
# PRODUCT VIEW KEYBOARD
# ==========================================================


def product_admin_keyboard(
    product_id: int,
    is_active: bool,
    is_featured: bool,
) -> InlineKeyboardMarkup:
    active_text = (
        "🔴 غیرفعال کردن"
        if is_active
        else "🟢 فعال کردن"
    )

    active_action = (
        "deactivate"
        if is_active
        else "activate"
    )

    featured_text = (
        "☆ حذف از ویژه"
        if is_featured
        else "⭐ ویژه کردن"
    )

    featured_action = (
        "unfeatured"
        if is_featured
        else "featured"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ ویرایش محصول",
                    callback_data=(
                        f"admin:product:edit:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=active_text,
                    callback_data=(
                        f"admin:product:{active_action}:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=featured_text,
                    callback_data=(
                        f"admin:product:{featured_action}:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 غیرفعال‌سازی",
                    callback_data=(
                        f"admin:product:delete:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 لیست محصولات",
                    callback_data="admin:product:list",
                )
            ],
        ]
    )


# ==========================================================
# ADMIN PANEL
# ==========================================================


@router.message(Command("admin"))
async def admin_command(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "⛔ دسترسی غیرمجاز."
        )
        return

    await message.answer(
        "⚙️ پنل مدیریت VIRA MOBILE\n\n"
        "به بخش مدیریت خوش آمدید.",
        reply_markup=admin_menu(),
    )


@router.callback_query(F.data == "admin:panel")
async def admin_panel(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "⚙️ پنل مدیریت VIRA MOBILE\n\n"
        "بخش موردنظر را انتخاب کنید:",
        reply_markup=admin_menu(),
    )

    await callback.answer()


# ==========================================================
# DASHBOARD
# ==========================================================


@router.callback_query(F.data == "admin:dashboard")
async def admin_dashboard(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        try:
            dashboard = await get_admin_dashboard(
                session
            )

            await callback.message.edit_text(
                "📊 داشبورد مدیریت\n\n"
                f"📱 محصولات: "
                f"{dashboard.get('products', 0)}\n"
                f"🟢 محصولات فعال: "
                f"{dashboard.get('active_products', 0)}\n"
                f"⭐ محصولات ویژه: "
                f"{dashboard.get('featured_products', 0)}\n"
                f"📦 موجودی: "
                f"{dashboard.get('inventory', 0)}\n"
                f"🛒 سفارش‌ها: "
                f"{dashboard.get('orders', 0)}\n"
                f"👥 مشتریان: "
                f"{dashboard.get('customers', 0)}",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔄 بروزرسانی",
                                callback_data="admin:dashboard",
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text="🔙 پنل مدیریت",
                                callback_data="admin:panel",
                            )
                        ],
                    ]
                ),
            )

        except Exception:
            await callback.message.edit_text(
                "❌ دریافت اطلاعات داشبورد با خطا مواجه شد.",
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

    await callback.answer()


# ==========================================================
# PRODUCTS MENU
# ==========================================================


@router.callback_query(F.data == "admin:products")
async def admin_products(callback: CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📱 مدیریت محصولات\n\n"
        "عملیات موردنظر را انتخاب کنید:",
        reply_markup=admin_products_menu(),
    )

    await callback.answer()


# ==========================================================
# CREATE PRODUCT FSM
# ==========================================================


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


@router.callback_query(F.data == "admin:product:add")
async def admin_product_add(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        ProductCreateStates.sku
    )

    await callback.message.edit_text(
        "➕ افزودن محصول\n\n"
        "مرحله ۱ از ۹\n\n"
        "SKU محصول را وارد کنید:"
    )

    await callback.answer()


@router.message(ProductCreateStates.sku)
async def product_create_sku(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if not value:
        await message.answer(
            "❌ SKU نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        sku=value
    )

    await state.set_state(
        ProductCreateStates.brand
    )

    await message.answer(
        "مرحله ۲ از ۹\n\n"
        "برند محصول را وارد کنید:"
    )


@router.message(ProductCreateStates.brand)
async def product_create_brand(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if not value:
        await message.answer(
            "❌ برند نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        brand=value
    )

    await state.set_state(
        ProductCreateStates.model
    )

    await message.answer(
        "مرحله ۳ از ۹\n\n"
        "مدل محصول را وارد کنید:"
    )


@router.message(ProductCreateStates.model)
async def product_create_model(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if not value:
        await message.answer(
            "❌ مدل نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        model=value
    )

    await state.set_state(
        ProductCreateStates.category
    )

    await message.answer(
        "مرحله ۴ از ۹\n\n"
        "دسته‌بندی را وارد کنید.\n\n"
        "مثال:\n"
        "iphone\n"
        "samsung\n"
        "xiaomi\n"
        "other\n"
        "used"
    )


@router.message(ProductCreateStates.category)
async def product_create_category(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if not value:
        await message.answer(
            "❌ دسته‌بندی نمی‌تواند خالی باشد."
        )
        return

    await state.update_data(
        category=value
    )

    await state.set_state(
        ProductCreateStates.condition
    )

    await message.answer(
        "مرحله ۵ از ۹\n\n"
        "وضعیت محصول را وارد کنید:\n\n"
        "NEW = نو\n"
        "USED = کارکرده"
    )


@router.message(ProductCreateStates.condition)
async def product_create_condition(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip().upper()

    if value not in {"NEW", "USED"}:
        await message.answer(
            "❌ فقط یکی از این دو مقدار را وارد کنید:\n\n"
            "NEW\n"
            "USED"
        )
        return

    await state.update_data(
        condition=value
    )

    await state.set_state(
        ProductCreateStates.price
    )

    await message.answer(
        "مرحله ۶ از ۹\n\n"
        "قیمت محصول را به تومان وارد کنید.\n\n"
        "مثال:\n"
        "42500000"
    )


@router.message(ProductCreateStates.price)
async def product_create_price(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    raw = (
        message.text
        .strip()
        .replace(",", "")
        .replace("٬", "")
        .replace("،", "")
    )

    try:
        price = Decimal(raw)

        if price < 0:
            raise ValueError

    except (InvalidOperation, ValueError):
        await message.answer(
            "❌ قیمت معتبر نیست.\n\n"
            "مثال صحیح:\n"
            "42500000"
        )
        return

    await state.update_data(
        price=str(price)
    )

    await state.set_state(
        ProductCreateStates.short_description
    )

    await message.answer(
        "مرحله ۷ از ۹\n\n"
        "توضیح کوتاه محصول را وارد کنید.\n\n"
        "اگر نمی‌خواهید، بنویسید:\n"
        "ندارد"
    )


@router.message(ProductCreateStates.short_description)
async def product_create_short_description(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if value == "ندارد":
        value = ""

    await state.update_data(
        short_description=value
    )

    await state.set_state(
        ProductCreateStates.description
    )

    await message.answer(
        "مرحله ۸ از ۹\n\n"
        "توضیحات کامل محصول را وارد کنید.\n\n"
        "اگر نمی‌خواهید، بنویسید:\n"
        "ندارد"
    )


@router.message(ProductCreateStates.description)
async def product_create_description(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    value = message.text.strip()

    if value == "ندارد":
        value = ""

    await state.update_data(
        description=value
    )

    await state.set_state(
        ProductCreateStates.image
    )

    await message.answer(
        "مرحله ۹ از ۹\n\n"
        "تصویر محصول را ارسال کنید.\n\n"
        "اگر تصویر ندارید، بنویسید:\n"
        "ندارد"
    )


@router.message(ProductCreateStates.image)
async def product_create_image(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    image_file_id = None

    if message.photo:
        image_file_id = (
            message.photo[-1].file_id
        )

    elif message.text:
        value = message.text.strip()

        if value != "ندارد":
            image_file_id = value

    if not image_file_id:
        await state.update_data(
            image_url=None
        )
    else:
        await state.update_data(
            image_url=image_file_id
        )

    data = await state.get_data()

    condition = data["condition"]

    preview = (
        "📋 پیش‌نمایش محصول\n\n"
        f"🆔 SKU: {data['sku']}\n"
        f"🏷 برند: {data['brand']}\n"
        f"📱 مدل: {data['model']}\n"
        f"📂 دسته‌بندی: {data['category']}\n"
        f"📦 وضعیت: {condition_text(condition)}\n"
        f"💰 قیمت: {format_price(data['price'])} تومان\n"
        f"📝 توضیح کوتاه: "
        f"{data.get('short_description') or 'ندارد'}\n"
        f"📄 توضیحات: "
        f"{data.get('description') or 'ندارد'}\n"
        f"🖼 تصویر: "
        f"{'دارد' if data.get('image_url') else 'ندارد'}"
    )

    await message.answer(
        preview,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✅ ثبت محصول",
                        callback_data="admin:product:create:confirm",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ لغو",
                        callback_data="admin:product:create:cancel",
                    )
                ],
            ]
        ),
    )


@router.callback_query(
    F.data == "admin:product:create:confirm"
)
async def product_create_confirm(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    data = await state.get_data()

    async with AsyncSessionLocal() as session:
        try:
            product = await create_product(
                session,
                sku=data["sku"],
                brand=data["brand"],
                model=data["model"],
                category=data["category"],
                condition=data["condition"],
                base_price=data["price"],
                short_description=data.get(
                    "short_description"
                ),
                description=data.get(
                    "description"
                ),
                image_url=data.get(
                    "image_url"
                ),
            )

        except ValueError as exc:
            await callback.message.edit_text(
                f"❌ {exc}\n\n"
                "محصول ثبت نشد."
            )
            await state.clear()
            await callback.answer()
            return

        except Exception:
            await session.rollback()

            await callback.message.edit_text(
                "❌ هنگام ثبت محصول خطایی رخ داد."
            )
            await state.clear()
            await callback.answer()
            return

    await state.clear()

    await callback.message.edit_text(
        "✅ محصول با موفقیت ثبت شد.\n\n"
        f"📱 {product_title(product)}\n"
        f"🆔 SKU: {product.sku}\n"
        f"💰 {format_price(product.base_price)} تومان",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="✏️ ویرایش محصول",
                        callback_data=(
                            f"admin:product:edit:{product.id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 لیست محصولات",
                        callback_data="admin:product:list",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت محصولات",
                        callback_data="admin:products",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data == "admin:product:create:cancel"
)
async def product_create_cancel(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_text(
        "❌ عملیات افزودن محصول لغو شد.",
        reply_markup=admin_products_menu(),
    )

    await callback.answer()


# ==========================================================
# PRODUCT LIST
# ==========================================================


@router.callback_query(F.data == "admin:product:list")
async def admin_product_list(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        products = await get_admin_products(
            session,
            limit=50,
        )

    if not products:
        await callback.message.edit_text(
            "📋 لیست محصولات\n\n"
            "هنوز محصولی ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="➕ افزودن محصول",
                            callback_data="admin:product:add",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت محصولات",
                            callback_data="admin:products",
                        )
                    ],
                ]
            ),
        )

        await callback.answer()
        return

    rows = []

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

        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"{status} "
                        f"{product.brand} "
                        f"{product.model}"
                        f"{featured}"
                    ),
                    callback_data=(
                        f"admin:product:view:{product.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="➕ افزودن محصول",
                callback_data="admin:product:add",
            )
        ]
    )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 مدیریت محصولات",
                callback_data="admin:products",
            )
        ]
    )

    await callback.message.edit_text(
        f"📋 لیست محصولات\n\n"
        f"تعداد: {len(products)}\n\n"
        "برای مشاهده جزئیات روی محصول بزنید:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


# ==========================================================
# PRODUCT VIEW
# ==========================================================


@router.callback_query(
    F.data.startswith("admin:product:view:")
)
async def admin_product_view(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await get_product(
            session,
            product_id,
        )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
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
        else "☆ خیر"
    )

    text = (
        "📱 اطلاعات محصول\n\n"
        f"🆔 ID: {product.id}\n"
        f"🏷 SKU: {product.sku}\n"
        f"📱 محصول: {product_title(product)}\n"
        f"🏭 برند: {product.brand}\n"
        f"📂 دسته‌بندی: {product.category}\n"
        f"📦 وضعیت: "
        f"{condition_text(product.condition)}\n"
        f"💰 قیمت: "
        f"{format_price(product.base_price)} تومان\n"
        f"🔘 وضعیت فروش: {status}\n"
        f"⭐ ویژه: {featured}\n\n"
        f"📝 توضیح کوتاه:\n"
        f"{product.short_description or 'ندارد'}"
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_admin_keyboard(
            product.id,
            product.is_active,
            product.is_featured,
        ),
    )

    await callback.answer()


# ==========================================================
# EDIT PRODUCT FSM
# ==========================================================


class ProductEditStates(StatesGroup):
    value = State()


EDITABLE_FIELDS = {
    "sku": "SKU",
    "brand": "برند",
    "model": "مدل",
    "category": "دسته‌بندی",
    "condition": "وضعیت",
    "price": "قیمت",
    "short_description": "توضیح کوتاه",
    "description": "توضیحات",
    "image": "تصویر",
}


def edit_fields_keyboard(
    product_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🏷 SKU",
                    callback_data=(
                        f"admin:product:editfield:sku:{product_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="🏭 برند",
                    callback_data=(
                        f"admin:product:editfield:brand:{product_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 مدل",
                    callback_data=(
                        f"admin:product:editfield:model:{product_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="📂 دسته‌بندی",
                    callback_data=(
                        f"admin:product:editfield:category:{product_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📦 وضعیت",
                    callback_data=(
                        f"admin:product:editfield:condition:{product_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text="💰 قیمت",
                    callback_data=(
                        f"admin:product:editfield:price:{product_id}"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📝 توضیح کوتاه",
                    callback_data=(
                        f"admin:product:editfield:short_description:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="📄 توضیحات کامل",
                    callback_data=(
                        f"admin:product:editfield:description:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 تصویر",
                    callback_data=(
                        f"admin:product:editfield:image:{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=(
                        f"admin:product:view:{product_id}"
                    ),
                )
            ],
        ]
    )


@router.callback_query(
    F.data.startswith("admin:product:edit:")
)
async def admin_product_edit(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await get_product(
            session,
            product_id,
        )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await state.clear()

    await callback.message.edit_text(
        "✏️ ویرایش محصول\n\n"
        f"📱 {product_title(product)}\n"
        f"🏷 SKU: {product.sku}\n\n"
        "فیلدی که می‌خواهید تغییر دهید را انتخاب کنید:",
        reply_markup=edit_fields_keyboard(
            product_id
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith("admin:product:editfield:")
)
async def admin_product_edit_field(
    callback: CallbackQuery,
    state: FSMContext,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    parts = callback.data.split(":")

    if len(parts) != 5:
        await callback.answer(
            "اطلاعات ویرایش نامعتبر است.",
            show_alert=True,
        )
        return

    field = parts[3]

    try:
        product_id = int(parts[4])
    except ValueError:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    if field not in EDITABLE_FIELDS:
        await callback.answer(
            "فیلد نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await get_product(
            session,
            product_id,
        )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await state.clear()

    await state.set_state(
        ProductEditStates.value
    )

    await state.update_data(
        product_id=product_id,
        field=field,
    )

    current_value = ""

    if field == "sku":
        current_value = product.sku
    elif field == "brand":
        current_value = product.brand
    elif field == "model":
        current_value = product.model
    elif field == "category":
        current_value = product.category
    elif field == "condition":
        current_value = condition_text(
            product.condition
        )
    elif field == "price":
        current_value = (
            format_price(product.base_price)
        )
    elif field == "short_description":
        current_value = (
            product.short_description
            or "ندارد"
        )
    elif field == "description":
        current_value = (
            product.description
            or "ندارد"
        )
    elif field == "image":
        current_value = (
            "دارد"
            if product.image_url
            else "ندارد"
        )

    instruction = (
        f"✏️ ویرایش {EDITABLE_FIELDS[field]}\n\n"
        f"مقدار فعلی:\n"
        f"{current_value}\n\n"
    )

    if field == "condition":
        instruction += (
            "مقدار جدید را وارد کنید:\n"
            "NEW = نو\n"
            "USED = کارکرده"
        )

    elif field == "price":
        instruction += (
            "قیمت جدید را به تومان وارد کنید.\n\n"
            "مثال:\n"
            "45000000"
        )

    elif field == "image":
        instruction += (
            "تصویر جدید را ارسال کنید.\n\n"
            "یا اگر می‌خواهید تصویر حذف شود، "
            "بنویسید:\n"
            "حذف"
        )

    else:
        instruction += (
            "مقدار جدید را ارسال کنید.\n\n"
            "برای لغو، بنویسید:\n"
            "لغو"
        )

    await callback.message.edit_text(
        instruction
    )

    await callback.answer()


@router.message(ProductEditStates.value)
async def admin_product_edit_value(
    message: Message,
    state: FSMContext,
):
    if not is_admin(message.from_user.id):
        return

    data = await state.get_data()

    product_id = data.get("product_id")
    field = data.get("field")

    if not product_id or not field:
        await state.clear()

        await message.answer(
            "❌ جلسه ویرایش منقضی شده است."
        )
        return

    # ------------------------------------------------------
    # Cancel
    # ------------------------------------------------------

    if message.text:
        text = message.text.strip()

        if text == "لغو":
            await state.clear()

            await message.answer(
                "❌ ویرایش لغو شد.",
                reply_markup=InlineKeyboardMarkup(
                    inline_keyboard=[
                        [
                            InlineKeyboardButton(
                                text="🔙 محصول",
                                callback_data=(
                                    f"admin:product:view:{product_id}"
                                ),
                            )
                        ]
                    ]
                ),
            )
            return

    # ------------------------------------------------------
    # Image
    # ------------------------------------------------------

    if field == "image":
        if message.photo:
            value = (
                message.photo[-1].file_id
            )
        elif message.text:
            if message.text.strip() == "حذف":
                value = ""
            else:
                value = message.text.strip()
        else:
            await message.answer(
                "❌ تصویر معتبر نیست."
            )
            return

    else:
        if not message.text:
            await message.answer(
                "❌ لطفاً مقدار را به‌صورت متنی ارسال کنید."
            )
            return

        value = message.text.strip()

        if not value:
            await message.answer(
                "❌ مقدار نمی‌تواند خالی باشد."
            )
            return

    # ------------------------------------------------------
    # Normalize condition
    # ------------------------------------------------------

    if field == "condition":
        value = value.upper()

        if value in {"نو", "NEW"}:
            value = "NEW"

        elif value in {"کارکرده", "USED"}:
            value = "USED"

        else:
            await message.answer(
                "❌ وضعیت نامعتبر است.\n\n"
                "فقط:\n"
                "NEW\n"
                "USED"
            )
            return

    # ------------------------------------------------------
    # Normalize price
    # ------------------------------------------------------

    if field == "price":
        normalized = (
            value
            .replace(",", "")
            .replace("٬", "")
            .replace("،", "")
            .replace("تومان", "")
            .replace("تومن", "")
            .strip()
        )

        try:
            price = Decimal(normalized)

            if price < 0:
                raise ValueError

        except (InvalidOperation, ValueError):
            await message.answer(
                "❌ قیمت معتبر نیست.\n\n"
                "مثال:\n"
                "45000000"
            )
            return

        value = str(price)

    # ------------------------------------------------------
    # Update
    # ------------------------------------------------------

    async with AsyncSessionLocal() as session:
        try:
            kwargs = {}

            if field == "sku":
                kwargs["sku"] = value

            elif field == "brand":
                kwargs["brand"] = value

            elif field == "model":
                kwargs["model"] = value

            elif field == "category":
                kwargs["category"] = value

            elif field == "condition":
                kwargs["condition"] = value

            elif field == "price":
                kwargs["base_price"] = value

            elif field == "short_description":
                kwargs["short_description"] = value

            elif field == "description":
                kwargs["description"] = value

            elif field == "image":
                kwargs["image_url"] = value or None

            product, price_changed = (
                await update_product(
                    session,
                    product_id,
                    **kwargs,
                )
            )

            if product is None:
                await state.clear()

                await message.answer(
                    "❌ محصول پیدا نشد."
                )
                return

        except ValueError as exc:
            await message.answer(
                f"❌ {exc}"
            )
            return

        except Exception:
            await session.rollback()

            await message.answer(
                "❌ هنگام ذخیره تغییرات خطایی رخ داد."
            )
            return

    await state.clear()

    price_message = ""

    if field == "price" and price_changed:
        price_message = (
            "\n\n📈 تغییر قیمت ثبت شد و "
            "در تاریخچه قیمت ذخیره گردید."
        )

    await message.answer(
        "✅ تغییرات با موفقیت ذخیره شد.\n\n"
        f"📱 {product_title(product)}\n"
        f"✏️ فیلد تغییر یافته: "
        f"{EDITABLE_FIELDS[field]}"
        f"{price_message}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مشاهده محصول",
                        callback_data=(
                            f"admin:product:view:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="✏️ ادامه ویرایش",
                        callback_data=(
                            f"admin:product:edit:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 مدیریت محصولات",
                        callback_data="admin:products",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# ACTIVE / INACTIVE
# ==========================================================


@router.callback_query(
    F.data.startswith("admin:product:activate:")
)
async def admin_product_activate(
    callback: CallbackQuery,
):
    await _set_active(
        callback,
        True,
    )


@router.callback_query(
    F.data.startswith("admin:product:deactivate:")
)
async def admin_product_deactivate(
    callback: CallbackQuery,
):
    await _set_active(
        callback,
        False,
    )


async def _set_active(
    callback: CallbackQuery,
    active: bool,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await set_product_active(
            session,
            product_id,
            active,
        )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "✅ وضعیت محصول تغییر کرد.\n\n"
        f"📱 {product_title(product)}\n"
        f"وضعیت جدید: "
        f"{'🟢 فعال' if active else '🔴 غیرفعال'}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مشاهده محصول",
                        callback_data=(
                            f"admin:product:view:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 لیست محصولات",
                        callback_data="admin:product:list",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


# ==========================================================
# FEATURED / UNFEATURED
# ==========================================================


@router.callback_query(
    F.data.startswith("admin:product:featured:")
)
async def admin_product_featured_toggle(
    callback: CallbackQuery,
):
    await _set_featured(
        callback,
        True,
    )


@router.callback_query(
    F.data.startswith("admin:product:unfeatured:")
)
async def admin_product_unfeatured_toggle(
    callback: CallbackQuery,
):
    await _set_featured(
        callback,
        False,
    )


async def _set_featured(
    callback: CallbackQuery,
    featured: bool,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await set_product_featured(
            session,
            product_id,
            featured,
        )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "✅ وضعیت ویژه محصول تغییر کرد.\n\n"
        f"📱 {product_title(product)}\n"
        f"وضعیت جدید: "
        f"{'⭐ ویژه' if featured else '☆ عادی'}",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مشاهده محصول",
                        callback_data=(
                            f"admin:product:view:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 لیست محصولات",
                        callback_data="admin:product:list",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


# ==========================================================
# SAFE DELETE / DEACTIVATE
# ==========================================================


@router.callback_query(
    F.data.startswith("admin:product:delete:")
)
async def admin_product_delete(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "⚠️ غیرفعال‌سازی محصول\n\n"
        "محصول به‌صورت فیزیکی از دیتابیس حذف نمی‌شود.\n"
        "فقط از فروش خارج خواهد شد.\n\n"
        "این روش برای حفظ سوابق سفارش‌ها و موجودی امن‌تر است.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔴 تأیید غیرفعال‌سازی",
                        callback_data=(
                            f"admin:product:delete_confirm:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="❌ انصراف",
                        callback_data=(
                            f"admin:product:view:{product_id}"
                        ),
                    )
                ],
            ]
        ),
    )

    await callback.answer()


@router.callback_query(
    F.data.startswith(
        "admin:product:delete_confirm:"
    )
)
async def admin_product_delete_confirm(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    product_id = parse_id(callback)

    if product_id is None:
        await callback.answer(
            "شناسه محصول نامعتبر است.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        product = await set_product_active(
            session,
            product_id,
            False,
        )

        if product is not None:
            product = await set_product_featured(
                session,
                product_id,
                False,
            )

    if product is None:
        await callback.answer(
            "محصول پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🔴 محصول غیرفعال شد.\n\n"
        f"📱 {product_title(product)}\n"
        "این محصول از فروش خارج شده ولی "
        "اطلاعات آن در دیتابیس باقی مانده است.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🟢 فعال‌سازی مجدد",
                        callback_data=(
                            f"admin:product:activate:{product_id}"
                        ),
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="📋 لیست محصولات",
                        callback_data="admin:product:list",
                    )
                ],
            ]
        ),
    )

    await callback.answer()


# ==========================================================
# FEATURED PRODUCTS
# ==========================================================


@router.callback_query(
    F.data == "admin:product:featured"
)
async def admin_product_featured(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    async with AsyncSessionLocal() as session:
        products = await get_admin_products(
            session,
            limit=100,
        )

    featured_products = [
        product
        for product in products
        if product.is_featured
    ]

    if not featured_products:
        await callback.message.edit_text(
            "⭐ محصولات ویژه\n\n"
            "در حال حاضر محصول ویژه‌ای ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 لیست محصولات",
                            callback_data="admin:product:list",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🔙 مدیریت محصولات",
                            callback_data="admin:products",
                        )
                    ],
                ]
            ),
        )

        await callback.answer()
        return

    rows = []

    for product in featured_products:
        rows.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"⭐ {product.brand} "
                        f"{product.model}"
                    ),
                    callback_data=(
                        f"admin:product:view:{product.id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="🔙 مدیریت محصولات",
                callback_data="admin:products",
            )
        ]
    )

    await callback.message.edit_text(
        "⭐ محصولات ویژه\n\n"
        f"تعداد: {len(featured_products)}\n\n"
        "محصول موردنظر را انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
    )

    await callback.answer()


# ==========================================================
# OTHER ADMIN SECTIONS
# ==========================================================


@router.callback_query(
    F.data == "admin:inventory"
)
async def admin_inventory(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📦 مدیریت موجودی\n\n"
        "این بخش در مرحله بعد به Variant و "
        "Inventory متصل می‌شود.",
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

    await callback.answer()


@router.callback_query(
    F.data == "admin:orders"
)
async def admin_orders(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "🛒 مدیریت سفارش‌ها\n\n"
        "این بخش در مرحله بعد تکمیل می‌شود.",
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

    await callback.answer()


@router.callback_query(
    F.data == "admin:customers"
)
async def admin_customers(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "👥 مشتریان\n\n"
        "این بخش در مرحله بعد تکمیل می‌شود.",
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

    await callback.answer()


@router.callback_query(
    F.data == "admin:prices"
)
async def admin_prices(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "💰 مدیریت قیمت‌ها\n\n"
        "تاریخچه تغییر قیمت‌ها در CRUD محصولات "
        "ثبت می‌شود.\n\n"
        "گزارش کامل قیمت‌ها در مرحله بعد اضافه می‌شود.",
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

    await callback.answer()


@router.callback_query(
    F.data == "admin:stats"
)
async def admin_stats(
    callback: CallbackQuery,
):
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        "📈 آمار فروش\n\n"
        "سیستم آمار فروش پس از تکمیل سفارش‌ها "
        "و موجودی فعال خواهد شد.",
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

    await callback.answer()
