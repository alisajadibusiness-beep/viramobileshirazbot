"""
VIRA MOBILE
Smart Pricing Calculator

موتور محاسبه:
Market Price
      ↓
Adjustments
      ↓
Estimated Value
      ↓
Purchase Price
      ↓
Selling Price
      ↓
Profit
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.services.smart_pricing.rules import (
    DEFAULT_MAX_PURCHASE_DISCOUNT,
    DEFAULT_PROFIT_PERCENT,
    get_appearance_deduction,
    get_battery_deduction,
    get_parts_deduction,
    get_registration_deduction,
    get_repair_deduction,
    get_risk_adjustment,
    round_price,
)


# ==========================================================
# Input
# ==========================================================

@dataclass(slots=True)
class PricingInput:
    market_price: Decimal

    battery_percent: int | None = None

    appearance_condition: str = "good"

    technical_condition: str = "good"

    repair_status: str = "none"

    parts_status: str = "original"

    registration_status: str = "registered"

    risk_level: str = "low"

    has_box: bool = True

    has_accessories: bool = True

    profit_percent: Decimal = (
        DEFAULT_PROFIT_PERCENT
    )

    purchase_discount_percent: Decimal = (
        DEFAULT_MAX_PURCHASE_DISCOUNT
    )


# ==========================================================
# Result
# ==========================================================

@dataclass(slots=True)
class PricingResult:
    market_price: Decimal

    estimated_value: Decimal

    purchase_price: Decimal

    max_purchase_price: Decimal

    selling_price: Decimal

    expected_profit: Decimal

    profit_percent: Decimal

    total_adjustment_percent: Decimal

    risk_level: str

    score: int

    recommendation: str

    explanation: str


# ==========================================================
# Decimal Helpers
# ==========================================================

def to_decimal(
    value: Decimal | int | float | str,
) -> Decimal:
    try:
        result = Decimal(str(value))

        if not result.is_finite():
            raise InvalidOperation

        return result

    except (
        InvalidOperation,
        ValueError,
        TypeError,
    ):
        raise ValueError(
            "مقدار عددی نامعتبر است."
        )


# ==========================================================
# Main Calculator
# ==========================================================

def calculate_price(
    data: PricingInput,
) -> PricingResult:

    market_price = to_decimal(
        data.market_price
    )

    if market_price <= 0:
        raise ValueError(
            "قیمت بازار باید بیشتر از صفر باشد."
        )

    profit_percent = max(
        Decimal("0"),
        min(
            Decimal("100"),
            to_decimal(
                data.profit_percent
            ),
        ),
    )

    purchase_discount = max(
        Decimal("0"),
        min(
            Decimal("50"),
            to_decimal(
                data.purchase_discount_percent
            ),
        ),
    )

    # ------------------------------------------------------
    # Adjustments
    # ------------------------------------------------------

    deductions = Decimal("0")

    battery_deduction = (
        get_battery_deduction(
            data.battery_percent
        )
    )

    appearance_deduction = (
        get_appearance_deduction(
            data.appearance_condition
        )
    )

    technical_deduction = (
        get_technical_deduction_safe(
            data.technical_condition
        )
    )

    repair_deduction = (
        get_repair_deduction(
            data.repair_status
        )
    )

    parts_deduction = (
        get_parts_deduction(
            data.parts_status
        )
    )

    registration_deduction = (
        get_registration_deduction(
            data.registration_status
        )
    )

    risk_adjustment = (
        get_risk_adjustment(
            data.risk_level
        )
    )

    deductions += battery_deduction
    deductions += appearance_deduction
    deductions += technical_deduction
    deductions += repair_deduction
    deductions += parts_deduction
    deductions += registration_deduction
    deductions += risk_adjustment

    # ------------------------------------------------------
    # Box / Accessories
    # ------------------------------------------------------

    if not data.has_box:
        deductions += Decimal("1")

    if not data.has_accessories:
        deductions += Decimal("1")

    # ------------------------------------------------------
    # Limit total deduction
    # ------------------------------------------------------

    deductions = min(
        deductions,
        Decimal("50"),
    )

    # ------------------------------------------------------
    # Estimated Market Value
    # ------------------------------------------------------

    estimated_value = (
        market_price
        * (
            Decimal("100")
            - deductions
        )
        / Decimal("100")
    )

    estimated_value = round_price(
        estimated_value
    )

    # ------------------------------------------------------
    # Purchase Price
    # ------------------------------------------------------

    purchase_price = (
        estimated_value
        * (
            Decimal("100")
            - purchase_discount
        )
        / Decimal("100")
    )

    purchase_price = round_price(
        purchase_price
    )

    # ------------------------------------------------------
    # Maximum Purchase
    # ------------------------------------------------------

    max_purchase_price = (
        estimated_value
        * Decimal("92")
        / Decimal("100")
    )

    max_purchase_price = round_price(
        max_purchase_price
    )

    # ------------------------------------------------------
    # Selling Price
    # ------------------------------------------------------

    selling_price = (
        purchase_price
        * (
            Decimal("100")
            + profit_percent
        )
        / Decimal("100")
    )

    selling_price = round_price(
        selling_price
    )

    # ------------------------------------------------------
    # Profit
    # ------------------------------------------------------

    expected_profit = (
        selling_price
        - purchase_price
    )

    if purchase_price > 0:
        actual_profit_percent = (
            expected_profit
            / purchase_price
            * Decimal("100")
        )
    else:
        actual_profit_percent = Decimal("0")

    # ------------------------------------------------------
    # Score
    # ------------------------------------------------------

    score = calculate_score(
        battery_percent=data.battery_percent,
        appearance=data.appearance_condition,
        technical=data.technical_condition,
        repair=data.repair_status,
        parts=data.parts_status,
        registration=data.registration_status,
        risk=data.risk_level,
    )

    # ------------------------------------------------------
    # Recommendation
    # ------------------------------------------------------

    if score >= 85:
        recommendation = "خرید بسیار مناسب"

    elif score >= 70:
        recommendation = "خرید مناسب"

    elif score >= 55:
        recommendation = "نیازمند بررسی مدیریت"

    else:
        recommendation = "خرید پرریسک"

    # ------------------------------------------------------
    # Explanation
    # ------------------------------------------------------

    explanation = (
        "قیمت پیشنهادی بر اساس قیمت بازار اعلام‌شده، "
        "سلامت باتری، وضعیت ظاهری و فنی، تعمیرات، "
        "قطعات، رجیستری، لوازم و سطح ریسک معامله محاسبه شده است."
    )

    return PricingResult(
        market_price=market_price,
        estimated_value=estimated_value,
        purchase_price=purchase_price,
        max_purchase_price=max_purchase_price,
        selling_price=selling_price,
        expected_profit=expected_profit,
        profit_percent=actual_profit_percent,
        total_adjustment_percent=deductions,
        risk_level=data.risk_level,
        score=score,
        recommendation=recommendation,
        explanation=explanation,
    )


# ==========================================================
# Technical Condition Adapter
# ==========================================================

def get_technical_deduction_safe(
    condition: str | None,
) -> Decimal:

    from app.services.smart_pricing.rules import (
        get_technical_deduction,
    )

    return get_technical_deduction(
        condition
    )


# ==========================================================
# Score
# ==========================================================

def calculate_score(
    *,
    battery_percent: int | None,
    appearance: str,
    technical: str,
    repair: str,
    parts: str,
    registration: str,
    risk: str,
) -> int:

    score = 100

    # Battery
    if battery_percent is not None:

        if battery_percent >= 95:
            score -= 0

        elif battery_percent >= 90:
            score -= 3

        elif battery_percent >= 85:
            score -= 7

        elif battery_percent >= 80:
            score -= 12

        elif battery_percent >= 75:
            score -= 18

        else:
            score -= 25

    else:
        score -= 8

    # Appearance
    appearance_map = {
        "excellent": 0,
        "very_good": 3,
        "good": 7,
        "fair": 14,
        "poor": 25,
    }

    score -= appearance_map.get(
        str(appearance).lower(),
        10,
    )

    # Technical
    technical_map = {
        "excellent": 0,
        "good": 4,
        "fair": 12,
        "poor": 30,
    }

    score -= technical_map.get(
        str(technical).lower(),
        10,
    )

    # Repair
    repair_map = {
        "none": 0,
        "minor": 5,
        "major": 15,
        "unknown": 10,
    }

    score -= repair_map.get(
        str(repair).lower(),
        10,
    )

    # Parts
    parts_map = {
        "original": 0,
        "mixed": 8,
        "non_original": 18,
        "unknown": 10,
    }

    score -= parts_map.get(
        str(parts).lower(),
        10,
    )

    # Registration
    registration_map = {
        "registered": 0,
        "not_registered": 15,
        "unknown": 8,
    }

    score -= registration_map.get(
        str(registration).lower(),
        8,
    )

    # Risk
    risk_map = {
        "low": 0,
        "medium": 5,
        "high": 15,
    }

    score -= risk_map.get(
        str(risk).lower(),
        8,
    )

    return max(
        0,
        min(
            100,
            score,
        ),
    )
