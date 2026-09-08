"""
VIRA MOBILE
Purchase Evaluation Service

این سرویس درخواست کارشناسی را مدیریت می‌کند.

نکته:
AI/موتور کارشناسی فقط پیشنهاد می‌دهد.
تأیید نهایی معامله فقط توسط مدیریت انجام می‌شود.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.database.connection import AsyncSessionLocal
from app.services.smart_pricing.calculator import (
    PricingInput,
    PricingResult,
    calculate_price,
)
from app.services.smart_pricing.models import (
    EvaluationStatus,
    PurchaseEvaluation,
)


# ==========================================================
# Create Evaluation
# ==========================================================

async def create_evaluation(
    *,
    telegram_user_id: int,
    brand: str,
    model: str,
    storage: str | None = None,
    ram: str | None = None,
    color: str | None = None,
    battery_percent: int | None = None,
    appearance_condition: str = "good",
    technical_condition: str = "good",
    repair_status: str = "none",
    parts_status: str = "original",
    registration_status: str = "registered",
    risk_level: str = "low",
    has_box: bool = True,
    has_accessories: bool = True,
    market_price: Decimal = Decimal("0"),
    profit_percent: Decimal = Decimal("10"),
    purchase_discount_percent: Decimal = Decimal("12"),
    customer_note: str | None = None,
) -> PurchaseEvaluation:

    pricing_input = PricingInput(
        market_price=market_price,
        battery_percent=battery_percent,
        appearance_condition=appearance_condition,
        technical_condition=technical_condition,
        repair_status=repair_status,
        parts_status=parts_status,
        registration_status=registration_status,
        risk_level=risk_level,
        has_box=has_box,
        has_accessories=has_accessories,
        profit_percent=profit_percent,
        purchase_discount_percent=(
            purchase_discount_percent
        ),
    )

    result = calculate_price(
        pricing_input
    )

    evaluation = PurchaseEvaluation(
        telegram_user_id=telegram_user_id,
        brand=brand.strip(),
        model=model.strip(),
        storage=storage,
        ram=ram,
        color=color,
        battery_percent=battery_percent,
        appearance_condition=appearance_condition,
        technical_condition=technical_condition,
        repair_status=repair_status,
        parts_status=parts_status,
        registration_status=registration_status,
        risk_level=risk_level,
        has_box=has_box,
        has_accessories=has_accessories,
        market_price=result.market_price,
        estimated_value=result.estimated_value,
        purchase_price=result.purchase_price,
        max_purchase_price=result.max_purchase_price,
        selling_price=result.selling_price,
        expected_profit=result.expected_profit,
        profit_percent=result.profit_percent,
        score=result.score,
        recommendation=result.recommendation,
        ai_explanation=result.explanation,
        customer_note=customer_note,
        status=EvaluationStatus.PENDING.value,
    )

    async with AsyncSessionLocal() as session:

        session.add(evaluation)

        await session.commit()

        await session.refresh(
            evaluation
        )

        return evaluation


# ==========================================================
# Get Evaluation
# ==========================================================

async def get_evaluation(
    evaluation_id: int,
) -> PurchaseEvaluation | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(PurchaseEvaluation).where(
                PurchaseEvaluation.id
                == evaluation_id
            )
        )

        return result.scalar_one_or_none()


# ==========================================================
# Pending Evaluations
# ==========================================================

async def get_pending_evaluations(
    limit: int = 30,
) -> list[PurchaseEvaluation]:

    limit = max(
        1,
        min(
            100,
            int(limit),
        ),
    )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(PurchaseEvaluation)
            .where(
                PurchaseEvaluation.status
                == EvaluationStatus.PENDING.value
            )
            .order_by(
                PurchaseEvaluation.created_at.desc()
            )
            .limit(limit)
        )

        return list(
            result.scalars().all()
        )


# ==========================================================
# Approve
# ==========================================================

async def approve_evaluation(
    evaluation_id: int,
    admin_id: int,
    admin_note: str | None = None,
) -> PurchaseEvaluation | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(PurchaseEvaluation).where(
                PurchaseEvaluation.id
                == evaluation_id
            )
        )

        evaluation = (
            result.scalar_one_or_none()
        )

        if evaluation is None:
            return None

        if evaluation.status != (
            EvaluationStatus.PENDING.value
        ):
            return evaluation

        evaluation.status = (
            EvaluationStatus.APPROVED.value
        )

        evaluation.reviewed_by = admin_id

        evaluation.reviewed_at = (
            datetime.now(timezone.utc)
        )

        evaluation.admin_note = admin_note

        await session.commit()

        await session.refresh(
            evaluation
        )

        return evaluation


# ==========================================================
# Reject
# ==========================================================

async def reject_evaluation(
    evaluation_id: int,
    admin_id: int,
    admin_note: str | None = None,
) -> PurchaseEvaluation | None:

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(PurchaseEvaluation).where(
                PurchaseEvaluation.id
                == evaluation_id
            )
        )

        evaluation = (
            result.scalar_one_or_none()
        )

        if evaluation is None:
            return None

        if evaluation.status != (
            EvaluationStatus.PENDING.value
        ):
            return evaluation

        evaluation.status = (
            EvaluationStatus.REJECTED.value
        )

        evaluation.reviewed_by = admin_id

        evaluation.reviewed_at = (
            datetime.now(timezone.utc)
        )

        evaluation.admin_note = admin_note

        await session.commit()

        await session.refresh(
            evaluation
        )

        return evaluation


# ==========================================================
# Modify Price
# ==========================================================

async def modify_evaluation_price(
    evaluation_id: int,
    admin_id: int,
    purchase_price: Decimal,
    selling_price: Decimal,
    admin_note: str | None = None,
) -> PurchaseEvaluation | None:

    purchase_price = Decimal(
        str(purchase_price)
    )

    selling_price = Decimal(
        str(selling_price)
    )

    if purchase_price <= 0:
        raise ValueError(
            "قیمت خرید باید بیشتر از صفر باشد."
        )

    if selling_price <= 0:
        raise ValueError(
            "قیمت فروش باید بیشتر از صفر باشد."
        )

    if selling_price <= purchase_price:
        raise ValueError(
            "قیمت فروش باید بیشتر از قیمت خرید باشد."
        )

    async with AsyncSessionLocal() as session:

        result = await session.execute(
            select(PurchaseEvaluation).where(
                PurchaseEvaluation.id
                == evaluation_id
            )
        )

        evaluation = (
            result.scalar_one_or_none()
        )

        if evaluation is None:
            return None

        if evaluation.status != (
            EvaluationStatus.PENDING.value
        ):
            return evaluation

        evaluation.purchase_price = (
            purchase_price
        )

        evaluation.selling_price = (
            selling_price
        )

        evaluation.expected_profit = (
            selling_price
            - purchase_price
        )

        evaluation.profit_percent = (
            (
                evaluation.expected_profit
                / purchase_price
            )
            * Decimal("100")
        )

        evaluation.status = (
            EvaluationStatus.MODIFIED.value
        )

        evaluation.reviewed_by = admin_id

        evaluation.reviewed_at = (
            datetime.now(timezone.utc)
        )

        evaluation.admin_note = admin_note

        await session.commit()

        await session.refresh(
            evaluation
        )

        return evaluation


# ==========================================================
# Serialization
# ==========================================================

def evaluation_to_dict(
    evaluation: PurchaseEvaluation,
) -> dict[str, Any]:

    return {
        "id": evaluation.id,
        "telegram_user_id": (
            evaluation.telegram_user_id
        ),
        "brand": evaluation.brand,
        "model": evaluation.model,
        "storage": evaluation.storage,
        "ram": evaluation.ram,
        "color": evaluation.color,
        "battery_percent": (
            evaluation.battery_percent
        ),
        "appearance_condition": (
            evaluation.appearance_condition
        ),
        "technical_condition": (
            evaluation.technical_condition
        ),
        "repair_status": (
            evaluation.repair_status
        ),
        "parts_status": (
            evaluation.parts_status
        ),
        "registration_status": (
            evaluation.registration_status
        ),
        "risk_level": evaluation.risk_level,
        "has_box": evaluation.has_box,
        "has_accessories": (
            evaluation.has_accessories
        ),
        "market_price": str(
            evaluation.market_price
        ),
        "estimated_value": str(
            evaluation.estimated_value
        ),
        "purchase_price": str(
            evaluation.purchase_price
        ),
        "max_purchase_price": str(
            evaluation.max_purchase_price
        ),
        "selling_price": str(
            evaluation.selling_price
        ),
        "expected_profit": str(
            evaluation.expected_profit
        ),
        "profit_percent": str(
            evaluation.profit_percent
        ),
        "score": evaluation.score,
        "recommendation": (
            evaluation.recommendation
        ),
        "status": evaluation.status,
        "ai_explanation": (
            evaluation.ai_explanation
        ),
        "customer_note": (
            evaluation.customer_note
        ),
        "admin_note": evaluation.admin_note,
        "reviewed_by": evaluation.reviewed_by,
        "reviewed_at": (
            evaluation.reviewed_at.isoformat()
            if evaluation.reviewed_at
            else None
        ),
        "created_at": (
            evaluation.created_at.isoformat()
            if evaluation.created_at
            else None
        ),
    }
