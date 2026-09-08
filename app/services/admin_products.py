from __future__ import annotations

from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import Product


# ============================================================
# Product CRUD Service
# ============================================================


async def create_product(
    session: AsyncSession,
    *,
    sku: str,
    brand: str,
    model: str,
    category: str,
    description: str = "",
    short_description: str = "",
    image_url: str = "",
    condition: str = "NEW",
    base_price: Decimal = Decimal("0"),
    is_active: bool = True,
    is_featured: bool = False,
) -> Product:
    """
    Create a new product.
    """

    product = Product(
        sku=sku.strip(),
        brand=brand.strip(),
        model=model.strip(),
        category=category.strip(),
        description=description.strip(),
        short_description=short_description.strip(),
        image_url=image_url.strip(),
        condition=condition,
        base_price=base_price,
        is_active=is_active,
        is_featured=is_featured,
    )

    session.add(product)

    await session.commit()
    await session.refresh(product)

    return product


async def get_product(
    session: AsyncSession,
    product_id: int,
) -> Product | None:
    """
    Get one product by ID.
    """

    result = await session.execute(
        select(Product).where(
            Product.id == product_id
        )
    )

    return result.scalar_one_or_none()


async def get_admin_products(
    session: AsyncSession,
    *,
    limit: int = 30,
    offset: int = 0,
) -> list[Product]:
    """
    Return products for admin panel.
    """

    result = await session.execute(
        select(Product)
        .order_by(Product.id.desc())
        .offset(offset)
        .limit(limit)
    )

    return list(result.scalars().all())


async def count_admin_products(
    session: AsyncSession,
) -> int:
    """
    Count all products.
    """

    result = await session.execute(
        select(func.count(Product.id))
    )

    return int(result.scalar_one() or 0)


async def update_product(
    session: AsyncSession,
    product_id: int,
    **fields: Any,
) -> Product | None:
    """
    Update product fields.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    allowed_fields = {
        "sku",
        "brand",
        "model",
        "category",
        "description",
        "short_description",
        "image_url",
        "condition",
        "base_price",
        "is_active",
        "is_featured",
    }

    for field, value in fields.items():
        if field not in allowed_fields:
            continue

        if isinstance(value, str):
            value = value.strip()

        setattr(product, field, value)

    await session.commit()
    await session.refresh(product)

    return product


async def set_product_active(
    session: AsyncSession,
    product_id: int,
    active: bool,
) -> Product | None:
    """
    Activate or deactivate a product.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    product.is_active = active

    await session.commit()
    await session.refresh(product)

    return product


async def set_product_featured(
    session: AsyncSession,
    product_id: int,
    featured: bool,
) -> Product | None:
    """
    Enable or disable featured status.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    product.is_featured = featured

    await session.commit()
    await session.refresh(product)

    return product


async def delete_product(
    session: AsyncSession,
    product_id: int,
) -> bool:
    """
    Permanently delete a product.

    This function exists for future hard-delete support.
    For normal store operation, deactivation is safer.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return False

    await session.delete(product)
    await session.commit()

    return True
