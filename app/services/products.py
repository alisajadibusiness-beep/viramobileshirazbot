from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import (
    InventoryStatus,
    InventoryUnit,
    Product,
    ProductVariant,
)


# ==========================================================
# PRODUCT SERVICE
# VIRA MOBILE
# ==========================================================


# ==========================================================
# HELPERS
# ==========================================================

def _available_inventory_status() -> str:
    """
    Return the database value used for available inventory.
    """

    return InventoryStatus.AVAILABLE.value


def _decimal_to_float(value: Decimal | None) -> float | None:
    """
    Convert Decimal database values to float for API/Telegram output.
    """

    if value is None:
        return None

    return float(value)


# ==========================================================
# PRODUCT QUERIES
# ==========================================================

async def get_product_by_id(
    db: AsyncSession,
    product_id: int,
) -> Product | None:
    """
    Get one product by ID with variants and inventory loaded.
    """

    statement = (
        select(Product)
        .where(Product.id == product_id)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return result.scalar_one_or_none()


async def get_products(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Product]:
    """
    Get products with pagination.
    """

    if skip < 0:
        skip = 0

    if limit <= 0:
        limit = 50

    if limit > 200:
        limit = 200

    statement = (
        select(Product)
        .order_by(Product.id.desc())
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(result.scalars().unique().all())


async def get_all_products(
    db: AsyncSession,
) -> list[Product]:
    """
    Get all products.

    Intended for internal use and small product catalogs.
    """

    statement = (
        select(Product)
        .order_by(Product.id.desc())
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(result.scalars().unique().all())


# ==========================================================
# PRODUCT SEARCH
# ==========================================================

async def search_products(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
) -> list[Product]:
    """
    Search products by name and brand.

    Search is case-insensitive.
    """

    query = query.strip()

    if not query:
        return []

    if limit <= 0:
        limit = 20

    if limit > 100:
        limit = 100

    search_pattern = f"%{query}%"

    conditions = [
        Product.name.ilike(search_pattern),
    ]

    if hasattr(Product, "brand"):
        conditions.append(
            Product.brand.ilike(search_pattern)
        )

    statement = (
        select(Product)
        .where(or_(*conditions))
        .order_by(Product.id.desc())
        .limit(limit)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(result.scalars().unique().all())


# ==========================================================
# PRODUCT COUNT
# ==========================================================

async def count_products(
    db: AsyncSession,
) -> int:
    """
    Return total number of products.
    """

    statement = select(
        func.count(Product.id)
    )

    result = await db.execute(statement)

    return int(result.scalar_one() or 0)


# ==========================================================
# VARIANT QUERIES
# ==========================================================

async def get_product_variants(
    db: AsyncSession,
    product_id: int,
) -> list[ProductVariant]:
    """
    Get all variants belonging to a product.
    """

    statement = (
        select(ProductVariant)
        .where(
            ProductVariant.product_id == product_id
        )
        .order_by(ProductVariant.id.asc())
        .options(
            selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(
        result.scalars().unique().all()
    )


async def get_variant_by_id(
    db: AsyncSession,
    variant_id: int,
) -> ProductVariant | None:
    """
    Get one product variant with inventory.
    """

    statement = (
        select(ProductVariant)
        .where(
            ProductVariant.id == variant_id
        )
        .options(
            selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return result.scalar_one_or_none()


# ==========================================================
# INVENTORY
# ==========================================================

async def get_available_inventory_units(
    db: AsyncSession,
    variant_id: int,
) -> list[InventoryUnit]:
    """
    Get available inventory units for a variant.
    """

    statement = (
        select(InventoryUnit)
        .where(
            InventoryUnit.variant_id == variant_id,
            InventoryUnit.status
            == _available_inventory_status(),
        )
        .order_by(InventoryUnit.id.asc())
    )

    result = await db.execute(statement)

    return list(result.scalars().all())


async def get_variant_stock(
    db: AsyncSession,
    variant_id: int,
) -> int:
    """
    Return available stock quantity for one variant.
    """

    statement = select(
        func.count(InventoryUnit.id)
    ).where(
        InventoryUnit.variant_id == variant_id,
        InventoryUnit.status
        == _available_inventory_status(),
    )

    result = await db.execute(statement)

    return int(result.scalar_one() or 0)


async def get_product_stock(
    db: AsyncSession,
    product_id: int,
) -> int:
    """
    Return total available stock for all variants of a product.
    """

    statement = (
        select(
            func.count(InventoryUnit.id)
        )
        .join(
            ProductVariant,
            ProductVariant.id
            == InventoryUnit.variant_id,
        )
        .where(
            ProductVariant.product_id == product_id,
            InventoryUnit.status
            == _available_inventory_status(),
        )
    )

    result = await db.execute(statement)

    return int(result.scalar_one() or 0)


async def is_product_available(
    db: AsyncSession,
    product_id: int,
) -> bool:
    """
    Check whether a product has at least one
    available inventory unit.
    """

    stock = await get_product_stock(
        db,
        product_id,
    )

    return stock > 0


async def is_variant_available(
    db: AsyncSession,
    variant_id: int,
) -> bool:
    """
    Check whether a variant has available stock.
    """

    stock = await get_variant_stock(
        db,
        variant_id,
    )

    return stock > 0


# ==========================================================
# AVAILABLE PRODUCTS
# ==========================================================

async def get_available_products(
    db: AsyncSession,
    *,
    skip: int = 0,
    limit: int = 50,
) -> list[Product]:
    """
    Get products that currently have available inventory.
    """

    if skip < 0:
        skip = 0

    if limit <= 0:
        limit = 50

    if limit > 200:
        limit = 200

    statement = (
        select(Product)
        .join(
            ProductVariant,
            ProductVariant.product_id == Product.id,
        )
        .join(
            InventoryUnit,
            InventoryUnit.variant_id
            == ProductVariant.id,
        )
        .where(
            InventoryUnit.status
            == _available_inventory_status()
        )
        .group_by(Product.id)
        .order_by(Product.id.desc())
        .offset(skip)
        .limit(limit)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(
        result.scalars().unique().all()
    )


# ==========================================================
# PRODUCT DATA
# ==========================================================

def product_to_dict(
    product: Product,
) -> dict[str, Any]:
    """
    Convert a Product SQLAlchemy object into
    a clean dictionary.

    This is useful for API responses and Telegram messages.
    """

    data: dict[str, Any] = {
        "id": product.id,
        "name": product.name,
    }

    # ------------------------------------------------------
    # Optional product fields
    # ------------------------------------------------------

    optional_fields = (
        "brand",
        "model",
        "category",
        "description",
        "condition",
        "price",
        "is_active",
        "created_at",
        "updated_at",
    )

    for field in optional_fields:

        if not hasattr(product, field):
            continue

        value = getattr(product, field)

        if isinstance(value, Decimal):
            value = _decimal_to_float(value)

        if hasattr(value, "value"):
            value = value.value

        if hasattr(value, "isoformat"):
            try:
                value = value.isoformat()
            except Exception:
                pass

        data[field] = value

    # ------------------------------------------------------
    # Variants
    # ------------------------------------------------------

    variants: list[dict[str, Any]] = []

    for variant in getattr(
        product,
        "variants",
        [],
    ):

        variant_data: dict[str, Any] = {
            "id": variant.id,
        }

        variant_fields = (
            "storage",
            "color",
            "ram",
            "price",
            "sku",
        )

        for field in variant_fields:

            if not hasattr(variant, field):
                continue

            value = getattr(
                variant,
                field,
            )

            if isinstance(value, Decimal):
                value = _decimal_to_float(value)

            if hasattr(value, "value"):
                value = value.value

            variant_data[field] = value

        # --------------------------------------------------
        # Variant stock
        # --------------------------------------------------

        inventory_units = getattr(
            variant,
            "inventory_units",
            [],
        )

        available_units = [
            unit
            for unit in inventory_units
            if getattr(unit, "status", None)
            == _available_inventory_status()
        ]

        variant_data["stock"] = len(
            available_units
        )

        variant_data["available"] = bool(
            available_units
        )

        variants.append(
            variant_data
        )

    data["variants"] = variants

    data["stock"] = sum(
        variant.get("stock", 0)
        for variant in variants
    )

    data["available"] = data["stock"] > 0

    return data


# ==========================================================
# PRODUCT LIST DATA
# ==========================================================

def products_to_dict(
    products: list[Product],
) -> list[dict[str, Any]]:
    """
    Convert a list of Product objects into dictionaries.
    """

    return [
        product_to_dict(product)
        for product in products
    ]


# ==========================================================
# PRODUCT SUMMARY
# ==========================================================

async def get_product_summary(
    db: AsyncSession,
    product_id: int,
) -> dict[str, Any] | None:
    """
    Get a complete product summary including
    variants and current stock.
    """

    product = await get_product_by_id(
        db,
        product_id,
    )

    if product is None:
        return None

    return product_to_dict(product)


# ==========================================================
# SEARCH WITH STOCK
# ==========================================================

async def search_available_products(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
) -> list[Product]:
    """
    Search products and return only products
    that currently have available stock.
    """

    query = query.strip()

    if not query:
        return []

    if limit <= 0:
        limit = 20

    if limit > 100:
        limit = 100

    search_pattern = f"%{query}%"

    conditions = [
        Product.name.ilike(search_pattern),
    ]

    if hasattr(Product, "brand"):
        conditions.append(
            Product.brand.ilike(search_pattern)
        )

    statement = (
        select(Product)
        .join(
            ProductVariant,
            ProductVariant.product_id == Product.id,
        )
        .join(
            InventoryUnit,
            InventoryUnit.variant_id
            == ProductVariant.id,
        )
        .where(
            or_(*conditions),
            InventoryUnit.status
            == _available_inventory_status(),
        )
        .group_by(Product.id)
        .order_by(Product.id.desc())
        .limit(limit)
        .options(
            selectinload(Product.variants).selectinload(
                ProductVariant.inventory_units
            )
        )
    )

    result = await db.execute(statement)

    return list(
        result.scalars().unique().all()
    )


# ==========================================================
# SERVICE HEALTH
# ==========================================================

async def products_service_check(
    db: AsyncSession,
) -> bool:
    """
    Simple database-level product service check.
    """

    try:

        statement = select(
            func.count(Product.id)
        )

        result = await db.execute(
            statement
        )

        result.scalar_one()

        return True

    except Exception:

        return False
