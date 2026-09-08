from __future__ import annotations

from datetime import datetime, time
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Customer,
    InventoryStatus,
    InventoryUnit,
    Order,
    OrderItem,
    OrderStatus,
    Product,
)


# ============================================================
# Helpers
# ============================================================


def _enum_value(value) -> str:
    """
    Return enum value safely.

    Supports both Enum instances and plain strings.
    """
    return getattr(value, "value", value)


def _decimal(value) -> Decimal:
    """
    Convert database numeric values safely to Decimal.
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, Decimal):
        return value

    return Decimal(str(value))


def _start_of_today() -> datetime:
    """
    Return today's local midnight.
    """
    now = datetime.now()
    return datetime.combine(now.date(), time.min)


# ============================================================
# Product Statistics
# ============================================================


async def get_product_statistics(
    session: AsyncSession,
) -> dict[str, int]:
    """
    Return product statistics.
    """

    total_result = await session.execute(
        select(func.count(Product.id))
    )
    total = total_result.scalar_one() or 0

    active_result = await session.execute(
        select(func.count(Product.id)).where(
            Product.is_active.is_(True)
        )
    )
    active = active_result.scalar_one() or 0

    inactive = total - active

    featured_result = await session.execute(
        select(func.count(Product.id)).where(
            Product.is_featured.is_(True),
            Product.is_active.is_(True),
        )
    )
    featured = featured_result.scalar_one() or 0

    return {
        "total": int(total),
        "active": int(active),
        "inactive": int(inactive),
        "featured": int(featured),
    }


# ============================================================
# Inventory Statistics
# ============================================================


async def get_inventory_statistics(
    session: AsyncSession,
) -> dict[str, int]:
    """
    Return inventory statistics.

    InventoryUnit is treated as the actual physical stock unit.
    """

    total_result = await session.execute(
        select(func.count(InventoryUnit.id))
    )
    total = total_result.scalar_one() or 0

    available_result = await session.execute(
        select(func.count(InventoryUnit.id)).where(
            InventoryUnit.status == _enum_value(
                InventoryStatus.AVAILABLE
            )
        )
    )
    available = available_result.scalar_one() or 0

    reserved_result = await session.execute(
        select(func.count(InventoryUnit.id)).where(
            InventoryUnit.status == _enum_value(
                InventoryStatus.RESERVED
            )
        )
    )
    reserved = reserved_result.scalar_one() or 0

    sold_result = await session.execute(
        select(func.count(InventoryUnit.id)).where(
            InventoryUnit.status == _enum_value(
                InventoryStatus.SOLD
            )
        )
    )
    sold = sold_result.scalar_one() or 0

    damaged_result = await session.execute(
        select(func.count(InventoryUnit.id)).where(
            InventoryUnit.status == _enum_value(
                InventoryStatus.DAMAGED
            )
        )
    )
    damaged = damaged_result.scalar_one() or 0

    return {
        "total": int(total),
        "available": int(available),
        "reserved": int(reserved),
        "sold": int(sold),
        "damaged": int(damaged),
    }


# ============================================================
# Order Statistics
# ============================================================


async def get_order_statistics(
    session: AsyncSession,
) -> dict[str, int]:
    """
    Return order statistics grouped by status.
    """

    result = await session.execute(
        select(
            Order.status,
            func.count(Order.id),
        ).group_by(Order.status)
    )

    rows = result.all()

    statistics: dict[str, int] = {
        "total": 0,
        "pending": 0,
        "payment_pending": 0,
        "paid": 0,
        "processing": 0,
        "ready": 0,
        "shipped": 0,
        "delivered": 0,
        "cancelled": 0,
        "refunded": 0,
    }

    for status, count in rows:
        count = int(count or 0)
        status_value = _enum_value(status)

        statistics["total"] += count

        if status_value == _enum_value(OrderStatus.PENDING):
            statistics["pending"] = count

        elif status_value == _enum_value(
            OrderStatus.PAYMENT_PENDING
        ):
            statistics["payment_pending"] = count

        elif status_value == _enum_value(OrderStatus.PAID):
            statistics["paid"] = count

        elif status_value == _enum_value(
            OrderStatus.PROCESSING
        ):
            statistics["processing"] = count

        elif status_value == _enum_value(OrderStatus.READY):
            statistics["ready"] = count

        elif status_value == _enum_value(OrderStatus.SHIPPED):
            statistics["shipped"] = count

        elif status_value == _enum_value(
            OrderStatus.DELIVERED
        ):
            statistics["delivered"] = count

        elif status_value == _enum_value(
            OrderStatus.CANCELLED
        ):
            statistics["cancelled"] = count

        elif status_value == _enum_value(
            OrderStatus.REFUNDED
        ):
            statistics["refunded"] = count

    return statistics


# ============================================================
# Customer Statistics
# ============================================================


async def get_customer_statistics(
    session: AsyncSession,
) -> dict[str, int]:
    """
    Return customer statistics.
    """

    total_result = await session.execute(
        select(func.count(Customer.id))
    )

    total = total_result.scalar_one() or 0

    return {
        "total": int(total),
    }


# ============================================================
# Sales Statistics
# ============================================================


async def get_sales_statistics(
    session: AsyncSession,
) -> dict[str, Decimal | int]:
    """
    Return sales statistics.

    Only PAID, PROCESSING, READY, SHIPPED and DELIVERED
    orders are considered successful sales.

    Cancelled/refunded orders are excluded.
    """

    successful_statuses = [
        _enum_value(OrderStatus.PAID),
        _enum_value(OrderStatus.PROCESSING),
        _enum_value(OrderStatus.READY),
        _enum_value(OrderStatus.SHIPPED),
        _enum_value(OrderStatus.DELIVERED),
    ]

    # --------------------------------------------------------
    # Total sales
    # --------------------------------------------------------

    total_sales_result = await session.execute(
        select(
            func.coalesce(
                func.sum(Order.total_amount),
                0,
            )
        ).where(
            Order.status.in_(successful_statuses)
        )
    )

    total_sales = _decimal(
        total_sales_result.scalar_one()
    )

    # --------------------------------------------------------
    # Number of successful orders
    # --------------------------------------------------------

    successful_orders_result = await session.execute(
        select(func.count(Order.id)).where(
            Order.status.in_(successful_statuses)
        )
    )

    successful_orders = (
        successful_orders_result.scalar_one() or 0
    )

    # --------------------------------------------------------
    # Today's sales
    # --------------------------------------------------------

    today_start = _start_of_today()

    today_sales_result = await session.execute(
        select(
            func.coalesce(
                func.sum(Order.total_amount),
                0,
            )
        ).where(
            Order.status.in_(successful_statuses),
            Order.created_at >= today_start,
        )
    )

    today_sales = _decimal(
        today_sales_result.scalar_one()
    )

    # --------------------------------------------------------
    # Today's successful orders
    # --------------------------------------------------------

    today_orders_result = await session.execute(
        select(func.count(Order.id)).where(
            Order.status.in_(successful_statuses),
            Order.created_at >= today_start,
        )
    )

    today_orders = (
        today_orders_result.scalar_one() or 0
    )

    return {
        "total_sales": total_sales,
        "successful_orders": int(successful_orders),
        "today_sales": today_sales,
        "today_orders": int(today_orders),
    }


# ============================================================
# Low Stock
# ============================================================


async def get_low_stock_products(
    session: AsyncSession,
    threshold: int = 2,
) -> list[dict]:
    """
    Return products whose available physical inventory
    is at or below the given threshold.

    Example:
        threshold=2

    means products with 0, 1 or 2 available units
    are returned.
    """

    available_status = _enum_value(
        InventoryStatus.AVAILABLE
    )

    result = await session.execute(
        select(
            Product.id,
            Product.brand,
            Product.model,
            func.count(InventoryUnit.id).label(
                "stock_count"
            ),
        )
        .join(
            InventoryUnit,
            InventoryUnit.product_id == Product.id,
            isouter=True,
        )
        .where(
            Product.is_active.is_(True),
            (
                (InventoryUnit.status == available_status)
                | (InventoryUnit.id.is_(None))
            ),
        )
        .group_by(
            Product.id,
            Product.brand,
            Product.model,
        )
        .having(
            func.count(InventoryUnit.id) <= threshold
        )
        .order_by(
            func.count(InventoryUnit.id).asc()
        )
    )

    rows = result.all()

    return [
        {
            "id": int(row.id),
            "brand": row.brand,
            "model": row.model,
            "stock": int(row.stock_count or 0),
        }
        for row in rows
    ]


# ============================================================
# Complete Dashboard
# ============================================================


async def get_admin_dashboard(
    session: AsyncSession,
) -> dict:
    """
    Return all dashboard statistics in one structure.

    This is the main function that the admin handler
    should call.
    """

    products = await get_product_statistics(session)

    inventory = await get_inventory_statistics(session)

    orders = await get_order_statistics(session)

    customers = await get_customer_statistics(session)

    sales = await get_sales_statistics(session)

    low_stock = await get_low_stock_products(
        session,
        threshold=2,
    )

    return {
        "products": products,
        "inventory": inventory,
        "orders": orders,
        "customers": customers,
        "sales": sales,
        "low_stock": low_stock,
    }


# ============================================================
# Dashboard Service Health Check
# ============================================================


async def admin_dashboard_service_check(
    session: AsyncSession,
) -> dict:
    """
    Simple service/database health check.
    """

    try:
        result = await session.execute(
            select(func.count(Product.id))
        )

        product_count = result.scalar_one() or 0

        return {
            "ok": True,
            "database": True,
            "product_count": int(product_count),
        }

    except Exception as exc:
        return {
            "ok": False,
            "database": False,
            "product_count": 0,
            "error": str(exc),
        }
