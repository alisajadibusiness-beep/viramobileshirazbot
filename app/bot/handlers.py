from decimal import Decimal

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import AsyncSessionLocal
from app.database.models import Product


router = Router()


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
    back_callback: str,
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

@router.callback_query(lambda callback: callback.data == "shop")
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

    category = callback.data.split(":", 1)[1]

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

        result = await db.execute(
            select(Product)
            .where(
                Product.category == category,
                Product.is_active.is_(True),
            )
            .order_by(Product.created_at.desc())
            .limit(30)
        )

        products = list(result.scalars().all())

    if not products:

        await callback.message.edit_text(
            f"{title}\n\n"
            "در حال حاضر محصولی در این دسته ثبت نشده است.\n\n"
            "محصولات از طریق پنل مدیریت اضافه خواهند شد.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 دسته‌بندی‌ها",
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

    text = (
        f"{title}\n\n"
        f"تعداد محصولات: {len(products)}\n\n"
        "محصول موردنظر را انتخاب کن 👇"
    )

    await callback.message.edit_text(
        text,
        reply_markup=product_list_keyboard(
            products,
            f"shop",
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

        result = await db.execute(
            select(Product)
            .where(
                Product.is_active.is_(True),
                Product.is_featured.is_(True),
            )
            .order_by(Product.created_at.desc())
            .limit(30)
        )

        products = list(result.scalars().all())

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
                    ]
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

    product_id = int(
        callback.data.split(":", 1)[1]
    )

    async with AsyncSessionLocal() as db:

        result = await db.execute(
            select(Product)
            .where(
                Product.id == product_id,
                Product.is_active.is_(True),
            )
        )

        product = result.scalar_one_or_none()

    if product is None:

        await callback.message.edit_text(
            "❌ محصول پیدا نشد.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="🔙 فروشگاه",
                            callback_data="shop",
                        )
                    ]
                ]
            ),
        )

        return

    if product.base_price > 0:
        price_text = (
            f"{product.base_price:,.0f} تومان"
        )
    else:
        price_text = "تماس برای قیمت"

    condition_text = (
        "نو"
        if product.condition == "new"
        else "کارکرده"
    )

    text = (
        f"📱 {product.brand} {product.model}\n\n"
        f"🏷️ کد محصول: {product.sku}\n"
        f"📦 وضعیت: {condition_text}\n"
        f"💰 قیمت: {price_text}\n\n"
    )

    if product.short_description:
        text += (
            f"📝 {product.short_description}\n\n"
        )

    if product.description:
        text += (
            f"📋 توضیحات:\n"
            f"{product.description}\n\n"
        )

    if product.variants:

        text += "⚙️ مشخصات موجود:\n\n"

        for variant in product.variants:

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

            if variant.price > 0:
                parts.append(
                    f"💰 {variant.price:,.0f}"
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
        reply_markup=main_menu(),
    )


# ==========================================================
# PLACEHOLDER ACTIONS
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
# OTHER MAIN MENU ITEMS
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
        "سیستم جستجوی هوشمند در حال آماده‌سازی است.\n\n"
        "در نسخه کامل می‌توانی بر اساس مدل، برند، "
        "قیمت، حافظه و کاربرد جستجو کنی.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )


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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )


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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )


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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )


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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )


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
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="🔙 منوی اصلی",
                        callback_data="home",
                    )
                ]
            ]
        ),
    )
