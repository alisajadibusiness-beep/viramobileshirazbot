from __future__ import annotations
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import get_db
from app.database.models import Product, ProductVariant
from app.services.products import (
    get_active_product_by_id,
    get_product_by_id,
    get_products as service_get_products,
    get_products_by_category,
    get_products_by_brand,
    get_product_variants,
    search_products,
)
router = APIRouter(
    prefix="/api/products",
    tags=["Products"],
)
# ==========================================================
# SCHEMAS
# ==========================================================
class ProductVariantResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
    id: int
    storage: str | None
    color: str | None
    ram: str | None
    price: Decimal
    is_active: bool
class ProductResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
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
    variants: list[ProductVariantResponse] = Field(
        default_factory=list
    )
class ProductListResponse(BaseModel):
    model_config = ConfigDict(
        from_attributes=True
    )
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
    sku: str = Field(
        min_length=1,
        max_length=100,
    )
    brand: str = Field(
        min_length=1,
        max_length=100,
    )
    model: str = Field(
        min_length=1,
        max_length=150,
    )
    category: str = Field(
        min_length=1,
        max_length=100,
    )
    description: str | None = None
    short_description: str | None = None
    image_url: str | None = None
    condition: str = "new"
    base_price: Decimal = Field(
        default=Decimal("0"),
        ge=0,
    )
    is_featured: bool = False
class VariantCreateRequest(BaseModel):
    storage: str | None = None
    color: str | None = None
    ram: str | None = None
    price: Decimal = Field(
        ge=0
    )
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
    Return real active product categories
    with product counts.
    """
    result = await db.execute(
        select(
            Product.category,
            func.count(Product.id),
        )
        .where(
            Product.is_active.is_(True)
        )
        .group_by(
            Product.category
        )
        .order_by(
            Product.category
        )
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
                "count": int(count),
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
@router.get(
    "",
    response_model=list[ProductListResponse],
)
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
        description="Search product by brand, model or SKU",
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
    Return active products with filtering.
    Search/filter logic is delegated to the
    product service where possible.
    """
    # ------------------------------------------------------
    # Search
    # ------------------------------------------------------
    if search:
        products = await search_products(
            db,
            search,
            limit=limit,
            active_only=True,
        )
        # Apply remaining filters in Python only after
        # service-level search. This keeps the service
        # reusable while preserving API behavior.
        if category:
            products = [
                product
                for product in products
                if product.category == category
            ]
        if brand:
            brand_lower = brand.lower()
            products = [
                product
                for product in products
                if brand_lower
                in product.brand.lower()
            ]
        if condition:
            products = [
                product
                for product in products
                if product.condition == condition
            ]
        if featured is not None:
            products = [
                product
                for product in products
                if product.is_featured == featured
            ]
        return products[
            offset: offset + limit
        ]
    # ------------------------------------------------------
    # Category
    # ------------------------------------------------------
    if category:
        products = await get_products_by_category(
            db,
            category,
            skip=offset,
            limit=limit,
            active_only=True,
        )
    # ------------------------------------------------------
    # Brand
    # ------------------------------------------------------
    elif brand:
        products = await get_products_by_brand(
            db,
            brand,
            skip=offset,
            limit=limit,
            active_only=True,
        )
    # ------------------------------------------------------
    # Standard listing
    # ------------------------------------------------------
    else:
        products = await service_get_products(
            db,
            skip=offset,
            limit=limit,
            active_only=True,
        )
    # ------------------------------------------------------
    # Additional filters
    # ------------------------------------------------------
    if condition:
        products = [
            product
            for product in products
            if product.condition == condition
        ]
    if featured is not None:
        products = [
            product
            for product in products
            if product.is_featured == featured
        ]
    return products
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
    Return complete active product information.
    """
    product = await get_active_product_by_id(
        db,
        product_id,
    )
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
    status_code=201,
)
async def create_product(
    data: ProductCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new product.
    Intended for the future admin panel.
    """
    sku = data.sku.strip()
    if not sku:
        raise HTTPException(
            status_code=422,
            detail="SKU نمی‌تواند خالی باشد.",
        )
    # ------------------------------------------------------
    # Check duplicate SKU
    # ------------------------------------------------------
    existing_result = await db.execute(
        select(Product).where(
            Product.sku == sku
        )
    )
    existing = (
        existing_result.scalar_one_or_none()
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="SKU قبلاً ثبت شده است.",
        )
    # ------------------------------------------------------
    # Create product
    # ------------------------------------------------------
    product = Product(
        sku=sku,
        brand=data.brand.strip(),
        model=data.model.strip(),
        category=data.category.strip(),
        description=data.description,
        short_description=data.short_description,
        image_url=data.image_url,
        condition=data.condition,
        base_price=data.base_price,
        is_featured=data.is_featured,
        is_active=True,
    )
    db.add(product)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="خطا در ثبت محصول.",
        )
    # ------------------------------------------------------
    # Reload product with relationships
    # ------------------------------------------------------
    created_product = await get_product_by_id(
        db,
        product.id,
    )
    if created_product is None:
        raise HTTPException(
            status_code=500,
            detail="محصول ثبت شد اما دریافت اطلاعات آن ناموفق بود.",
        )
    return created_product
# ==========================================================
# GET PRODUCT VARIANTS
# ==========================================================
@router.get(
    "/{product_id}/variants",
    response_model=list[ProductVariantResponse],
)
async def get_variants(
    product_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Return active variants of a product.
    """
    product = await get_active_product_by_id(
        db,
        product_id,
    )
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="محصول پیدا نشد.",
        )
    return await get_product_variants(
        db,
        product_id,
        active_only=True,
    )
# ==========================================================
# CREATE PRODUCT VARIANT
# ==========================================================
@router.post(
    "/{product_id}/variants",
    response_model=ProductVariantResponse,
    status_code=201,
)
async def create_variant(
    product_id: int,
    data: VariantCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Add a variant to an existing product.
    """
    # ------------------------------------------------------
    # Check product
    # ------------------------------------------------------
    product = await get_active_product_by_id(
        db,
        product_id,
    )
    if product is None:
        raise HTTPException(
            status_code=404,
            detail="محصول پیدا نشد.",
        )
    # ------------------------------------------------------
    # Create variant
    # ------------------------------------------------------
    variant = ProductVariant(
        product_id=product_id,
        storage=data.storage,
        color=data.color,
        ram=data.ram,
        price=data.price,
        is_active=data.is_active,
    )
    db.add(variant)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail="خطا در ثبت تنوع محصول.",
        )
    await db.refresh(
        variant
    )
    return variant
