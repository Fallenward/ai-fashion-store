import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.exceptions import AppError, NotFound
from app.core.text import slugify
from app.models import Category, Inventory, Product, ProductImage, ProductVariant
from app.repositories.product_repository import get_product
from app.services.serializers import product_detail


def _unique_slug(db: Session, name: str, requested: str | None, ignore: uuid.UUID | None = None) -> str:
    base = slugify(requested or name) or "product"
    slug = base
    index = 2
    while True:
        existing = db.scalar(select(Product.id).where(Product.slug == slug))
        if existing is None or existing == ignore:
            return slug
        slug = f"{base}-{index}"
        index += 1


def create_product(db: Session, payload: dict) -> dict:
    category = db.get(Category, payload["category_id"])
    if category is None:
        raise AppError("Choose a category.")
    product = Product(
        category_id=category.id,
        name=payload["name"].strip(),
        slug=_unique_slug(db, payload["name"], payload.get("slug")),
        description=payload["description"].strip(),
        brand=payload["brand"].strip(),
        price=payload["price"],
        compare_at_price=payload.get("compare_at_price"),
        material=(payload.get("material") or None),
        care=(payload.get("care") or None),
        is_featured=bool(payload.get("is_featured")),
        is_new=bool(payload.get("is_new")),
        is_bestseller=bool(payload.get("is_bestseller")),
        is_trending=bool(payload.get("is_trending")),
        is_active=bool(payload.get("is_active", True)),
    )
    db.add(product)
    db.flush()
    _replace_variants(db, product, payload["variants"])
    db.add(
        ProductImage(
            product_id=product.id,
            url="/static/products/placeholder.svg",
            alt=product.name,
            sort_order=0,
            is_primary=True,
        )
    )
    db.commit()
    return product_detail(_reload(db, product.id))


def update_product(db: Session, product_id: uuid.UUID, payload: dict) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found.")
    for field in ("name", "description", "brand", "material", "care"):
        if field in payload and payload[field] is not None:
            setattr(product, field, str(payload[field]).strip())
    if payload.get("category_id"):
        category = db.get(Category, payload["category_id"])
        if category is None:
            raise AppError("Choose a category.")
        product.category_id = category.id
    if "price" in payload and payload["price"] is not None:
        product.price = payload["price"]
    if "compare_at_price" in payload:
        product.compare_at_price = payload["compare_at_price"]
    for flag in ("is_featured", "is_new", "is_bestseller", "is_trending", "is_active"):
        if flag in payload and payload[flag] is not None:
            setattr(product, flag, bool(payload[flag]))
    if payload.get("slug"):
        product.slug = _unique_slug(db, product.name, payload["slug"], ignore=product.id)
    if payload.get("variants") is not None:
        _replace_variants(db, product, payload["variants"])
    db.commit()
    return product_detail(_reload(db, product.id))


def _replace_variants(db: Session, product: Product, variants: list[dict]) -> None:
    existing = {variant.sku: variant for variant in db.scalars(select(ProductVariant).where(ProductVariant.product_id == product.id)).all()}
    seen = set()
    for index, raw in enumerate(variants):
        sku = raw["sku"].strip()
        if sku in seen:
            raise AppError(f"Duplicate SKU {sku}.")
        seen.add(sku)
        variant = existing.get(sku)
        if variant is None:
            variant = ProductVariant(product_id=product.id, sku=sku, size=raw["size"].strip(), color=raw["color"].strip())
            db.add(variant)
            db.flush()
            db.add(Inventory(variant_id=variant.id, quantity=int(raw.get("quantity") or 0), low_stock_threshold=int(raw.get("low_stock_threshold") or 5)))
        variant.size = raw["size"].strip()
        variant.color = raw["color"].strip()
        variant.color_hex = (raw.get("color_hex") or "#222222").strip()
        variant.price = raw.get("price")
        variant.is_active = True
        if variant.inventory is None:
            db.add(Inventory(variant_id=variant.id, quantity=int(raw.get("quantity") or 0)))
        elif "quantity" in raw and raw["quantity"] is not None:
            variant.inventory.quantity = int(raw["quantity"])
        if raw.get("low_stock_threshold") is not None and variant.inventory is not None:
            variant.inventory.low_stock_threshold = int(raw["low_stock_threshold"])
    for sku, variant in existing.items():
        if sku not in seen:
            variant.is_active = False


def archive_product(db: Session, product_id: uuid.UUID) -> None:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found.")
    product.is_active = False
    db.commit()


def add_image(db: Session, product_id: uuid.UUID, url: str, alt: str) -> dict:
    product = db.get(Product, product_id)
    if product is None:
        raise NotFound("Product not found.")
    count = db.scalar(select(func.count()).select_from(ProductImage).where(ProductImage.product_id == product.id)) or 0
    image = ProductImage(product_id=product.id, url=url, alt=alt or product.name, sort_order=int(count), is_primary=count == 0)
    db.add(image)
    db.commit()
    return product_detail(_reload(db, product.id))


def delete_image(db: Session, image_id: uuid.UUID) -> None:
    image = db.get(ProductImage, image_id)
    if image is None:
        raise NotFound("Image not found.")
    product_id = image.product_id
    was_primary = image.is_primary
    db.delete(image)
    db.commit()
    if was_primary:
        replacement = db.scalar(select(ProductImage).where(ProductImage.product_id == product_id).order_by(ProductImage.sort_order))
        if replacement:
            replacement.is_primary = True
            db.commit()


def _reload(db: Session, product_id: uuid.UUID) -> Product:
    product = db.scalar(
        select(Product)
        .options(selectinload(Product.images), selectinload(Product.category), selectinload(Product.variants).selectinload(ProductVariant.inventory))
        .where(Product.id == product_id)
    )
    if product is None:
        raise NotFound("Product not found.")
    return product


def admin_product(db: Session, product_id: uuid.UUID) -> dict:
    product = _reload(db, product_id)
    return product_detail(product)


def low_stock(db: Session) -> list[dict]:
    rows = db.execute(
        select(Product, ProductVariant, Inventory)
        .join(ProductVariant, ProductVariant.product_id == Product.id)
        .join(Inventory, Inventory.variant_id == ProductVariant.id)
        .where(Product.is_active.is_(True), ProductVariant.is_active.is_(True), Inventory.quantity <= Inventory.low_stock_threshold)
        .order_by(Inventory.quantity.asc())
        .limit(20)
    ).all()
    return [
        {
            "product_id": str(product.id),
            "product_name": product.name,
            "slug": product.slug,
            "sku": variant.sku,
            "size": variant.size,
            "color": variant.color,
            "quantity": inventory.quantity,
            "threshold": inventory.low_stock_threshold,
        }
        for product, variant, inventory in rows
    ]
