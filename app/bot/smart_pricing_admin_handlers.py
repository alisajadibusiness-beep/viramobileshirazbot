from __future__ import annotations

import logging
from decimal import Decimal

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from app.bot.admin_handlers import is_admin
from app.services.smart_pricing import (
    EvaluationStatus,
    approve_evaluation,
    get_evaluation,
    get_pending_evaluations,
    reject_evaluation,
)

logger = logging.getLogger(__name__)

router = Router(name="smart_pricing_admin")


# ============================================================
# Helpers
# ============================================================

def format_price(value: Decimal | int | float | str | None) -> str:
    if value is None:
        return "-"

    try:
        amount = Decimal(str(value))
        return f"{amount:,.0f}"
    except Exception:
        return str(value)


def condition_label(value: str | None) -> str:
    labels = {
        "excellent": "عالی",
        "very_good": "خیلی خوب",
        "good": "خوب",
        "fair": "متوسط",
        "poor": "ضعیف",
        "none": "بدون تعمیر",
        "minor": "تعمیر جزئی",
        "major": "تعمیر اساسی",
        "unknown": "نامشخص",
        "original": "اصلی",
        "mixed": "ترکیبی",
        "non_original": "غیراصلی",
        "registered": "رجیستر شده",
        "not_registered": "رجیستر نشده",
        "low": "کم",
        "medium": "متوسط",
        "high": "زیاد",
    }

    return labels.get(value or "", value or "-")


def status_label(status: str | None) -> str:
    labels = {
        EvaluationStatus.PENDING.value: "⏳ در انتظار مدیریت",
        EvaluationStatus.APPROVED.value: "✅ تأیید شده",
        EvaluationStatus.REJECTED.value: "❌ رد شده",
        EvaluationStatus.MODIFIED.value: "✏️ اصلاح شده",
    }

    return labels.get(status or "", status or "-")


def evaluation_keyboard(evaluation_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ تأیید خرید",
                    callback_data=f"smart_admin:approve:{evaluation_id}",
                ),
                InlineKeyboardButton(
                    text="❌ رد درخواست",
                    callback_data=f"smart_admin:reject:{evaluation_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🔄 بازگشت به درخواست‌ها",
                    callback_data="smart_admin:list",
                ),
            ],
        ]
    )


def back_to_list_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔄 درخواست‌های در انتظار",
                    callback_data="smart_admin:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ],
        ]
    )


def render_evaluation(evaluation) -> str:
    return (
        "🤖 <b>کارشناسی هوشمند خرید گوشی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>شناسه درخواست:</b> {evaluation.id}\n"
        f"👤 <b>شناسه مشتری:</b> <code>{evaluation.telegram_user_id}</code>\n\n"
        f"📱 <b>برند:</b> {evaluation.brand}\n"
        f"📲 <b>مدل:</b> {evaluation.model}\n"
        f"💾 <b>حافظه:</b> {evaluation.storage or '-'}\n"
        f"🧠 <b>رم:</b> {evaluation.ram or '-'}\n"
        f"🎨 <b>رنگ:</b> {evaluation.color or '-'}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "🔍 <b>وضعیت دستگاه</b>\n\n"
        f"🔋 سلامت باتری: "
        f"{evaluation.battery_percent if evaluation.battery_percent is not None else '-'}٪\n"
        f"✨ ظاهر: {condition_label(evaluation.appearance_condition)}\n"
        f"⚙️ فنی: {condition_label(evaluation.technical_condition)}\n"
        f"🔧 تعمیرات: {condition_label(evaluation.repair_status)}\n"
        f"🧩 قطعات: {condition_label(evaluation.parts_status)}\n"
        f"📡 رجیستری: {condition_label(evaluation.registration_status)}\n"
        f"📦 جعبه: {'دارد' if evaluation.has_box else 'ندارد'}\n"
        f"🎧 لوازم: {'دارد' if evaluation.has_accessories else 'ندارد'}\n"
        f"⚠️ ریسک: {condition_label(evaluation.risk_level)}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💰 <b>ارزیابی مالی</b>\n\n"
        f"📊 قیمت بازار: "
        f"<b>{format_price(evaluation.market_price)}</b> تومان\n"
        f"📉 ارزش برآوردی: "
        f"<b>{format_price(evaluation.estimated_value)}</b> تومان\n"
        f"🛒 قیمت پیشنهادی خرید: "
        f"<b>{format_price(evaluation.purchase_price)}</b> تومان\n"
        f"🔴 سقف خرید: "
        f"<b>{format_price(evaluation.max_purchase_price)}</b> تومان\n"
        f"🏷 قیمت پیشنهادی فروش: "
        f"<b>{format_price(evaluation.selling_price)}</b> تومان\n"
        f"💵 سود مورد انتظار: "
        f"<b>{format_price(evaluation.expected_profit)}</b> تومان\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"⭐ <b>امتیاز کارشناسی:</b> {evaluation.score}/100\n"
        f"📌 <b>پیشنهاد:</b> {evaluation.recommendation}\n"
        f"📋 <b>وضعیت:</b> {status_label(evaluation.status)}\n\n"
        f"🤖 <b>توضیح کارشناس:</b>\n"
        f"{evaluation.ai_explanation or '-'}\n\n"
        f"📝 <b>یادداشت مشتری:</b>\n"
        f"{evaluation.customer_note or '-'}"
    )


# ============================================================
# Admin smart pricing menu
# ============================================================

async def smart_pricing_admin_menu(message: Message) -> None:
    if not is_admin(message.from_user.id):
        await message.answer("⛔ دسترسی غیرمجاز.")
        return

    pending = await get_pending_evaluations(limit=30)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⏳ درخواست‌های در انتظار ({len(pending)})",
                    callback_data="smart_admin:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ],
        ]
    )

    await message.answer(
        "🤖 <b>کارشناس هوشمند خرید</b>\n\n"
        "از این بخش می‌توانی درخواست‌های کارشناسی گوشی را بررسی کنی.\n\n"
        "⚠️ هیچ خریدی بدون تأیید مدیریت نهایی نمی‌شود.",
        reply_markup=keyboard,
    )


# ============================================================
# Open admin smart pricing menu from callback
# ============================================================

@router.callback_query(F.data == "admin:smart_pricing")
async def admin_smart_pricing_callback(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    pending = await get_pending_evaluations(limit=30)

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"⏳ درخواست‌های در انتظار ({len(pending)})",
                    callback_data="smart_admin:list",
                )
            ],
            [
                InlineKeyboardButton(
                    text="⚙️ پنل مدیریت",
                    callback_data="admin:panel",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "🤖 <b>کارشناس هوشمند خرید</b>\n\n"
        f"تعداد درخواست‌های در انتظار بررسی: <b>{len(pending)}</b>\n\n"
        "⚠️ تأیید یا رد فقط توسط مدیریت انجام می‌شود.",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# Pending evaluations list
# ============================================================

@router.callback_query(F.data == "smart_admin:list")
async def admin_smart_pricing_list(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    evaluations = await get_pending_evaluations(limit=30)

    if not evaluations:
        await callback.message.edit_text(
            "🤖 <b>درخواست‌های کارشناسی</b>\n\n"
            "✅ در حال حاضر هیچ درخواست در انتظاری وجود ندارد.",
            reply_markup=back_to_list_keyboard(),
        )
        await callback.answer()
        return

    buttons = []

    for evaluation in evaluations:
        title = (
            f"📱 {evaluation.brand} {evaluation.model}"
            f" | {format_price(evaluation.purchase_price)}"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    text=title,
                    callback_data=f"smart_admin:view:{evaluation.id}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text="⚙️ پنل مدیریت",
                callback_data="admin:panel",
            )
        ]
    )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=buttons
    )

    await callback.message.edit_text(
        "🤖 <b>درخواست‌های کارشناسی در انتظار</b>\n\n"
        f"تعداد درخواست‌ها: <b>{len(evaluations)}</b>\n\n"
        "برای مشاهده جزئیات، درخواست موردنظر را انتخاب کن.",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# View evaluation
# ============================================================

@router.callback_query(F.data.startswith("smart_admin:view:"))
async def admin_view_evaluation(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    try:
        evaluation_id = int(
            callback.data.split(":")[-1]
        )
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    evaluation = await get_evaluation(evaluation_id)

    if evaluation is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    await callback.message.edit_text(
        render_evaluation(evaluation),
        reply_markup=evaluation_keyboard(evaluation.id),
    )

    await callback.answer()


# ============================================================
# Approve evaluation
# ============================================================

@router.callback_query(F.data.startswith("smart_admin:approve:"))
async def admin_approve_evaluation(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    try:
        evaluation_id = int(
            callback.data.split(":")[-1]
        )
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    evaluation = await get_evaluation(evaluation_id)

    if evaluation is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    if evaluation.status != EvaluationStatus.PENDING.value:
        await callback.answer(
            "این درخواست قبلاً تعیین تکلیف شده است.",
            show_alert=True,
        )
        return

    try:
        approved = await approve_evaluation(
            evaluation_id=evaluation_id,
            admin_id=callback.from_user.id,
            admin_note="تأیید توسط مدیریت",
        )

        if approved is None:
            await callback.answer(
                "تأیید درخواست انجام نشد.",
                show_alert=True,
            )
            return

        await callback.message.edit_text(
            "✅ <b>درخواست تأیید شد</b>\n\n"
            f"🆔 شناسه درخواست: <b>{evaluation_id}</b>\n"
            f"📱 {evaluation.brand} {evaluation.model}\n\n"
            f"🛒 قیمت خرید تأییدشده:\n"
            f"<b>{format_price(evaluation.purchase_price)}</b> تومان\n\n"
            f"🏷 قیمت فروش پیشنهادی:\n"
            f"<b>{format_price(evaluation.selling_price)}</b> تومان\n\n"
            "⚠️ این تأیید فقط مربوط به کارشناسی و قیمت پیشنهادی است "
            "و به‌تنهایی هیچ موجودی یا تراکنشی را تغییر نمی‌دهد.",
            reply_markup=back_to_list_keyboard(),
        )

        await callback.answer(
            "درخواست با موفقیت تأیید شد.",
        )

    except Exception:
        logger.exception(
            "Failed to approve evaluation %s",
            evaluation_id,
        )

        await callback.answer(
            "خطا هنگام تأیید درخواست.",
            show_alert=True,
        )


# ============================================================
# Reject confirmation
# ============================================================

@router.callback_query(F.data.startswith("smart_admin:reject:"))
async def admin_reject_evaluation_confirm(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    try:
        evaluation_id = int(
            callback.data.split(":")[-1]
        )
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    evaluation = await get_evaluation(evaluation_id)

    if evaluation is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    if evaluation.status != EvaluationStatus.PENDING.value:
        await callback.answer(
            "این درخواست قبلاً تعیین تکلیف شده است.",
            show_alert=True,
        )
        return

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ بله، رد شود",
                    callback_data=f"smart_admin:reject_confirm:{evaluation_id}",
                )
            ],
            [
                InlineKeyboardButton(
                    text="↩️ بازگشت",
                    callback_data=f"smart_admin:view:{evaluation_id}",
                )
            ],
        ]
    )

    await callback.message.edit_text(
        "⚠️ <b>رد درخواست</b>\n\n"
        f"آیا مطمئنی درخواست شماره <b>{evaluation_id}</b> رد شود؟\n\n"
        f"📱 {evaluation.brand} {evaluation.model}\n"
        f"💰 قیمت خرید پیشنهادی: "
        f"<b>{format_price(evaluation.purchase_price)}</b> تومان",
        reply_markup=keyboard,
    )

    await callback.answer()


# ============================================================
# Reject evaluation
# ============================================================

@router.callback_query(
    F.data.startswith("smart_admin:reject_confirm:")
)
async def admin_reject_evaluation(
    callback: CallbackQuery,
) -> None:
    if not is_admin(callback.from_user.id):
        await callback.answer(
            "⛔ دسترسی غیرمجاز.",
            show_alert=True,
        )
        return

    try:
        evaluation_id = int(
            callback.data.split(":")[-1]
        )
    except (TypeError, ValueError):
        await callback.answer(
            "شناسه درخواست نامعتبر است.",
            show_alert=True,
        )
        return

    evaluation = await get_evaluation(evaluation_id)

    if evaluation is None:
        await callback.answer(
            "درخواست پیدا نشد.",
            show_alert=True,
        )
        return

    if evaluation.status != EvaluationStatus.PENDING.value:
        await callback.answer(
            "این درخواست قبلاً تعیین تکلیف شده است.",
            show_alert=True,
        )
        return

    try:
        rejected = await reject_evaluation(
            evaluation_id=evaluation_id,
            admin_id=callback.from_user.id,
            admin_note="رد درخواست توسط مدیریت",
        )

        if rejected is None:
            await callback.answer(
                "رد درخواست انجام نشد.",
                show_alert=True,
            )
            return

        await callback.message.edit_text(
            "❌ <b>درخواست رد شد</b>\n\n"
            f"🆔 شناسه درخواست: <b>{evaluation_id}</b>\n"
            f"📱 {evaluation.brand} {evaluation.model}\n\n"
            "این درخواست دیگر در فهرست درخواست‌های در انتظار نمایش داده نمی‌شود.",
            reply_markup=back_to_list_keyboard(),
        )

        await callback.answer(
            "درخواست رد شد.",
        )

    except Exception:
        logger.exception(
            "Failed to reject evaluation %s",
            evaluation_id,
        )

        await callback.answer(
            "خطا هنگام رد درخواست.",
            show_alert=True,
        )


# ============================================================
# Text command for admin
# ============================================================

@router.message(F.text == "🤖 کارشناس هوشمند")
async def admin_smart_pricing_text(
    message: Message,
) -> None:
    if not is_admin(message.from_user.id):
        return

    await smart_pricing_admin_menu(message)
