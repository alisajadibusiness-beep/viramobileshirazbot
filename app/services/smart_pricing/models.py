"""
VIRA MOBILE
Smart Pricing Database Models
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.database.connection import Base


# ==========================================================
# Evaluation Status
# ==========================================================

class EvaluationStatus(str, Enum):

    PENDING = "PENDING"

    APPROVED = "APPROVED"

    REJECTED = "REJECTED"

    MODIFIED = "MODIFIED"


# ==========================================================
# Purchase Evaluation
# ==========================================================

class PurchaseEvaluation(Base):

    __tablename__ = "purchase_evaluations"

    # ------------------------------------------------------
    # Primary Key
    # ------------------------------------------------------

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    # ------------------------------------------------------
    # Customer
    # ------------------------------------------------------

    telegram_user_id: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )

    # ------------------------------------------------------
    # Product Information
    # ------------------------------------------------------

    brand: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    model: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )

    storage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    ram: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    color: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # ------------------------------------------------------
    # Device Condition
    # ------------------------------------------------------

    battery_percent: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    appearance_condition: Mapped[str] = mapped_column(
        String(50),
        default="good",
        nullable=False,
    )

    technical_condition: Mapped[str] = mapped_column(
        String(50),
        default="good",
        nullable=False,
    )

    repair_status: Mapped[str] = mapped_column(
        String(50),
        default="none",
        nullable=False,
    )

    parts_status: Mapped[str] = mapped_column(
        String(50),
        default="original",
        nullable=False,
    )

    registration_status: Mapped[str] = mapped_column(
        String(50),
        default="registered",
        nullable=False,
    )

    risk_level: Mapped[str] = mapped_column(
        String(50),
        default="low",
        nullable=False,
    )

    has_box: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    has_accessories: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # ------------------------------------------------------
    # Pricing
    # ------------------------------------------------------

    market_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    estimated_value: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    max_purchase_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    selling_price: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    expected_profit: Mapped[Decimal] = mapped_column(
        Numeric(15, 2),
        default=Decimal("0"),
        nullable=False,
    )

    profit_percent: Mapped[Decimal] = mapped_column(
        Numeric(7, 2),
        default=Decimal("0"),
        nullable=False,
    )

    # ------------------------------------------------------
    # AI / Evaluation
    # ------------------------------------------------------

    score: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )

    recommendation: Mapped[str] = mapped_column(
        String(100),
        default="نیازمند بررسی مدیریت",
        nullable=False,
    )

    ai_explanation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------
    # Customer Note
    # ------------------------------------------------------

    customer_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------
    # Management Review
    # ------------------------------------------------------

    status: Mapped[str] = mapped_column(
        String(30),
        default=EvaluationStatus.PENDING.value,
        nullable=False,
        index=True,
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    admin_note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # ------------------------------------------------------
    # Timestamps
    # ------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(
            timezone.utc
        ),
        onupdate=lambda: datetime.now(
            timezone.utc
        ),
        nullable=False,
    )
