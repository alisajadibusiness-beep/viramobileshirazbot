"""
VIRA MOBILE
Smart Pricing Database Registration

این فایل مدل‌های کارشناسی را به SQLAlchemy معرفی می‌کند.
"""

from app.services.smart_pricing.models import (
    EvaluationStatus,
    PurchaseEvaluation,
)

__all__ = [
    "EvaluationStatus",
    "PurchaseEvaluation",
]
