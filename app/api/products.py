from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.connection import get_db
from app.database.models import Product, ProductVariant


router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)


# ==========================================================
# SCHEMAS
# ==========================================================

class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    storage: str | None
    color: str | None
    ram: str | None
    price: Decimal
    is_active: bool


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sku: str
    brand: str
    model: str
    category: str
    description: str | None
    short_description: str | None
    image_url: str | None
    condition: str
    base_price: Decimal
    is_active: bool
    is_featured: bool
    variants: list[ProductVariantResponse] = []


class ProductListResponse(BaseModel):
    id: int
    sku: str
    brand: str
    model: str
    category: str
    condition: str
    base_price: Decimal
    image_url: str | None
    is_featured: bool


class ProductCreateRequest(BaseModel):
    sku: str
    brand: str
    model: str
    category: str
    description: str | None = None
    short_description: str | None = None
    image_url: str | None = None
    condition: str = "new"
    base_price: Decimal = Decimal("0")
    is_featured: bool = False


class VariantCreateRequest(BaseModel):
    storage: str | None = None
    color: str | None = None
    ram: str | None = None
    price: Decimal
    is_active: bool = True


# ==========================================================
# CATEGORY MAP
# ==========================================================

CATEGORY_MAP = {
    "iphone": "آیفون",
    "samsung": "سامسونگ",
    "xiaomi": "شیائومی",
    "other": "سایر برندها",
    "used": "گوشی‌های کارکرده",
}


# ==========================================================
# GET CATEGORIES
# ==========================================================

@router.get("/categories")
async def get_categories(
    db: AsyncSession = Depends(get_db),
):
    """
    Return real product categories with product counts.
    """

    result = await db.execute(
        select(
            Product.category,
            func.count(Product.id),
        )
        .where(Product.is_active.is_(True))
        .group_by(Product.category)
        .order_by(Product.category)
    )

    rows = result.all()

    categories = []

    for category, count in rows:
        categories.append(
            {
                "key": category,
                "title": CATEGORY_MAP.get(
                    category,
                    category,
                ),
                "count": count,
            }
        )

    return {
        "status": "ok",
        "count": len(categories),
        "categories": categories,
    }


# ==========================================================
# GET PRODUCTS
# ==========================================================

@router.get("", response_model=list[ProductListResponse])
async def get_products(
    category: str | None = Query(
        default=None,
        description="Product category",
    ),
    brand: str | None = Query(
        default=None,
        description="Brand",
    ),
    search: str | None = Query(
        default=None,
        description="Search product",
    ),
    condition: str | None = Query(
        default=None,
        description="new or used",
    ),
    featured: bool | None = Query(
        default=None,
        description="Featured products",
    ),
    limit: int = Query(
        default=20,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    db: AsyncSession = Depends(get_db),
):
    """
    Return products with filtering.
    """

    statement = (
        select(Product)
        .where(Product.is_active.is_(True))
    )

    if category:
        statement = statement.where(
            Product.category == category
        )

    if brand:
        statement = statement.where(
            Product.brand.ilike(f"%{brand}%")
        )

    if search:
        statement = statement.where(
            (
                Product.model.ilike(f"%{search}%")
                | Product.brand.ilike(f"%{search}%")
                | Product.sku.ilike(f"%{search}%")
            )
        )

    if condition:
        statement = statement.where(
            Product.condition == condition
        )

    if featured is not None:
        statement = statement.where(
            Product.is_featured == featured
        )

    statement = (
        statement
        .order_by(Product.created_at.desc())
        .offset(offset)
        .limit(limit)
    )

    result = await db.execute(statement)

    return result.scalars().all()


# ==========================================================
# GET SINGLE PRODUCT
# ==========================================================

@router.get(
    "/{product_id}",
    response_model=ProductResponse,
)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Return complete product information.
    """

    result = await db.execute(
        select(Product)
        .options(
            selectinload(Product.variants)
        )
        .where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )

    product = result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="محصول پیدا نشد.",
        )

    return product


# ==========================================================
# CREATE PRODUCT
# ==========================================================

@router.post(
    "",
    response_model=ProductResponse,
)
async def create_product(
    data: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a product.

    This endpoint is intended for the future admin panel.
    """

    existing = await db.execute(
        select(Product).where(
            Product.sku == data.sku
        )
    )

    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail="SKU قبلاً ثبت شده است.",
        )

    product = Product(
        sku=data.sku,
        brand=data.brand,
        model=data.model,
        category=data.category,
        description=data.description,
        short_description=data.short_description,
        image_url=data.image_url,
        condition=data.condition,
        base_price=data.base_price,
        is_featured=data.is_featured,
        is_active=True,
    )

    db.add(product)

    await db.commit()
    await db.refresh(product)

    return product


# ==========================================================
# CREATE PRODUCT VARIANT
# ==========================================================

@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
)
async def create_variant(
    product_id: int,
    data: VariantCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a product variant.
    """

    product_result = await db.execute(
        select(Product).where(
            Product.id == product_id
        )
    )

    product = product_result.scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="محصول پیدا نشد.",
        )

    variant = ProductVariant(
        product_id=product_id,
        storage=data.storage,
        color=data.color,
        ram=data.ram,
        price=data.price,
        is_active=data.is_active,
    )

    db.add(variant)

    await db.commit()
    await db.refresh(variant)

    return variant
