from decimal import Decimal, InvalidOperation

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database.connection import AsyncSessionLocal
from app.database.models import Product
from app.services.products import (
    get_active_product_by_id,
    get_products_by_category,
    get_product_variants,
    get_products,
    search_products,
)


router = Router()


# ==========================================================
# CONSTANTS
# ==========================================================

PRODUCT_LIMIT = 30


CATEGORY_NAMES = {
    "iphone": "🍎 آیفون",
    "samsung": "📱 سامسونگ",
    "xiaomi": "🔵 شیائومی",
    "other": "📲 سایر برندها",
    "used": "♻️ گوشی‌های کارکرده",
}


# ==========================================================
# HELPERS
# ==========================================================

def format_price(value) -> str:
    """
    Format product price for Telegram display.
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


def condition_text(condition) -> str:
    """
    Convert product condition to Persian text.
    """

    value = getattr(condition, "value", condition)

    if value == "new":
        return "نو"

    if value == "used":
        return "کارکرده"

    return str(value or "نامشخص")


def safe_product_id(callback_data: str | None) -> int | None:
    """
    Safely extract product ID from callback data.
    """

    if not callback_data:
        return None

    try:
        value = callback_data.split(":", 1)[1]
        product_id = int(value)

        if product_id <= 0:
            return None

        return product_id

    except (ValueError, IndexError):
        return None


def safe_variant_id(callback_data: str | None) -> int | None:
    """
    Safely extract variant ID from callback data.
    """

    if not callback_data:
        return None

    try:
        value = callback_data.split(":", 2)[2]
        variant_id = int(value)

        if variant_id <= 0:
            return None

        return variant_id

    except (ValueError, IndexError):
        return None


# ==========================================================
# MAIN MENU
# ==========================================================

def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
# GENERIC BACK MENU
# ==========================================================

def back_home_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔙 منوی اصلی",
                    callback_data="home",
                )
            ]
        ]
    )


def shop_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
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
    )


# ==========================================================
# PRODUCT LIST MENU
# ==========================================================

def product_list_keyboard(
    products: list[Product],
    back_callback: str = "shop",
) -> InlineKeyboardMarkup:

    buttons = []

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
# PRODUCT DETAIL MENU
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
        "از منوی زیر شروع کن 👇"
    )

    await message.answer(
        text,
        reply_markup=main_menu(),
    )


# ==========================================================
# MENU
# ==========================================================

@router.message(Command("menu"))
async def menu_handler(message: Message):

    await message.answer(
        "📱 منوی اصلی VIRA MOBILE",
        reply_markup=main_menu(),
    )


# ==========================================================
# HELP
# ==========================================================

@router.message(Command("help"))
async def help_handler(message: Message):

    await message.answer(
        "راهنمای VIRA MOBILE\n\n"
        "/start - شروع کار\n"
        "/menu - منوی اصلی\n"
        "/help - راهنما\n\n"
        "برای خرید یا مشاوره از منوی اصلی استفاده کن.",
    )


# ==========================================================
# SHOP
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "shop"
)
async def shop_handler(callback: CallbackQuery):

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
    )[1]

    title = CATEGORY_NAMES.get(
        category,
        "📱 محصولات",
    )

    try:

        products = await get_products_by_category(
            category=category,
            limit=PRODUCT_LIMIT,
            offset=0,
            active_only=True,
        )

    except Exception as exc:

        print(
            f"Category handler error: {type(exc).__name__}: {exc}"
        )

        await callback.message.edit_text(
            "❌ خطایی هنگام دریافت محصولات رخ داد.\n\n"
            "لطفاً دوباره تلاش کن.",
            reply_markup=shop_back_keyboard(),
        )

        return

    if not products:

        await callback.message.edit_text(
            f"{title}\n\n"
            "در حال حاضر محصولی در این دسته ثبت نشده است.\n\n"
            "محصولات از طریق پنل مدیریت اضافه خواهند شد.",
            reply_markup=shop_back_keyboard(),
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

    try:

        products = await get_products(
            limit=PRODUCT_LIMIT,
            offset=0,
            active_only=True,
            featured_only=True,
        )

    except Exception as exc:

        print(
            f"Featured handler error: {type(exc).__name__}: {exc}"
        )

        await callback.message.edit_text(
            "❌ خطایی هنگام دریافت محصولات ویژه رخ داد.",
            reply_markup=shop_back_keyboard(),
        )

        return

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

    product_id = safe_product_id(
        callback.data
    )

    if product_id is None:

        await callback.message.edit_text(
            "❌ شناسه محصول نامعتبر است.",
            reply_markup=shop_back_keyboard(),
        )

        return

    try:

        product = await get_active_product_by_id(
            product_id
        )

    except Exception as exc:

        print(
            f"Product handler error: {type(exc).__name__}: {exc}"
        )

        await callback.message.edit_text(
            "❌ خطایی هنگام دریافت اطلاعات محصول رخ داد.",
            reply_markup=shop_back_keyboard(),
        )

        return

    if product is None:

        await callback.message.edit_text(
            "❌ محصول پیدا نشد یا در حال حاضر فعال نیست.",
            reply_markup=shop_back_keyboard(),
        )

        return

    # ------------------------------------------------------
    # VARIANTS
    # ------------------------------------------------------

    try:

        variants = await get_product_variants(
            product_id=product.id,
            active_only=True,
        )

    except Exception as exc:

        print(
            f"Variant loading error: {type(exc).__name__}: {exc}"
        )

        variants = []

    # ------------------------------------------------------
    # PRICE
    # ------------------------------------------------------

    price_text = format_price(
        product.base_price
    )

    # ------------------------------------------------------
    # CONDITION
    # ------------------------------------------------------

    condition = condition_text(
        product.condition
    )

    # ------------------------------------------------------
    # TEXT
    # ------------------------------------------------------

    text = (
        f"📱 {product.brand} {product.model}\n\n"
        f"🏷️ کد محصول: {product.sku}\n"
        f"📦 وضعیت: {condition}\n"
        f"💰 قیمت پایه: {price_text}\n\n"
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

    # ------------------------------------------------------
    # VARIANTS
    # ------------------------------------------------------

    if variants:

        text += "⚙️ مشخصات موجود:\n\n"

        for variant in variants:

            parts = []

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

            if variant.price:

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

    else:

        text += (
            "⚙️ نسخه یا ظرفیت دیگری برای این محصول "
            "ثبت نشده است.\n\n"
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
        reply_markup=main_menu(),
    )


# ==========================================================
# SEARCH
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
        "نام برند یا مدل گوشی را برای جستجو ارسال کن.\n\n"
        "مثلاً:\n"
        "• iPhone 15\n"
        "• Samsung S24\n"
        "• Xiaomi 14",
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# ADVISOR
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
        "باتری، بازی و نیازت بهترین گزینه‌ها پیشنهاد می‌شوند.\n\n"
        "سیستم مشاور خرید در مرحله بعد به موتور "
        "پیشنهاد محصول متصل خواهد شد.",
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# COMPARE
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
# PRICES
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "prices"
)
async def prices_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    try:

        products = await get_products(
            limit=PRODUCT_LIMIT,
            offset=0,
            active_only=True,
        )

    except Exception as exc:

        print(
            f"Prices handler error: {type(exc).__name__}: {exc}"
        )

        await callback.message.edit_text(
            "❌ خطایی هنگام دریافت قیمت‌ها رخ داد.",
            reply_markup=shop_back_keyboard(),
        )

        return

    if not products:

        await callback.message.edit_text(
            "💰 قیمت‌های VIRA MOBILE\n\n"
            "در حال حاضر محصولی برای نمایش قیمت ثبت نشده است.",
            reply_markup=shop_back_keyboard(),
        )

        return

    text = (
        "💰 قیمت‌های VIRA MOBILE\n\n"
        "آخرین قیمت محصولات ثبت‌شده:\n\n"
    )

    for index, product in enumerate(
        products,
        start=1,
    ):

        price = format_price(
            product.base_price
        )

        text += (
            f"{index}. "
            f"{product.brand} {product.model}\n"
            f"   💰 {price}\n\n"
        )

    await callback.message.edit_text(
        text,
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
# TRADE-IN
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
        "تا ارزش تقریبی آن برای تعویض محاسبه شود.\n\n"
        "سامانه ارزیابی و تعویض گوشی در مرحله بعد "
        "فعال خواهد شد.",
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# INSTALLMENT
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
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# CART
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
        "سبد خرید شما در حال حاضر خالی است.\n\n"
        "پس از فعال شدن سیستم سبد خرید، "
        "محصولات انتخاب‌شده در این بخش نمایش داده می‌شوند.",
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
# PROFILE
# ==========================================================

@router.callback_query(
    lambda callback: callback.data == "profile"
)
async def profile_handler(
    callback: CallbackQuery,
):

    await callback.answer()

    user = callback.from_user

    first_name = (
        user.first_name
        if user.first_name
        else "-"
    )

    username = (
        f"@{user.username}"
        if user.username
        else "ثبت نشده"
    )

    await callback.message.edit_text(
        "👤 حساب کاربری\n\n"
        f"نام: {first_name}\n"
        f"نام کاربری: {username}\n"
        f"شناسه تلگرام: {user.id}\n\n"
        "اطلاعات مشتری در سیستم مرکزی "
        "VIRA MOBILE مدیریت خواهد شد.",
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# ORDERS
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
        "هنوز سفارشی برای این حساب ثبت نشده است.\n\n"
        "سیستم سفارش‌ها در مرحله اتصال به بخش "
        "مدیریت سفارشات قرار دارد.",
        reply_markup=back_home_keyboard(),
    )


# ==========================================================
# ADD TO CART
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

    product_id = safe_product_id(
        callback.data
    )

    if product_id is None:

        await callback.answer(
            "❌ شناسه محصول نامعتبر است.",
            show_alert=True,
        )

        return

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

    product_id = safe_product_id(
        callback.data
    )

    if product_id is None:

        await callback.answer(
            "❌ شناسه محصول نامعتبر است.",
            show_alert=True,
        )

        return

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

    product_id = safe_product_id(
        callback.data
    )

    if product_id is None:

        await callback.answer(
            "❌ شناسه محصول نامعتبر است.",
            show_alert=True,
        )

        return

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

    product_id = safe_product_id(
        callback.data
    )

    if product_id is None:

        await callback.answer(
            "❌ شناسه محصول نامعتبر است.",
            show_alert=True,
        )

        return

    await callback.answer(
        "🔔 سیستم هشدار قیمت در حال اتصال است.",
        show_alert=True,
    )


# ==========================================================
# UNKNOWN CALLBACK FALLBACK
# ==========================================================

@router.callback_query()
async def unknown_callback_handler(
    callback: CallbackQuery,
):

    await callback.answer(
        "⚠️ این گزینه هنوز فعال نشده است.",
        show_alert=True,
    )
