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
def _decimal_to_float(
    value: Decimal | None,
) -> float | None:
    """
    Convert Decimal values to float for API/Telegram output.
    """
    if value is None:
        return None
    return float(value)
def _serialize_value(value: Any) -> Any:
    """
    Convert common SQLAlchemy/Python values into
    JSON-friendly values.
    """
    if isinstance(value, Decimal):
        return _decimal_to_float(value)
    if hasattr(value, "value"):
        return value.value
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass
    return value
# ==========================================================
# PRODUCT QUERIES
# ==========================================================
async def get_product_by_id(
    db: AsyncSession,
    product_id: int,
) -> Product | None:
    """
    Get one product by ID.
    Variants and inventory units are loaded together
    to avoid lazy-loading problems in async SQLAlchemy.
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
async def get_active_product_by_id(
    db: AsyncSession,
    product_id: int,
) -> Product | None:
    """
    Get one active product by ID.
    """
    statement = (
        select(Product)
        .where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
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
    active_only: bool = True,
) -> list[Product]:
    """
    Get products with pagination.
    """
    skip = max(skip, 0)
    limit = max(1, min(limit, 200))
    statement = select(Product)
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    statement = (
        statement
        .order_by(Product.created_at.desc())
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
async def get_all_products(
    db: AsyncSession,
    *,
    active_only: bool = True,
) -> list[Product]:
    """
    Get all products.
    Intended for internal use and small catalogs.
    """
    statement = select(Product)
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    statement = (
        statement
        .order_by(Product.created_at.desc())
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
# PRODUCT SEARCH
# ==========================================================
async def search_products(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
    active_only: bool = True,
) -> list[Product]:
    """
    Search products using the actual Product fields:
    - brand
    - model
    - sku
    - category
    - description
    - short_description
    """
    query = query.strip()
    if not query:
        return []
    limit = max(1, min(limit, 100))
    search_pattern = f"%{query}%"
    conditions = [
        Product.brand.ilike(search_pattern),
        Product.model.ilike(search_pattern),
        Product.sku.ilike(search_pattern),
        Product.category.ilike(search_pattern),
        Product.description.ilike(search_pattern),
        Product.short_description.ilike(search_pattern),
    ]
    statement = select(Product).where(
        or_(*conditions)
    )
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    statement = (
        statement
        .order_by(Product.created_at.desc())
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
# CATEGORY SEARCH
# ==========================================================
async def get_products_by_category(
    db: AsyncSession,
    category: str,
    *,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[Product]:
    """
    Get products by exact category.
    """
    category = category.strip()
    if not category:
        return []
    skip = max(skip, 0)
    limit = max(1, min(limit, 200))
    statement = (
        select(Product)
        .where(
            Product.category == category
        )
    )
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    statement = (
        statement
        .order_by(Product.created_at.desc())
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
async def get_products_by_brand(
    db: AsyncSession,
    brand: str,
    *,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[Product]:
    """
    Get products by brand.
    """
    brand = brand.strip()
    if not brand:
        return []
    skip = max(skip, 0)
    limit = max(1, min(limit, 200))
    statement = (
        select(Product)
        .where(
            Product.brand.ilike(brand)
        )
    )
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    statement = (
        statement
        .order_by(Product.created_at.desc())
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
# PRODUCT COUNT
# ==========================================================
async def count_products(
    db: AsyncSession,
    *,
    active_only: bool = True,
) -> int:
    """
    Return total number of products.
    """
    statement = select(
        func.count(Product.id)
    )
    if active_only:
        statement = statement.where(
            Product.is_active.is_(True)
        )
    result = await db.execute(statement)
    return int(
        result.scalar_one() or 0
    )
async def count_products_by_category(
    db: AsyncSession,
    category: str,
) -> int:
    """
    Return active product count for a category.
    """
    statement = select(
        func.count(Product.id)
    ).where(
        Product.category == category,
        Product.is_active.is_(True),
    )
    result = await db.execute(statement)
    return int(
        result.scalar_one() or 0
    )
# ==========================================================
# VARIANT QUERIES
# ==========================================================
async def get_product_variants(
    db: AsyncSession,
    product_id: int,
    *,
    active_only: bool = True,
) -> list[ProductVariant]:
    """
    Get variants belonging to a product.
    """
    statement = (
        select(ProductVariant)
        .where(
            ProductVariant.product_id == product_id
        )
    )
    if active_only:
        statement = statement.where(
            ProductVariant.is_active.is_(True)
        )
    statement = (
        statement
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
async def get_active_variant_by_id(
    db: AsyncSession,
    variant_id: int,
) -> ProductVariant | None:
    """
    Get one active product variant.
    """
    statement = (
        select(ProductVariant)
        .where(
            ProductVariant.id == variant_id,
            ProductVariant.is_active.is_(True),
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
    return list(
        result.scalars().all()
    )
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
    return int(
        result.scalar_one() or 0
    )
async def get_product_stock(
    db: AsyncSession,
    product_id: int,
) -> int:
    """
    Return total available stock for all variants
    of a product.
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
            ProductVariant.is_active.is_(True),
            InventoryUnit.status
            == _available_inventory_status(),
        )
    )
    result = await db.execute(statement)
    return int(
        result.scalar_one() or 0
    )
async def is_product_available(
    db: AsyncSession,
    product_id: int,
) -> bool:
    """
    Check whether a product has available inventory.
    """
    return (
        await get_product_stock(
            db,
            product_id,
        )
        > 0
    )
async def is_variant_available(
    db: AsyncSession,
    variant_id: int,
) -> bool:
    """
    Check whether a variant has available inventory.
    """
    return (
        await get_variant_stock(
            db,
            variant_id,
        )
        > 0
    )
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
    Get active products that currently have
    at least one available inventory unit.
    """
    skip = max(skip, 0)
    limit = max(1, min(limit, 200))
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
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            InventoryUnit.status
            == _available_inventory_status(),
        )
        .group_by(Product.id)
        .order_by(Product.created_at.desc())
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
async def search_available_products(
    db: AsyncSession,
    query: str,
    *,
    limit: int = 20,
) -> list[Product]:
    """
    Search products by brand/model/SKU/category
    and return only products with available stock.
    """
    query = query.strip()
    if not query:
        return []
    limit = max(1, min(limit, 100))
    search_pattern = f"%{query}%"
    search_conditions = [
        Product.brand.ilike(search_pattern),
        Product.model.ilike(search_pattern),
        Product.sku.ilike(search_pattern),
        Product.category.ilike(search_pattern),
        Product.description.ilike(search_pattern),
        Product.short_description.ilike(search_pattern),
    ]
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
            Product.is_active.is_(True),
            ProductVariant.is_active.is_(True),
            InventoryUnit.status
            == _available_inventory_status(),
            or_(*search_conditions),
        )
        .group_by(Product.id)
        .order_by(Product.created_at.desc())
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
# SERIALIZATION
# ==========================================================
def variant_to_dict(
    variant: ProductVariant,
) -> dict[str, Any]:
    """
    Convert ProductVariant to a clean dictionary.
    """
    data: dict[str, Any] = {
        "id": variant.id,
        "storage": getattr(
            variant,
            "storage",
            None,
        ),
        "color": getattr(
            variant,
            "color",
            None,
        ),
        "ram": getattr(
            variant,
            "ram",
            None,
        ),
        "price": _serialize_value(
            getattr(
                variant,
                "price",
                None,
            )
        ),
        "is_active": getattr(
            variant,
            "is_active",
            True,
        ),
    }
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
    data["stock"] = len(
        available_units
    )
    data["available"] = bool(
        available_units
    )
    return data
def product_to_dict(
    product: Product,
) -> dict[str, Any]:
    """
    Convert Product SQLAlchemy object into
    a JSON-friendly dictionary.
    Uses the actual Product fields.
    """
    data: dict[str, Any] = {
        "id": product.id,
        "sku": product.sku,
        "brand": product.brand,
        "model": product.model,
        "category": product.category,
        "description": product.description,
        "short_description": product.short_description,
        "image_url": product.image_url,
        "condition": _serialize_value(
            product.condition
        ),
        "base_price": _serialize_value(
            product.base_price
        ),
        "is_active": product.is_active,
        "is_featured": product.is_featured,
    }
    variants = getattr(
        product,
        "variants",
        [],
    )
    serialized_variants = [
        variant_to_dict(variant)
        for variant in variants
    ]
    data["variants"] = serialized_variants
    data["stock"] = sum(
        variant["stock"]
        for variant in serialized_variants
    )
    data["available"] = (
        data["stock"] > 0
    )
    return data
def products_to_dict(
    products: list[Product],
) -> list[dict[str, Any]]:
    """
    Convert a product list into dictionaries.
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
    Get complete product information including
    variants and current stock.
    """
    product = await get_active_product_by_id(
        db,
        product_id,
    )
    if product is None:
        return None
    return product_to_dict(product)
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
