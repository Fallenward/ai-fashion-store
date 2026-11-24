from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import AppError, NotFound
from app.models import Category, Product, ProductVariant
from app.repositories.product_repository import ProductSearch, get_product_by_slug, search_products
from app.services.recommendation import related_products, styling_for_product
from app.services.serializers import product_card, product_detail

router = APIRouter(tags=["catalog"])

SORTS = {"newest", "price_asc", "price_desc", "popularity"}


@router.get("/categories")
def categories(db: Session = Depends(get_db)):
    rows = db.scalars(select(Category).order_by(Category.sort_order, Category.name)).all()
    return [
        {
            "id": str(row.id),
            "name": row.name,
            "slug": row.slug,
            "description": row.description,
            "image_url": row.image_url,
        }
        for row in rows
    ]


@router.get("/facets")
def facets(db: Session = Depends(get_db)):
    sizes = db.scalars(
        select(ProductVariant.size)
        .join(Product)
        .where(Product.is_active.is_(True), ProductVariant.is_active.is_(True))
        .distinct()
    ).all()
    colors = db.scalars(
        select(ProductVariant.color)
        .join(Product)
        .where(Product.is_active.is_(True), ProductVariant.is_active.is_(True))
        .distinct()
    ).all()
    brands = db.scalars(select(Product.brand).where(Product.is_active.is_(True)).distinct()).all()
    low, high = db.execute(
        select(func.min(Product.price), func.max(Product.price)).where(Product.is_active.is_(True))
    ).one()
    order = {"XS": 0, "S": 1, "M": 2, "L": 3, "XL": 4, "XXL": 5}
    return {
        "sizes": sorted(set(sizes), key=lambda size: (order.get(size, 50), size)),
        "colors": sorted(set(colors)),
        "brands": sorted(set(brands)),
        "min_price": f"{low:.2f}" if low is not None else None,
        "max_price": f"{high:.2f}" if high is not None else None,
    }


@router.get("/products")
def products(
    q: str | None = None,
    category: str | None = None,
    size: str | None = None,
    color: str | None = None,
    brand: str | None = None,
    min_price: Decimal | None = None,
    max_price: Decimal | None = None,
    in_stock: bool | None = None,
    sort: str = "newest",
    page: int = 1,
    page_size: int = 12,
    featured: bool | None = None,
    is_new: bool | None = None,
    bestseller: bool | None = None,
    trending: bool | None = None,
    db: Session = Depends(get_db),
):
    if sort not in SORTS:
        raise AppError("Unknown sort.")
    rows, total = search_products(
        db,
        ProductSearch(
            query=q,
            category=category,
            size=size,
            color=color,
            brand=brand,
            min_price=min_price,
            max_price=max_price,
            in_stock=in_stock,
            sort=sort,
            page=page,
            page_size=page_size,
            featured=featured,
            is_new=is_new,
            bestseller=bestseller,
            trending=trending,
        ),
    )
    return {
        "items": [product_card(row) for row in rows],
        "total": total,
        "page": max(page, 1),
        "page_size": min(max(page_size, 1), 48),
    }


@router.get("/products/{slug}")
def product_detail_route(slug: str, db: Session = Depends(get_db)):
    product = get_product_by_slug(db, slug)
    if product is None:
        raise NotFound("Product not found.")
    return product_detail(product)


@router.get("/products/{slug}/related")
def related(slug: str, db: Session = Depends(get_db)):
    product = get_product_by_slug(db, slug)
    if product is None:
        raise NotFound("Product not found.")
    return {"items": related_products(db, product.id)}


@router.get("/products/{slug}/styling")
def styling(slug: str, db: Session = Depends(get_db)):
    product = get_product_by_slug(db, slug)
    if product is None:
        raise NotFound("Product not found.")
    return styling_for_product(db, slug)
