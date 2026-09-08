"""
VIRA MOBILE
Smart Pricing Rules

قوانین پایه کارشناسی و قیمت‌گذاری.

این فایل عمداً مستقل از Telegram و Handlerهاست تا
بعداً بتوانیم منبع قیمت بازار یا مدل AI واقعی را
بدون تغییر ساختار اصلی اضافه کنیم.
"""

from __future__ import annotations

from decimal import Decimal


# ==========================================================
# Default Pricing Settings
# ==========================================================

DEFAULT_PROFIT_PERCENT = Decimal("10")
DEFAULT_MAX_PURCHASE_DISCOUNT = Decimal("12")


# ==========================================================
# Battery Rules
# ==========================================================

BATTERY_DEDUCTIONS = [
    (Decimal("95"), Decimal("0")),
    (Decimal("90"), Decimal("1")),
    (Decimal("85"), Decimal("2.5")),
    (Decimal("80"), Decimal("4")),
    (Decimal("75"), Decimal("6")),
    (Decimal("0"), Decimal("8")),
]


# ==========================================================
# Appearance Rules
# ==========================================================

APPEARANCE_DEDUCTIONS = {
    "excellent": Decimal("0"),
    "very_good": Decimal("2"),
    "good": Decimal("4"),
    "fair": Decimal("7"),
    "poor": Decimal("12"),
}


# ==========================================================
# Technical Rules
# ==========================================================

TECHNICAL_DEDUCTIONS = {
    "excellent": Decimal("0"),
    "good": Decimal("2"),
    "fair": Decimal("5"),
    "poor": Decimal("10"),
}


# ==========================================================
# Repair Rules
# ==========================================================

REPAIR_DEDUCTIONS = {
    "none": Decimal("0"),
    "minor": Decimal("3"),
    "major": Decimal("8"),
    "unknown": Decimal("10"),
}


# ==========================================================
# Original Parts Rules
# ==========================================================

PARTS_DEDUCTIONS = {
    "original": Decimal("0"),
    "mixed": Decimal("5"),
    "non_original": Decimal("10"),
    "unknown": Decimal("8"),
}


# ==========================================================
# Box / Accessories
# ==========================================================

BOX_ADJUSTMENT = Decimal("1")

ACCESSORIES_ADJUSTMENT = Decimal("1")


# ==========================================================
# Registration
# ==========================================================

REGISTRATION_DEDUCTIONS = {
    "registered": Decimal("0"),
    "not_registered": Decimal("8"),
    "unknown": Decimal("5"),
}


# ==========================================================
# Risk
# ==========================================================

RISK_ADJUSTMENTS = {
    "low": Decimal("0"),
    "medium": Decimal("2"),
    "high": Decimal("5"),
}


# ==========================================================
# Helpers
# ==========================================================

def clamp_percent(value: Decimal) -> Decimal:
    """
    محدود کردن درصد بین 0 تا 100.
    """
    if value < Decimal("0"):
        return Decimal("0")

    if value > Decimal("100"):
        return Decimal("100")

    return value


def get_battery_deduction(battery_percent: int | None) -> Decimal:
    """
    محاسبه درصد افت ارزش بر اساس سلامت باتری.
    """

    if battery_percent is None:
        return Decimal("5")

    try:
        battery = Decimal(str(battery_percent))
    except Exception:
        return Decimal("5")

    battery = max(
        Decimal("0"),
        min(Decimal("100"), battery),
    )

    for threshold, deduction in BATTERY_DEDUCTIONS:
        if battery >= threshold:
            return deduction

    return Decimal("8")


def get_appearance_deduction(
    condition: str | None,
) -> Decimal:
    """
    محاسبه افت ارزش ظاهری.
    """

    normalized = str(condition or "").strip().lower()

    aliases = {
        "عالی": "excellent",
        "very good": "very_good",
        "خیلی خوب": "very_good",
        "بسیار خوب": "very_good",
        "خوب": "good",
        "متوسط": "fair",
        "ضعیف": "poor",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return APPEARANCE_DEDUCTIONS.get(
        normalized,
        Decimal("5"),
    )


def get_technical_deduction(
    condition: str | None,
) -> Decimal:
    """
    محاسبه افت ارزش فنی.
    """

    normalized = str(condition or "").strip().lower()

    aliases = {
        "عالی": "excellent",
        "خوب": "good",
        "متوسط": "fair",
        "ضعیف": "poor",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return TECHNICAL_DEDUCTIONS.get(
        normalized,
        Decimal("3"),
    )


def get_repair_deduction(
    repair_status: str | None,
) -> Decimal:
    """
    محاسبه افت ناشی از تعمیر.
    """

    normalized = str(
        repair_status or ""
    ).strip().lower()

    aliases = {
        "ندارد": "none",
        "بدون تعمیر": "none",
        "جزئی": "minor",
        "عمده": "major",
        "نامشخص": "unknown",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return REPAIR_DEDUCTIONS.get(
        normalized,
        Decimal("5"),
    )


def get_parts_deduction(
    parts_status: str | None,
) -> Decimal:
    """
    محاسبه افت ناشی از قطعات غیر اصلی.
    """

    normalized = str(
        parts_status or ""
    ).strip().lower()

    aliases = {
        "اصلی": "original",
        "اورجینال": "original",
        "ترکیبی": "mixed",
        "غیراصلی": "non_original",
        "غیر اصلی": "non_original",
        "نامشخص": "unknown",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return PARTS_DEDUCTIONS.get(
        normalized,
        Decimal("5"),
    )


def get_registration_deduction(
    registration: str | None,
) -> Decimal:
    """
    محاسبه افت ناشی از وضعیت رجیستری.
    """

    normalized = str(
        registration or ""
    ).strip().lower()

    aliases = {
        "دارد": "registered",
        "رجیستر": "registered",
        "رجیستر شده": "registered",
        "ندارد": "not_registered",
        "رجیستر نیست": "not_registered",
        "نامشخص": "unknown",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return REGISTRATION_DEDUCTIONS.get(
        normalized,
        Decimal("5"),
    )


def get_risk_adjustment(
    risk_level: str | None,
) -> Decimal:
    """
    افت ارزش ناشی از ریسک معامله.
    """

    normalized = str(
        risk_level or ""
    ).strip().lower()

    aliases = {
        "کم": "low",
        "متوسط": "medium",
        "زیاد": "high",
        "بالا": "high",
    }

    normalized = aliases.get(
        normalized,
        normalized,
    )

    return RISK_ADJUSTMENTS.get(
        normalized,
        Decimal("2"),
    )


def round_price(
    value: Decimal,
    step: Decimal = Decimal("100000"),
) -> Decimal:
    """
    گرد کردن قیمت برای نمایش تجاری.

    پیش‌فرض: نزدیک‌ترین 100 هزار تومان.
    """

    if value <= 0:
        return Decimal("0")

    quotient = (
        value / step
    ).quantize(
        Decimal("1")
    )

    remainder = (
        value % step
    )

    if remainder >= step / Decimal("2"):
        quotient += Decimal("1")

    return quotient * step
