from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.config import settings
from app.database.connection import AsyncSessionLocal
from app.database.models import Product
from app.services.products import (
    get_active_product_by_id,
    get_products,
    get_products_by_category,
    search_products,
)

router = Router()

# ==========================================================
# SETTINGS
# ==========================================================

PRODUCT_LIMIT = 30


# ==========================================================
# HELPERS
# ==========================================================

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


def format_price(value) -> str:
    """
    Format product price for Telegram.
    """
    if value is None:
        return "تماس برای قیمت"

    try:
        price = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return "تماس برای قیمت"

    if price <= 0:
        return "تماس برای قیمت"

    return f"{price:,.0f} تومان"


def parse_callback_id(callback_data: str | None) -> int | None:
    """
    Safely extract integer ID from callback data.
    """
    if not callback_data:
        return None

    try:
        value = callback_data.split(":", 1)[1]
        return int(value)
    except (IndexError, ValueError, TypeError):
        return None


def condition_text(condition) -> str:
    """
    Convert product condition to Persian text.
    """
    value = getattr(condition, "value", condition)

    if value in ("new", "NEW"):
        return "نو"

    if value in ("used", "USED"):
        return "کارکرده"

    return str(value or "نامشخص")


# ==========================================================
# BOTTOM REPLY KEYBOARD
# ==========================================================

def bottom_menu(user_id: int | None = None) -> ReplyKeyboardMarkup:
    """
    Persistent Telegram Reply Keyboard shown at the bottom
    of the chat.

    Admin panel button is visible only for the configured admin.
    """

    keyboard = [
        [
            KeyboardButton(text="📱 فروشگاه"),
            KeyboardButton(text="🔎 جستجو"),
        ],
        [
            KeyboardButton(text="🧠 مشاور خرید"),
            KeyboardButton(text="⚖️ مقایسه"),
        ],
        [
            KeyboardButton(text="💰 قیمت‌ها"),
            KeyboardButton(text="🔄 تعویض گوشی"),
        ],
        [
            KeyboardButton(text="💳 خرید اقساطی"),
            KeyboardButton(text="🛒 سبد خرید"),
        ],
        [
            KeyboardButton(text="👤 حساب کاربری"),
            KeyboardButton(text="📦 سفارش‌های من"),
        ],
    ]

    # ------------------------------------------------------
    # ADMIN BUTTON
    # ------------------------------------------------------

    if is_admin(user_id):
        keyboard.append(
            [
                KeyboardButton(text="⚙️ پنل مدیریت"),
            ]
        )

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="یک گزینه را انتخاب کنید...",
    )


# ==========================================================
# MAIN INLINE MENU
# ==========================================================

def main_menu(
    user_id: int | None = None,
) -> InlineKeyboardMarkup:
    """
    Main VIRA MOBILE inline menu.
    Admin panel is visible only to the configured admin.
    """

    keyboard = [
        [
            InlineKeyboardButton(
                text="📱 فروشگاه موبایل",
                callback_data="shop",
            ),
            InlineKeyboardButton(
                text="🔎 جستجوی گوشی",
                callback_data="search",
            ),
        ],
        [
            InlineKeyboardButton(
                text="🧠 مشاور خرید",
                callback_data="advisor",
            ),
            InlineKeyboardButton(
                text="⚖️ مقایسه گوشی",
                callback_data="compare",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💰 قیمت‌ها",
                callback_data="prices",
            ),
            InlineKeyboardButton(
                text="🔄 تعویض گوشی",
                callback_data="tradein",
            ),
        ],
        [
            InlineKeyboardButton(
                text="💳 خرید اقساطی",
                callback_data="installment",
            ),
            InlineKeyboardButton(
                text="🛒 سبد خرید",
                callback_data="cart",
            ),
        ],
        [
            InlineKeyboardButton(
                text="👤 حساب کاربری",
                callback_data="profile",
            ),
            InlineKeyboardButton(
                text="📦 سفارش‌های من",
                callback_data="orders",
            ),
        ],
    ]

    # ------------------------------------------------------
    # ADMIN BUTTON
    # ------------------------------------------------------

    if is_admin(user_id):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# ==========================================================
# SHOP MENU
# ==========================================================

def shop_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🍎 آیفون",
                    callback_data="category:iphone",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📱 سامسونگ",
                    callback_data="category:samsung",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔵 شیائومی",
                    callback_data="category:xiaomi",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="📲 سایر برندها",
                    callback_data="category:other",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="♻️ گوشی‌های کارکرده",
                    callback_data="category:used",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔥 محصولات ویژه",
                    callback_data="featured",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 منوی اصلی",
                    callback_data="home",
                ),
            ],
        ]
    )


# ==========================================================
# PRODUCT LIST KEYBOARD
# ==========================================================

def product_list_keyboard(
    products: list[Product],
    back_callback: str = "shop",
) -> InlineKeyboardMarkup:

    buttons: list[list[InlineKeyboardButton]] = []

    for product in products:
        buttons.append(
            [
                InlineKeyboardButton(
                    text=(
                        f"📱 {product.brand} "
                        f"{product.model}"
                    ),
                    callback_data=f"product:{product.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="🔙 بازگشت",
                callback_data=back_callback,
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=buttons
    )


# ==========================================================
# PRODUCT DETAIL KEYBOARD
# ==========================================================

def product_detail_keyboard(
    product_id: int,
    back_callback: str = "shop",
) -> InlineKeyboardMarkup:

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🛒 افزودن به سبد خرید",
                    callback_data=f"cart:add:{product_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❤️ علاقه‌مندی",
                    callback_data=f"favorite:{product_id}",
                ),
                InlineKeyboardButton(
                    text="⚖️ مقایسه",
                    callback_data=f"compare:add:{product_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔔 اطلاع از کاهش قیمت",
                    callback_data=f"alert:{product_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔙 بازگشت",
                    callback_data=back_callback,
                ),
            ],
        ]
    )


# ==========================================================
# EMPTY / ERROR KEYBOARDS
# ==========================================================

def home_keyboard(
    user_id: int | None = None,
) -> InlineKeyboardMarkup:

    keyboard = [
        [
            InlineKeyboardButton(
                text="🏠 منوی اصلی",
                callback_data="home",
            )
        ]
    ]

    if is_admin(user_id):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


def shop_back_keyboard(
    user_id: int | None = None,
) -> InlineKeyboardMarkup:

    keyboard = [
        [
            InlineKeyboardButton(
                text="🔙 فروشگاه",
                callback_data="shop",
            )
        ],
        [
            InlineKeyboardButton(
                text="🏠 منوی اصلی",
                callback_data="home",
            )
        ],
    ]

    if is_admin(user_id):
        keyboard.append(
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=keyboard
    )


# ==========================================================
# START
# ==========================================================

@router.message(CommandStart())
async def start_handler(message: Message):

    user = message.from_user

    name = (
        user.first_name
        if user and user.first_name
        else "دوست عزیز"
    )

    user_id = user.id if user else None

    text = (
        f"سلام {name} 👋\n\n"
        "به ربات رسمی VIRA MOBILE خوش آمدی 📱\n\n"
        "اینجا می‌تونی:\n"
        "• گوشی مناسب بودجه‌ات رو پیدا کنی\n"
        "• گوشی‌ها رو مقایسه کنی\n"
        "• قیمت محصولات رو ببینی\n"
        "• برای خرید مشاوره بگیری\n"
        "• سفارش ثبت و پیگیری کنی\n"
        "• گوشی خودت رو برای تعویض اعلام کنی\n\n"
        "از منوی پایین یا منوی اصلی شروع کن 👇"
    )

    await message.answer(
        text,
        reply_markup=bottom_menu(user_id),
    )

    await message.answer(
        "📱 منوی اصلی VIRA MOBILE",
        reply_markup=main_menu(user_id),
    )


# ==========================================================
# MENU
# ==========================================================

@router.message(Command("menu"))
async def menu_handler(message: Message):

    user = message.from_user

    user_id = user.id if user else None

    await message.answer(
        "📱 منوی اصلی VIRA MOBILE",
        reply_markup=bottom_menu(user_id),
    )

    await message.answer(
        "گزینه موردنظر را انتخاب کن 👇",
        reply_markup=main_menu(user_id),
    )


# ==========================================================
# HELP
# ==========================================================

@router.message(Command("help"))
async def help_handler(message: Message):

    user_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    await message.answer(
        "راهنمای VIRA MOBILE\n\n"
        "/start - شروع کار\n"
        "/menu - منوی اصلی\n"
        "/help - راهنما\n\n"
        "برای خرید یا مشاوره از منوی اصلی یا "
        "کیبورد پایین استفاده کن.",
        reply_markup=bottom_menu(user_id),
    )


# ==========================================================
# BOTTOM KEYBOARD: SHOP
# ==========================================================

@router.message(
    lambda message: (
        message.text == "📱 فروشگاه"
    )
)
async def bottom_shop_handler(
    message: Message,
):

    await message.answer(
        "📱 فروشگاه VIRA MOBILE\n\n"
        "دسته‌بندی محصولات را انتخاب کن 👇",
        reply_markup=shop_menu(),
    )


# ==========================================================
# BOTTOM KEYBOARD: SEARCH
# ==========================================================

@router.message(
    lambda message: (
        message.text == "🔎 جستجو"
    )
)
async def bottom_search_handler(
    message: Message,
):

    await message.answer(
        "🔎 جستجوی گوشی\n\n"
        "نام برند یا مدل گوشی را ارسال کن.\n\n"
        "مثال:\n"
        "iPhone 15\n"
        "Samsung S24\n"
        "Xiaomi Redmi",
        reply_markup=home_keyboard(
            message.from_user.id
            if message.from_user
            else None
        ),
    )


# ==========================================================
# BOTTOM KEYBOARD: ADVISOR
# ==========================================================

@router.message(
    lambda message: (
        message.text == "🧠 مشاور خرید"
    )
)
async def bottom_advisor_handler(
    message: Message,
):

    user_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    await message.answer(
        "🧠 مشاور خرید VIRA MOBILE\n\n"
        "در این بخش بر اساس بودجه، کاربرد، دوربین، "
        "باتری، بازی و نیازت بهترین گزینه‌ها پیشنهاد می‌شوند.",
        reply_markup=home_keyboard(user_id),
    )


# ==========================================================
# BOTTOM KEYBOARD: COMPARE
# ==========================================================

@router.message(
    lambda message: (
        message.text == "⚖️ مقایسه"
    )
)
async def bottom_compare_handler(
    message: Message,
):

    await message.answer(
        "⚖️ مقایسه گوشی‌ها\n\n"
        "ابتدا محصولات موردنظر را انتخاب کن.\n"
        "سیستم مقایسه مشخصات فنی، قیمت و ارزش خرید "
        "را کنار هم نمایش خواهد داد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 رفتن به فروشگاه",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# BOTTOM KEYBOARD: PRICES
# ==========================================================

@router.message(
    lambda message: (
        message.text == "💰 قیمت‌ها"
    )
)
async def bottom_prices_handler(
    message: Message,
):

    await message.answer(
        "💰 قیمت‌های VIRA MOBILE\n\n"
        "قیمت محصولات مستقیماً از دیتابیس فروشگاه "
        "خوانده می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مشاهده محصولات",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# BOTTOM KEYBOARD: TRADE-IN
# ==========================================================

@router.message(
    lambda message: (
        message.text == "🔄 تعویض گوشی"
    )
)
async def bottom_tradein_handler(
    message: Message,
):

    user_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    await message.answer(
        "🔄 تعویض گوشی\n\n"
        "در این بخش مشخصات گوشی فعلی را ثبت می‌کنی "
        "تا ارزش تقریبی آن برای تعویض محاسبه شود.",
        reply_markup=home_keyboard(user_id),
    )


# ==========================================================
# BOTTOM KEYBOARD: INSTALLMENT
# ==========================================================

@router.message(
    lambda message: (
        message.text == "💳 خرید اقساطی"
    )
)
async def bottom_installment_handler(
    message: Message,
):

    user_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    await message.answer(
        "💳 خرید اقساطی\n\n"
        "سیستم خرید اقساطی VIRA MOBILE "
        "در حال آماده‌سازی است.",
        reply_markup=home_keyboard(user_id),
    )


# ==========================================================
# BOTTOM KEYBOARD: CART
# ==========================================================

@router.message(
    lambda message: (
        message.text == "🛒 سبد خرید"
    )
)
async def bottom_cart_handler(
    message: Message,
):

    await message.answer(
        "🛒 سبد خرید\n\n"
        "سبد خرید شما در حال حاضر خالی است.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 فروشگاه",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# BOTTOM KEYBOARD: PROFILE
# ==========================================================

@router.message(
    lambda message: (
        message.text == "👤 حساب کاربری"
    )
)
async def bottom_profile_handler(
    message: Message,
):

    user = message.from_user

    if user is None:
        return

    await message.answer(
        "👤 حساب کاربری\n\n"
        f"نام: {user.first_name or '-'}\n"
        f"شناسه تلگرام: {user.id}\n\n"
        "اطلاعات مشتری در سیستم مرکزی VIRA MOBILE "
        "مدیریت خواهد شد.",
        reply_markup=home_keyboard(user.id),
    )


# ==========================================================
# BOTTOM KEYBOARD: ORDERS
# ==========================================================

@router.message(
    lambda message: (
        message.text == "📦 سفارش‌های من"
    )
)
async def bottom_orders_handler(
    message: Message,
):

    user_id = (
        message.from_user.id
        if message.from_user
        else None
    )

    await message.answer(
        "📦 سفارش‌های من\n\n"
        "هنوز سفارشی برای این حساب ثبت نشده است.",
        reply_markup=home_keyboard(user_id),
    )


# ==========================================================
# BOTTOM KEYBOARD: ADMIN PANEL
# ==========================================================

@router.message(
    lambda message: (
        message.text == "⚙️ پنل مدیریت"
    )
)
async def bottom_admin_panel_handler(
    message: Message,
):

    user = message.from_user

    if user is None or not is_admin(user.id):
        await message.answer(
            "⛔ دسترسی غیرمجاز.",
            reply_markup=bottom_menu(
                user.id if user else None
            ),
        )
        return

    # ------------------------------------------------------
    # Import here to avoid router/import circular problems.
    # ------------------------------------------------------

    from app.bot.admin_handlers import admin_menu

    await message.answer(
        "⚙️ پنل مدیریت VIRA MOBILE\n\n"
        "به بخش مدیریت خوش آمدید.",
        reply_markup=admin_menu(),
    )


# ==========================================================
# SHOP
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "shop"
)
async def shop_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "📱 فروشگاه VIRA MOBILE\n\n"
        "دسته‌بندی محصولات را انتخاب کن 👇",
        reply_markup=shop_menu(),
    )


# ==========================================================
# CATEGORY
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("category:")
    )
)
async def category_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    category = callback.data.split(
        ":",
        1,
    )[1].strip()

    category_names = {
        "iphone": "🍎 آیفون",
        "samsung": "📱 سامسونگ",
        "xiaomi": "🔵 شیائومی",
        "other": "📲 سایر برندها",
        "used": "♻️ گوشی‌های کارکرده",
    }

    title = category_names.get(
        category,
        "📱 محصولات",
    )

    async with AsyncSessionLocal() as db:

        products = await get_products_by_category(
            db,
            category,
            skip=0,
            limit=PRODUCT_LIMIT,
            active_only=True,
        )

    if not products:

        await callback.message.edit_text(
            f"{title}\n\n"
            "در حال حاضر محصولی در این دسته ثبت نشده است.\n\n"
            "محصولات از طریق پنل مدیریت اضافه خواهند شد.",
            reply_markup=shop_back_keyboard(
                callback.from_user.id
            ),
        )

        return

    text = (
        f"{title}\n\n"
        f"تعداد محصولات: {len(products)}\n\n"
        "محصول موردنظر را انتخاب کن 👇"
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_list_keyboard(
            products,
            "shop",
        ),
    )


# ==========================================================
# FEATURED
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "featured"
)
async def featured_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    async with AsyncSessionLocal() as db:

        products = await get_products(
            db,
            skip=0,
            limit=PRODUCT_LIMIT,
            active_only=True,
        )

    products = [
        product
        for product in products
        if product.is_featured
    ]

    if not products:

        await callback.message.edit_text(
            "🔥 محصولات ویژه\n\n"
            "در حال حاضر محصول ویژه‌ای ثبت نشده است.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 فروشگاه",
                            callback_data="shop",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="🏠 منوی اصلی",
                            callback_data="home",
                        )
                    ],
                ]
            ),
        )

        return

    await callback.message.edit_text(
        "🔥 محصولات ویژه\n\n"
        "محصولات ویژه VIRA MOBILE:",
        reply_markup=product_list_keyboard(
            products,
            "shop",
        ),
    )


# ==========================================================
# PRODUCT DETAIL
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("product:")
    )
)
async def product_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    product_id = parse_callback_id(
        callback.data
    )

    if product_id is None:

        await callback.message.edit_text(
            "❌ شناسه محصول نامعتبر است.",
            reply_markup=shop_back_keyboard(
                callback.from_user.id
            ),
        )

        return

    async with AsyncSessionLocal() as db:

        product = await get_active_product_by_id(
            db,
            product_id,
        )

        if product is None:

            await callback.message.edit_text(
                "❌ محصول پیدا نشد.",
                reply_markup=shop_back_keyboard(
                    callback.from_user.id
                ),
            )

            return

        price_text = format_price(
            product.base_price
        )

        condition = condition_text(
            product.condition
        )

        text = (
            f"📱 {product.brand} {product.model}\n\n"
            f"🏷️ کد محصول: {product.sku}\n"
            f"📦 وضعیت: {condition}\n"
            f"💰 قیمت: {price_text}\n\n"
        )

        if product.short_description:

            text += (
                f"📝 {product.short_description}\n\n"
            )

        if product.description:

            text += (
                "📋 توضیحات:\n"
                f"{product.description}\n\n"
            )

        active_variants = [
            variant
            for variant in product.variants
            if variant.is_active
        ]

        if active_variants:

            text += "⚙️ مشخصات موجود:\n\n"

            for variant in active_variants:

                parts: list[str] = []

                if variant.storage:

                    parts.append(
                        f"💾 {variant.storage}"
                    )

                if variant.ram:

                    parts.append(
                        f"🧠 RAM {variant.ram}"
                    )

                if variant.color:

                    parts.append(
                        f"🎨 {variant.color}"
                    )

                if variant.price is not None:

                    variant_price = format_price(
                        variant.price
                    )

                    if variant_price != "تماس برای قیمت":

                        parts.append(
                            f"💰 {variant_price}"
                        )

                if parts:

                    text += (
                        " • ".join(parts)
                        + "\n"
                    )

    await callback.message.edit_text(
        text,
        reply_markup=product_detail_keyboard(
            product.id,
            "shop",
        ),
    )


# ==========================================================
# HOME
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "home"
)
async def home_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "📱 VIRA MOBILE\n\n"
        "منوی اصلی:",
        reply_markup=main_menu(
            callback.from_user.id
        ),
    )


# ==========================================================
# CART ADD
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("cart:add:")
    )
)
async def add_to_cart_handler(
    callback: CallbackQuery,
):

    await callback.answer(
        "🛒 سیستم سبد خرید در حال اتصال است.",
        show_alert=True,
    )


# ==========================================================
# FAVORITE
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("favorite:")
    )
)
async def favorite_handler(
    callback: CallbackQuery,
):

    await callback.answer(
        "❤️ سیستم علاقه‌مندی‌ها در حال اتصال است.",
        show_alert=True,
    )


# ==========================================================
# COMPARE ADD
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("compare:add:")
    )
)
async def compare_handler(
    callback: CallbackQuery,
):

    await callback.answer(
        "⚖️ سیستم مقایسه در حال اتصال است.",
        show_alert=True,
    )


# ==========================================================
# PRICE ALERT
# ==========================================================

@router.callback_query(
    lambda callback: (
        callback.data
        and callback.data.startswith("alert:")
    )
)
async def alert_handler(
    callback: CallbackQuery,
):

    await callback.answer(
        "🔔 سیستم هشدار قیمت در حال اتصال است.",
        show_alert=True,
    )


# ==========================================================
# SEARCH CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "search"
)
async def search_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "🔎 جستجوی گوشی\n\n"
        "برای جستجو، نام برند یا مدل گوشی را ارسال کن.\n\n"
        "مثال:\n"
        "iPhone 15\n"
        "Samsung S24\n"
        "Xiaomi Redmi",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )


# ==========================================================
# SEARCH TEXT
# ==========================================================

@router.message()
async def text_search_handler(
    message: Message,
):

    if not message.text:
        return

    query = message.text.strip()

    if not query:
        return

    if query.startswith("/"):
        return

    # ------------------------------------------------------
    # IMPORTANT:
    # Reply Keyboard buttons are handled above.
    # Any other normal text is treated as a product search.
    # ------------------------------------------------------

    bottom_buttons = {
        "📱 فروشگاه",
        "🔎 جستجو",
        "🧠 مشاور خرید",
        "⚖️ مقایسه",
        "💰 قیمت‌ها",
        "🔄 تعویض گوشی",
        "💳 خرید اقساطی",
        "🛒 سبد خرید",
        "👤 حساب کاربری",
        "📦 سفارش‌های من",
        "⚙️ پنل مدیریت",
    }

    if query in bottom_buttons:
        return

    async with AsyncSessionLocal() as db:

        products = await search_products(
            db,
            query,
            limit=PRODUCT_LIMIT,
            active_only=True,
        )

    if not products:

        await message.answer(
            f"🔎 نتیجه جستجو برای «{query}»\n\n"
            "❌ محصولی پیدا نشد.\n\n"
            "نام برند یا مدل دیگری را امتحان کن.",
            reply_markup=bottom_menu(
                message.from_user.id
                if message.from_user
                else None
            ),
        )

        return

    await message.answer(
        f"🔎 نتایج جستجو برای «{query}»\n\n"
        f"تعداد نتایج: {len(products)}\n\n"
        "محصول موردنظر را انتخاب کن 👇",
        reply_markup=product_list_keyboard(
            products,
            "home",
        ),
    )


# ==========================================================
# ADVISOR CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "advisor"
)
async def advisor_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "🧠 مشاور خرید VIRA MOBILE\n\n"
        "در این بخش بر اساس بودجه، کاربرد، دوربین، "
        "باتری، بازی و نیازت بهترین گزینه‌ها پیشنهاد می‌شوند.",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )


# ==========================================================
# COMPARE CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "compare"
)
async def compare_main_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "⚖️ مقایسه گوشی‌ها\n\n"
        "ابتدا محصولات موردنظر را انتخاب کن.\n"
        "سیستم مقایسه مشخصات فنی، قیمت و ارزش خرید "
        "را کنار هم نمایش خواهد داد.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 رفتن به فروشگاه",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# PRICES CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "prices"
)
async def prices_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "💰 قیمت‌های VIRA MOBILE\n\n"
        "قیمت محصولات مستقیماً از دیتابیس فروشگاه "
        "خوانده می‌شود.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 مشاهده محصولات",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# TRADE-IN CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "tradein"
)
async def tradein_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "🔄 تعویض گوشی\n\n"
        "در این بخش مشخصات گوشی فعلی را ثبت می‌کنی "
        "تا ارزش تقریبی آن برای تعویض محاسبه شود.",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )


# ==========================================================
# INSTALLMENT CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "installment"
)
async def installment_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "💳 خرید اقساطی\n\n"
        "سیستم خرید اقساطی VIRA MOBILE "
        "در حال آماده‌سازی است.",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )


# ==========================================================
# CART CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "cart"
)
async def cart_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "🛒 سبد خرید\n\n"
        "سبد خرید شما در حال حاضر خالی است.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="📱 فروشگاه",
                        callback_data="shop",
                    )
                ],
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ],
            ]
        ),
    )


# ==========================================================
# PROFILE CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "profile"
)
async def profile_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    user = callback.from_user

    await callback.message.edit_text(
        "👤 حساب کاربری\n\n"
        f"نام: {user.first_name or '-'}\n"
        f"شناسه تلگرام: {user.id}\n\n"
        "اطلاعات مشتری در سیستم مرکزی VIRA MOBILE "
        "مدیریت خواهد شد.",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )


# ==========================================================
# ORDERS CALLBACK
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "orders"
)
async def orders_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    await callback.message.edit_text(
        "📦 سفارش‌های من\n\n"
        "هنوز سفارشی برای این حساب ثبت نشده است.",
        reply_markup=home_keyboard(
            callback.from_user.id
        ),
    )
