from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import PriceHistory, Product


# ==========================================================
# Helpers
# ==========================================================


def normalize_text(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text if text else None


def parse_price(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        price = value
    else:
        normalized = (
            str(value)
            .strip()
            .replace(",", "")
            .replace("٬", "")
            .replace("،", "")
            .replace("تومان", "")
            .replace("تومن", "")
            .strip()
        )

        try:
            price = Decimal(normalized)
        except (InvalidOperation, ValueError):
            raise ValueError("قیمت واردشده معتبر نیست.")

    if price < 0:
        raise ValueError("قیمت نمی‌تواند منفی باشد.")

    return price


# ==========================================================
# SKU
# ==========================================================


async def sku_exists(
    session: AsyncSession,
    sku: str,
    exclude_product_id: int | None = None,
) -> bool:
    normalized_sku = normalize_text(sku)

    if not normalized_sku:
        return False

    statement = select(Product.id).where(
        func.lower(Product.sku) == normalized_sku.lower()
    )

    if exclude_product_id is not None:
        statement = statement.where(
            Product.id != exclude_product_id
        )

    result = await session.execute(statement)

    return result.scalar_one_or_none() is not None


# ==========================================================
# CREATE
# ==========================================================


async def create_product(
    session: AsyncSession,
    *,
    sku: str,
    brand: str,
    model: str,
    category: str,
    condition: Any,
    base_price: Any,
    short_description: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
    is_active: bool = True,
    is_featured: bool = False,
) -> Product:
    sku = normalize_text(sku) or ""
    brand = normalize_text(brand) or ""
    model = normalize_text(model) or ""
    category = normalize_text(category) or ""

    if not sku:
        raise ValueError("SKU الزامی است.")

    if not brand:
        raise ValueError("برند الزامی است.")

    if not model:
        raise ValueError("مدل محصول الزامی است.")

    if not category:
        raise ValueError("دسته‌بندی الزامی است.")

    if await sku_exists(session, sku):
        raise ValueError(
            f"SKU «{sku}» قبلاً برای یک محصول دیگر ثبت شده است."
        )

    price = parse_price(base_price)

    product = Product(
        sku=sku,
        brand=brand,
        model=model,
        category=category,
        condition=condition,
        base_price=price,
        short_description=normalize_text(short_description),
        description=normalize_text(description),
        image_url=normalize_text(image_url),
        is_active=is_active,
        is_featured=is_featured,
    )

    session.add(product)

    await session.commit()
    await session.refresh(product)

    return product


# ==========================================================
# READ
# ==========================================================


async def get_product(
    session: AsyncSession,
    product_id: int,
) -> Product | None:
    statement = select(Product).where(
        Product.id == product_id
    )

    result = await session.execute(statement)

    return result.scalar_one_or_none()


async def get_admin_products(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> list[Product]:
    statement = (
        select(Product)
        .order_by(Product.id.desc())
        .offset(max(offset, 0))
        .limit(max(limit, 1))
    )

    result = await session.execute(statement)

    return list(result.scalars().all())


async def count_admin_products(
    session: AsyncSession,
) -> int:
    statement = select(func.count(Product.id))

    result = await session.execute(statement)

    return int(result.scalar_one() or 0)


# ==========================================================
# UPDATE
# ==========================================================


async def update_product(
    session: AsyncSession,
    product_id: int,
    *,
    sku: str | None = None,
    brand: str | None = None,
    model: str | None = None,
    category: str | None = None,
    condition: Any | None = None,
    base_price: Any | None = None,
    short_description: str | None = None,
    description: str | None = None,
    image_url: str | None = None,
    is_active: bool | None = None,
    is_featured: bool | None = None,
    record_price_history: bool = True,
) -> tuple[Product | None, bool]:
    """
    Update product.

    Returns:
        (product, price_changed)

    PriceHistory is created only when the price actually changes.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None, False

    price_changed = False

    # ------------------------------------------------------
    # SKU
    # ------------------------------------------------------

    if sku is not None:
        normalized_sku = normalize_text(sku)

        if not normalized_sku:
            raise ValueError("SKU نمی‌تواند خالی باشد.")

        if await sku_exists(
            session,
            normalized_sku,
            exclude_product_id=product_id,
        ):
            raise ValueError(
                f"SKU «{normalized_sku}» قبلاً ثبت شده است."
            )

        product.sku = normalized_sku

    # ------------------------------------------------------
    # Basic fields
    # ------------------------------------------------------

    if brand is not None:
        normalized_brand = normalize_text(brand)

        if not normalized_brand:
            raise ValueError("برند نمی‌تواند خالی باشد.")

        product.brand = normalized_brand

    if model is not None:
        normalized_model = normalize_text(model)

        if not normalized_model:
            raise ValueError("مدل نمی‌تواند خالی باشد.")

        product.model = normalized_model

    if category is not None:
        normalized_category = normalize_text(category)

        if not normalized_category:
            raise ValueError(
                "دسته‌بندی نمی‌تواند خالی باشد."
            )

        product.category = normalized_category

    if condition is not None:
        product.condition = condition

    # ------------------------------------------------------
    # Price
    # ------------------------------------------------------

    if base_price is not None:
        new_price = parse_price(base_price)

        old_price = (
            Decimal(str(product.base_price))
            if product.base_price is not None
            else Decimal("0")
        )

        if new_price != old_price:
            price_changed = True

            if (
                record_price_history
                and product.id is not None
            ):
                price_history = PriceHistory(
                    product_id=product.id,
                    old_price=old_price,
                    new_price=new_price,
                )

                session.add(price_history)

            product.base_price = new_price

    # ------------------------------------------------------
    # Descriptions
    # ------------------------------------------------------

    if short_description is not None:
        product.short_description = (
            normalize_text(short_description)
        )

    if description is not None:
        product.description = normalize_text(description)

    if image_url is not None:
        product.image_url = normalize_text(image_url)

    # ------------------------------------------------------
    # Flags
    # ------------------------------------------------------

    if is_active is not None:
        product.is_active = bool(is_active)

    if is_featured is not None:
        product.is_featured = bool(is_featured)

    await session.commit()
    await session.refresh(product)

    return product, price_changed


# ==========================================================
# ACTIVE / INACTIVE
# ==========================================================


async def set_product_active(
    session: AsyncSession,
    product_id: int,
    active: bool,
) -> Product | None:
    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    product.is_active = bool(active)

    await session.commit()
    await session.refresh(product)

    return product


# ==========================================================
# FEATURED
# ==========================================================


async def set_product_featured(
    session: AsyncSession,
    product_id: int,
    featured: bool,
) -> Product | None:
    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    product.is_featured = bool(featured)

    await session.commit()
    await session.refresh(product)

    return product


# ==========================================================
# SAFE DELETE
# ==========================================================


async def delete_product(
    session: AsyncSession,
    product_id: int,
) -> Product | None:
    """
    Soft delete.

    Product is deactivated instead of physically removing it
    from the database.
    """

    product = await get_product(
        session,
        product_id,
    )

    if product is None:
        return None

    product.is_active = False
    product.is_featured = False

    await session.commit()
    await session.refresh(product)

    return product
