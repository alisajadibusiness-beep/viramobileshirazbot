from __future__ import annotations

from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
)

from app.services.smart_pricing import create_evaluation


router = Router(name="smart_pricing")


# ============================================================
# States
# ============================================================

class SmartPricingStates(StatesGroup):
    waiting_brand = State()
    waiting_model = State()
    waiting_storage = State()
    waiting_ram = State()
    waiting_color = State()

    waiting_battery = State()
    waiting_appearance = State()
    waiting_technical = State()
    waiting_repair = State()
    waiting_parts = State()

    waiting_registration = State()
    waiting_box = State()
    waiting_accessories = State()

    waiting_market_price = State()
    waiting_customer_note = State()


# ============================================================
# Keyboards
# ============================================================

def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def battery_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="100"),
                KeyboardButton(text="95"),
                KeyboardButton(text="90"),
            ],
            [
                KeyboardButton(text="85"),
                KeyboardButton(text="80"),
                KeyboardButton(text="75"),
            ],
            [
                KeyboardButton(text="70"),
                KeyboardButton(text="کمتر از 70"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def appearance_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="عالی"),
                KeyboardButton(text="خیلی خوب"),
            ],
            [
                KeyboardButton(text="خوب"),
                KeyboardButton(text="متوسط"),
            ],
            [
                KeyboardButton(text="ضعیف"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def technical_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="عالی"),
                KeyboardButton(text="خوب"),
            ],
            [
                KeyboardButton(text="متوسط"),
                KeyboardButton(text="ضعیف"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def repair_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="بدون تعمیر"),
                KeyboardButton(text="تعمیر جزئی"),
            ],
            [
                KeyboardButton(text="تعمیر اساسی"),
                KeyboardButton(text="نامشخص"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def parts_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="همه اصلی"),
                KeyboardButton(text="ترکیبی"),
            ],
            [
                KeyboardButton(text="غیراصلی"),
                KeyboardButton(text="نامشخص"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def registration_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="رجیستر شده"),
                KeyboardButton(text="رجیستر نشده"),
            ],
            [
                KeyboardButton(text="نامشخص"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def yes_no_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="بله"),
                KeyboardButton(text="خیر"),
            ],
            [
                KeyboardButton(text="❌ لغو کارشناسی"),
            ],
        ],
        resize_keyboard=True,
    )


def result_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📨 ارسال درخواست برای مدیریت",
                    callback_data="smart_price:submit",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="❌ لغو",
                    callback_data="smart_price:cancel",
                ),
            ],
        ],
    )


# ============================================================
# Helpers
# ============================================================

PERSIAN_DIGITS = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹",
    "0123456789",
)


def normalize_text(value: str) -> str:
    return (
        value.strip()
        .replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
    )


def normalize_digits(value: str) -> str:
    value = value.translate(PERSIAN_DIGITS)
    value = value.replace(",", "")
    value = value.replace("٬", "")
    value = value.replace(" ", "")
    return value


def parse_integer(value: str) -> int | None:
    value = normalize_digits(value)

    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def parse_decimal(value: str) -> Decimal | None:
    value = normalize_digits(value)

    try:
        number = Decimal(value)

        if not number.is_finite():
            return None

        return number
    except (InvalidOperation, ValueError, TypeError):
        return None


def appearance_to_code(value: str) -> str | None:
    value = normalize_text(value)

    mapping = {
        "عالی": "excellent",
        "خیلی خوب": "very_good",
        "خوب": "good",
        "متوسط": "fair",
        "ضعیف": "poor",
    }

    return mapping.get(value)


def technical_to_code(value: str) -> str | None:
    value = normalize_text(value)

    mapping = {
        "عالی": "excellent",
        "خوب": "good",
        "متوسط": "fair",
        "ضعیف": "poor",
    }

    return mapping.get(value)


def repair_to_code(value: str) -> str | None:
    value = normalize_text(value)

    mapping = {
        "بدون تعمیر": "none",
        "تعمیر جزئی": "minor",
        "تعمیر اساسی": "major",
        "نامشخص": "unknown",
    }

    return mapping.get(value)


def parts_to_code(value: str) -> str | None:
    value = normalize_text(value)

    mapping = {
        "همه اصلی": "original",
        "ترکیبی": "mixed",
        "غیراصلی": "non_original",
        "نامشخص": "unknown",
    }

    return mapping.get(value)


def registration_to_code(value: str) -> str | None:
    value = normalize_text(value)

    mapping = {
        "رجیستر شده": "registered",
        "رجیستر نشده": "not_registered",
        "نامشخص": "unknown",
    }

    return mapping.get(value)


def bool_from_text(value: str) -> bool | None:
    value = normalize_text(value)

    if value == "بله":
        return True

    if value == "خیر":
        return False

    return None


def format_price(value: Decimal | int | float | str) -> str:
    number = Decimal(str(value))
    return f"{number:,.0f}"


def format_result(data: dict) -> str:
    return (
        "🤖 <b>نتیجه کارشناسی هوشمند VIRA MOBILE</b>\n"
        "\n"
        f"📱 <b>{data['brand']} {data['model']}</b>\n"
        f"💾 حافظه: {data['storage'] or '-'}\n"
        f"🧠 RAM: {data['ram'] or '-'}\n"
        f"🎨 رنگ: {data['color'] or '-'}\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"📊 ارزش برآوردی: <b>{format_price(data['estimated_value'])} تومان</b>\n"
        f"🛒 قیمت پیشنهادی خرید: <b>{format_price(data['purchase_price'])} تومان</b>\n"
        f"🔴 سقف خرید: <b>{format_price(data['max_purchase_price'])} تومان</b>\n"
        f"🏷 قیمت پیشنهادی فروش: <b>{format_price(data['selling_price'])} تومان</b>\n"
        f"📈 سود احتمالی: <b>{format_price(data['expected_profit'])} تومان</b>\n"
        f"⭐ امتیاز کارشناسی: <b>{data['score']}/100</b>\n"
        "\n"
        f"🎯 <b>{data['recommendation']}</b>\n"
        "\n"
        f"📝 {data['explanation']}\n"
        "\n"
        "⚠️ این قیمت هنوز نهایی نیست.\n"
        "تأیید نهایی فقط توسط مدیریت VIRA MOBILE انجام می‌شود."
    )


async def cancel_flow(message: Message, state: FSMContext) -> None:
    await state.clear()

    await message.answer(
        "❌ کارشناسی لغو شد.\n\n"
        "هر زمان خواستی می‌توانی دوباره از گزینه «فروش گوشی» استفاده کنی."
    )


# ============================================================
# Entry
# ============================================================

@router.message(F.text == "📱 فروش گوشی")
async def start_smart_pricing(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SmartPricingStates.waiting_brand)

    await message.answer(
        "📱 <b>کارشناسی فروش گوشی</b>\n\n"
        "برای اینکه بتوانیم قیمت خرید مناسبی محاسبه کنیم، "
        "مشخصات گوشی را مرحله‌به‌مرحله وارد کن.\n\n"
        "اول از همه:\n"
        "🏷 برند گوشی را وارد کن.\n\n"
        "مثال:\n"
        "<code>Apple</code>\n"
        "<code>Samsung</code>\n"
        "<code>Xiaomi</code>",
        reply_markup=cancel_keyboard(),
    )


@router.message(F.text == "🤖 کارشناسی هوشمند")
async def start_smart_pricing_alt(
    message: Message,
    state: FSMContext,
) -> None:
    await start_smart_pricing(message, state)


# ============================================================
# Brand
# ============================================================

@router.message(SmartPricingStates.waiting_brand)
async def receive_brand(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    brand = normalize_text(message.text or "")

    if len(brand) < 2:
        await message.answer(
            "❌ نام برند معتبر نیست.\n"
            "مثلاً Apple یا Samsung را وارد کن."
        )
        return

    await state.update_data(brand=brand)
    await state.set_state(SmartPricingStates.waiting_model)

    await message.answer(
        "📱 حالا <b>مدل دقیق گوشی</b> را وارد کن.\n\n"
        "مثال:\n"
        "<code>iPhone 15 Pro Max</code>\n"
        "<code>Galaxy S24 Ultra</code>"
    )


# ============================================================
# Model
# ============================================================

@router.message(SmartPricingStates.waiting_model)
async def receive_model(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    model = normalize_text(message.text or "")

    if len(model) < 2:
        await message.answer("❌ مدل واردشده معتبر نیست.")
        return

    await state.update_data(model=model)
    await state.set_state(SmartPricingStates.waiting_storage)

    await message.answer(
        "💾 ظرفیت حافظه گوشی را وارد کن.\n\n"
        "مثال:\n"
        "<code>128GB</code>\n"
        "<code>256GB</code>\n"
        "<code>512GB</code>"
    )


# ============================================================
# Storage
# ============================================================

@router.message(SmartPricingStates.waiting_storage)
async def receive_storage(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    storage = normalize_text(message.text or "")

    if len(storage) < 2:
        await message.answer("❌ ظرفیت حافظه معتبر نیست.")
        return

    await state.update_data(storage=storage)
    await state.set_state(SmartPricingStates.waiting_ram)

    await message.answer(
        "🧠 مقدار RAM را وارد کن.\n\n"
        "مثال:\n"
        "<code>8GB</code>\n"
        "<code>12GB</code>\n"
        "<code>16GB</code>"
    )


# ============================================================
# RAM
# ============================================================

@router.message(SmartPricingStates.waiting_ram)
async def receive_ram(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    ram = normalize_text(message.text or "")

    if len(ram) < 1:
        await message.answer("❌ مقدار RAM معتبر نیست.")
        return

    await state.update_data(ram=ram)
    await state.set_state(SmartPricingStates.waiting_color)

    await message.answer(
        "🎨 رنگ گوشی را وارد کن.\n\n"
        "مثال:\n"
        "<code>مشکی</code>\n"
        "<code>تیتانیوم طبیعی</code>"
    )


# ============================================================
# Color
# ============================================================

@router.message(SmartPricingStates.waiting_color)
async def receive_color(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    color = normalize_text(message.text or "")

    if len(color) < 1:
        await message.answer("❌ رنگ گوشی را وارد کن.")
        return

    await state.update_data(color=color)
    await state.set_state(SmartPricingStates.waiting_battery)

    await message.answer(
        "🔋 درصد سلامت باتری را انتخاب یا وارد کن:",
        reply_markup=battery_keyboard(),
    )


# ============================================================
# Battery
# ============================================================

@router.message(SmartPricingStates.waiting_battery)
async def receive_battery(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    raw = normalize_text(message.text or "")

    if raw == "کمتر از 70":
        battery = 65
    else:
        battery = parse_integer(raw)

    if battery is None or battery < 1 or battery > 100:
        await message.answer(
            "❌ درصد باتری باید بین 1 تا 100 باشد."
        )
        return

    await state.update_data(battery_percent=battery)
    await state.set_state(SmartPricingStates.waiting_appearance)

    await message.answer(
        "📱 وضعیت ظاهری گوشی را انتخاب کن:",
        reply_markup=appearance_keyboard(),
    )


# ============================================================
# Appearance
# ============================================================

@router.message(SmartPricingStates.waiting_appearance)
async def receive_appearance(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    condition = appearance_to_code(message.text or "")

    if condition is None:
        await message.answer(
            "❌ یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",
            reply_markup=appearance_keyboard(),
        )
        return

    await state.update_data(
        appearance_condition=condition,
    )
    await state.set_state(
        SmartPricingStates.waiting_technical
    )

    await message.answer(
        "⚙️ وضعیت فنی گوشی را انتخاب کن:",
        reply_markup=technical_keyboard(),
    )


# ============================================================
# Technical
# ============================================================

@router.message(SmartPricingStates.waiting_technical)
async def receive_technical(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    condition = technical_to_code(message.text or "")

    if condition is None:
        await message.answer(
            "❌ یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",
            reply_markup=technical_keyboard(),
        )
        return

    await state.update_data(
        technical_condition=condition,
    )
    await state.set_state(
        SmartPricingStates.waiting_repair
    )

    await message.answer(
        "🔧 وضعیت تعمیرات گوشی:",
        reply_markup=repair_keyboard(),
    )


# ============================================================
# Repair
# ============================================================

@router.message(SmartPricingStates.waiting_repair)
async def receive_repair(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    repair = repair_to_code(message.text or "")

    if repair is None:
        await message.answer(
            "❌ یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",
            reply_markup=repair_keyboard(),
        )
        return

    await state.update_data(
        repair_status=repair,
    )
    await state.set_state(
        SmartPricingStates.waiting_parts
    )

    await message.answer(
        "🔩 وضعیت قطعات گوشی:",
        reply_markup=parts_keyboard(),
    )


# ============================================================
# Parts
# ============================================================

@router.message(SmartPricingStates.waiting_parts)
async def receive_parts(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    parts = parts_to_code(message.text or "")

    if parts is None:
        await message.answer(
            "❌ یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",
            reply_markup=parts_keyboard(),
        )
        return

    await state.update_data(
        parts_status=parts,
    )
    await state.set_state(
        SmartPricingStates.waiting_registration
    )

    await message.answer(
        "📡 وضعیت رجیستری گوشی:",
        reply_markup=registration_keyboard(),
    )


# ============================================================
# Registration
# ============================================================

@router.message(SmartPricingStates.waiting_registration)
async def receive_registration(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    registration = registration_to_code(message.text or "")

    if registration is None:
        await message.answer(
            "❌ یکی از گزینه‌های نمایش‌داده‌شده را انتخاب کن.",
            reply_markup=registration_keyboard(),
        )
        return

    await state.update_data(
        registration_status=registration,
    )
    await state.set_state(
        SmartPricingStates.waiting_box
    )

    await message.answer(
        "📦 جعبه اصلی گوشی را داری؟",
        reply_markup=yes_no_keyboard(),
    )


# ============================================================
# Box
# ============================================================

@router.message(SmartPricingStates.waiting_box)
async def receive_box(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    value = bool_from_text(message.text or "")

    if value is None:
        await message.answer(
            "❌ لطفاً بله یا خیر را انتخاب کن.",
            reply_markup=yes_no_keyboard(),
        )
        return

    await state.update_data(has_box=value)
    await state.set_state(
        SmartPricingStates.waiting_accessories
    )

    await message.answer(
        "🔌 لوازم جانبی اصلی را داری؟",
        reply_markup=yes_no_keyboard(),
    )


# ============================================================
# Accessories
# ============================================================

@router.message(SmartPricingStates.waiting_accessories)
async def receive_accessories(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    value = bool_from_text(message.text or "")

    if value is None:
        await message.answer(
            "❌ لطفاً بله یا خیر را انتخاب کن.",
            reply_markup=yes_no_keyboard(),
        )
        return

    await state.update_data(
        has_accessories=value,
    )
    await state.set_state(
        SmartPricingStates.waiting_market_price
    )

    await message.answer(
        "💰 حالا <b>قیمت تقریبی فعلی بازار</b> این گوشی را "
        "به تومان وارد کن.\n\n"
        "مثال:\n"
        "<code>85000000</code>\n\n"
        "در این نسخه قیمت بازار از ورودی شما استفاده می‌شود. "
        "در مرحله بعد امکان اتصال منبع قیمت بازار را اضافه می‌کنیم.",
        reply_markup=cancel_keyboard(),
    )


# ============================================================
# Market price
# ============================================================

@router.message(SmartPricingStates.waiting_market_price)
async def receive_market_price(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    price = parse_decimal(message.text or "")

    if price is None or price <= 0:
        await message.answer(
            "❌ قیمت معتبر نیست.\n"
            "مثلاً:\n"
            "<code>85000000</code>"
        )
        return

    await state.update_data(
        market_price=str(price),
    )

    await state.set_state(
        SmartPricingStates.waiting_customer_note
    )

    await message.answer(
        "📝 اگر توضیحی درباره گوشی داری وارد کن.\n\n"
        "مثلاً:\n"
        "«صفحه یک خط خیلی ریز دارد»\n\n"
        "اگر توضیحی نداری، بنویس:\n"
        "<code>ندارم</code>"
    )


# ============================================================
# Customer note + calculate
# ============================================================

@router.message(SmartPricingStates.waiting_customer_note)
async def receive_customer_note(
    message: Message,
    state: FSMContext,
) -> None:
    if message.text == "❌ لغو کارشناسی":
        await cancel_flow(message, state)
        return

    note = normalize_text(message.text or "")

    if note == "ندارم":
        note = ""

    await state.update_data(
        customer_note=note,
    )

    data = await state.get_data()

    try:
        result = await create_evaluation(
            telegram_user_id=message.from_user.id,
            brand=data["brand"],
            model=data["model"],
            storage=data["storage"],
            ram=data["ram"],
            color=data["color"],
            battery_percent=data["battery_percent"],
            appearance_condition=data["appearance_condition"],
            technical_condition=data["technical_condition"],
            repair_status=data["repair_status"],
            parts_status=data["parts_status"],
            registration_status=data["registration_status"],
            risk_level="low",
            has_box=data["has_box"],
            has_accessories=data["has_accessories"],
            market_price=Decimal(data["market_price"]),
            customer_note=data.get("customer_note") or None,
        )
    except Exception:
        await message.answer(
            "❌ هنگام محاسبه کارشناسی خطایی رخ داد.\n"
            "درخواست ثبت نشد. لطفاً دوباره تلاش کن."
        )
        return

    result_data = {
        "brand": data["brand"],
        "model": data["model"],
        "storage": data["storage"],
        "ram": data["ram"],
        "color": data["color"],
        "estimated_value": result.estimated_value,
        "purchase_price": result.purchase_price,
        "max_purchase_price": result.max_purchase_price,
        "selling_price": result.selling_price,
        "expected_profit": result.expected_profit,
        "score": result.score,
        "recommendation": result.recommendation,
        "explanation": result.explanation,
    }

    await state.update_data(
        evaluation_id=result.id,
    )

    await message.answer(
        format_result(result_data),
        reply_markup=result_keyboard(),
    )


# ============================================================
# Submit
# ============================================================

@router.callback_query(F.data == "smart_price:submit")
async def submit_evaluation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    data = await state.get_data()

    evaluation_id = data.get("evaluation_id")

    if not evaluation_id:
        await callback.answer(
            "درخواست کارشناسی پیدا نشد.",
            show_alert=True,
        )
        await state.clear()
        return

    await callback.message.edit_reply_markup(
        reply_markup=None,
    )

    await callback.message.answer(
        "📨 <b>درخواست کارشناسی ارسال شد.</b>\n\n"
        f"🆔 کد درخواست: <code>{evaluation_id}</code>\n\n"
        "⏳ درخواست برای مدیریت VIRA MOBILE ارسال شد.\n"
        "قیمت نهایی فقط پس از بررسی و تأیید مدیریت معتبر خواهد بود."
    )

    await callback.answer("درخواست ارسال شد.")
    await state.clear()


# ============================================================
# Cancel result
# ============================================================

@router.callback_query(F.data == "smart_price:cancel")
async def cancel_evaluation(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    await state.clear()

    try:
        await callback.message.edit_reply_markup(
            reply_markup=None,
        )
    except Exception:
        pass

    await callback.message.answer(
        "❌ درخواست کارشناسی لغو شد."
    )

    await callback.answer("لغو شد.")


# ============================================================
# Global cancellation while in FSM
# ============================================================

@router.message(SmartPricingStates, F.text == "❌ لغو کارشناسی")
async def global_smart_pricing_cancel(
    message: Message,
    state: FSMContext,
) -> None:
    await cancel_flow(message, state)
