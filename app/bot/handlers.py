from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton


router = Router()


def main_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 فروشگاه موبایل",
                    callback_data="shop"
                ),
                InlineKeyboardButton(
                    text="🔎 جستجوی گوشی",
                    callback_data="search"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🧠 مشاور خرید",
                    callback_data="advisor"
                ),
                InlineKeyboardButton(
                    text="⚖️ مقایسه گوشی",
                    callback_data="compare"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💰 قیمت‌ها",
                    callback_data="prices"
                ),
                InlineKeyboardButton(
                    text="🔄 تعویض گوشی",
                    callback_data="tradein"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="💳 خرید اقساطی",
                    callback_data="installment"
                ),
                InlineKeyboardButton(
                    text="🛒 سبد خرید",
                    callback_data="cart"
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👤 حساب کاربری",
                    callback_data="profile"
                ),
                InlineKeyboardButton(
                    text="📦 سفارش‌های من",
                    callback_data="orders"
                ),
            ],
        ]
    )


@router.message(CommandStart())
async def start_handler(message: Message):
    user = message.from_user

    name = user.first_name if user else "دوست عزیز"

    text = (
        f"سلام {name} 👋\n\n"
        "به ربات رسمی VIRA MOBILE خوش آمدی 📱\n\n"
        "اینجا می‌تونی:\n"
        "• گوشی مناسب بودجه‌ات رو پیدا کنی\n"
        "• گوشی‌ها رو با هم مقایسه کنی\n"
        "• قیمت محصولات رو ببینی\n"
        "• برای خرید مشاوره بگیری\n"
        "• سفارش ثبت و پیگیری کنی\n"
        "• گوشی خودت رو برای تعویض اعلام کنی\n\n"
        "از منوی زیر شروع کن 👇"
    )

    await message.answer(
        text,
        reply_markup=main_menu()
    )


@router.message(Command("menu"))
async def menu_handler(message: Message):
    await message.answer(
        "📱 منوی اصلی VIRA MOBILE",
        reply_markup=main_menu()
    )


@router.message(Command("help"))
async def help_handler(message: Message):
    await message.answer(
        "راهنمای VIRA MOBILE\n\n"
        "/start - شروع کار\n"
        "/menu - منوی اصلی\n"
        "/help - راهنما\n\n"
        "برای خرید یا مشاوره از منوی اصلی استفاده کن."
    )


@router.callback_query()
async def callback_handler(callback):
    data = callback.data

    if data == "shop":
        text = (
            "📱 فروشگاه VIRA MOBILE\n\n"
            "دسته‌بندی محصولات:\n\n"
            "🍎 آیفون\n"
            "📱 سامسونگ\n"
            "🔵 شیائومی\n"
            "📲 سایر برندها\n"
            "♻️ گوشی‌های کارکرده"
        )

    elif data == "search":
        text = (
            "🔎 جستجوی گوشی\n\n"
            "در نسخه کامل فروشگاه می‌تونی بر اساس:\n"
            "• برند\n"
            "• مدل\n"
            "• قیمت\n"
            "• حافظه\n"
            "• رم\n"
            "• دوربین\n"
            "• باتری\n"
            "• کاربرد\n"
            "گوشی موردنظرت رو پیدا کنی."
        )

    elif data == "advisor":
        text = (
            "🧠 مشاور خرید VIRA MOBILE\n\n"
            "مشاور خرید بر اساس بودجه و نیازت "
            "گوشی‌های مناسب رو پیشنهاد می‌ده.\n\n"
            "مثلاً برای:\n"
            "🎮 بازی\n"
            "📸 عکاسی\n"
            "🎬 تولید محتوا\n"
            "💼 استفاده روزمره\n"
            "🔋 باتری قوی"
        )

    elif data == "compare":
        text = (
            "⚖️ مقایسه گوشی‌ها\n\n"
            "در این بخش می‌تونی مشخصات دو یا چند گوشی "
            "رو کنار هم مقایسه کنی."
        )

    elif data == "prices":
        text = (
            "💰 قیمت محصولات\n\n"
            "قیمت‌ها از موجودی مرکزی VIRA MOBILE "
            "خوانده خواهند شد."
        )

    elif data == "tradein":
        text = (
            "🔄 تعویض گوشی\n\n"
            "مدل گوشی فعلی، وضعیت دستگاه و مشخصاتش "
            "رو ثبت می‌کنیم تا ارزش تقریبی تعویض محاسبه بشه."
        )

    elif data == "installment":
        text = (
            "💳 خرید اقساطی\n\n"
            "امکان ثبت درخواست خرید اقساطی "
            "و بررسی شرایط در سیستم فروشگاه قرار می‌گیرد."
        )

    elif data == "cart":
        text = (
            "🛒 سبد خرید\n\n"
            "سبد خرید شما در حال حاضر خالی است."
        )

    elif data == "profile":
        user = callback.from_user

        text = (
            "👤 حساب کاربری\n\n"
            f"نام: {user.first_name or '-'}\n"
            f"شناسه تلگرام: {user.id}\n\n"
            "اطلاعات مشتری در سیستم مرکزی VIRA MOBILE "
            "ذخیره خواهد شد."
        )

    elif data == "orders":
        text = (
            "📦 سفارش‌های من\n\n"
            "هنوز سفارشی برای این حساب ثبت نشده است."
        )

    else:
        text = "این بخش در حال آماده‌سازی است."

    await callback.answer()

    await callback.message.edit_text(
        text,
        reply_markup=main_menu()
    )
