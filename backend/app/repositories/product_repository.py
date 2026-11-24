import re
import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from sqlalchemy import and_, exists, func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Category, Inventory, Product, ProductImage, ProductVariant

STOPWORDS = {
    "a", "an", "the", "for", "to", "of", "on", "in", "and", "or", "with", "under", "below",
    "over", "above", "than", "less", "more", "please", "looking", "look", "find", "show",
    "need", "want", "something", "pair", "get", "buy", "some", "any", "that", "this", "is",
    "are", "am", "be", "it", "its", "your", "you", "we", "our", "store", "from", "into",
    "just", "really", "very", "like", "would", "could", "can", "help", "me", "my", "im",
    "i", "outfit", "wear", "wearing", "piece", "pieces", "item", "items", "clothing",
    "clothes", "budget", "around", "about", "size", "sized", "color", "colour", "have",
    "has", "do", "does", "what", "which", "where", "when", "how", "who",
}

COLORS = [
    "midnight", "charcoal", "indigo", "ivory", "cream", "black", "white", "navy", "olive",
    "sand", "beige", "camel", "brown", "gold", "gray", "grey", "blue",
]


@dataclass
class ProductSearch:
    query: str | None = None
    category: str | None = None
    size: str | None = None
    color: str | None = None
    brand: str | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    in_stock: bool | None = None
    sort: str = "newest"
    page: int = 1
    page_size: int = 12
    featured: bool | None = None
    is_new: bool | None = None
    bestseller: bool | None = None
    trending: bool | None = None
    ids: list[uuid.UUID] | None = None
    include_inactive: bool = False
    tokens: list[str] = field(default_factory=list)


def analyze_query(query: str) -> tuple[list[str], dict]:
    lowered = query.lower()
    filters: dict = {}
    max_match = re.search(r"(?:under|below|less than|max(?:imum)?)\s*\$?\s*(\d+(?:\.\d+)?)", lowered)
    if max_match:
        filters["max_price"] = Decimal(max_match.group(1))
        lowered = lowered.replace(max_match.group(0), " ")
    min_match = re.search(r"(?:over|above|more than|min(?:imum)?|at least)\s*\$?\s*(\d+(?:\.\d+)?)", lowered)
    if min_match:
        filters["min_price"] = Decimal(min_match.group(1))
        lowered = lowered.replace(min_match.group(0), " ")
    for color in COLORS:
        if re.search(rf"\b{color}\b", lowered):
            filters["color"] = "gray" if color == "grey" else color
            lowered = re.sub(rf"\b{color}\b", " ", lowered, count=1)
            break
    tokens = [
        word
        for word in re.findall(r"[a-z0-9]+", lowered)
        if word not in STOPWORDS and len(word) > 1 and not word.isdigit()
    ]
    return tokens, filters


def _load_options(stmt):
    return stmt.options(
        selectinload(Product.images),
        selectinload(Product.category),
        selectinload(Product.variants).selectinload(ProductVariant.inventory),
    )


def search_products(db: Session, spec: ProductSearch) -> tuple[list[Product], int]:
    tokens = list(spec.tokens)
    color = spec.color
    min_price = spec.min_price
    max_price = spec.max_price
    if spec.query:
        parsed_tokens, inferred = analyze_query(spec.query)
        tokens = tokens or parsed_tokens
        color = color or inferred.get("color")
        if min_price is None:
            min_price = inferred.get("min_price")
        if max_price is None:
            max_price = inferred.get("max_price")

    stmt = select(Product).join(Category)
    if not spec.include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    if spec.category:
        stmt = stmt.where(Category.slug == spec.category)
    if spec.brand:
        stmt = stmt.where(func.lower(Product.brand) == spec.brand.lower())
    if min_price is not None:
        stmt = stmt.where(Product.price >= min_price)
    if max_price is not None:
        stmt = stmt.where(Product.price <= max_price)
    if spec.featured:
        stmt = stmt.where(Product.is_featured.is_(True))
    if spec.is_new:
        stmt = stmt.where(Product.is_new.is_(True))
    if spec.bestseller:
        stmt = stmt.where(Product.is_bestseller.is_(True))
    if spec.trending:
        stmt = stmt.where(Product.is_trending.is_(True))
    if spec.ids is not None:
        if not spec.ids:
            return [], 0
        stmt = stmt.where(Product.id.in_(spec.ids))

    for token in tokens:
        like = f"%{token}%"
        color_match = exists(
            select(ProductVariant.id).where(
                ProductVariant.product_id == Product.id,
                ProductVariant.is_active.is_(True),
                func.lower(ProductVariant.color).like(like),
            )
        )
        stmt = stmt.where(
            or_(
                Product.name.ilike(like),
                Product.description.ilike(like),
                Product.brand.ilike(like),
                Product.material.ilike(like),
                Category.name.ilike(like),
                color_match,
            )
        )

    variant_filters = []
    if spec.size:
        variant_filters.append(func.lower(ProductVariant.size) == spec.size.lower())
    if color:
        variant_filters.append(func.lower(ProductVariant.color) == color.lower())
    if spec.in_stock:
        variant_filters.append(Inventory.quantity > 0)
    if variant_filters:
        variant_stmt = select(ProductVariant.id).where(
            ProductVariant.product_id == Product.id,
            ProductVariant.is_active.is_(True),
            *variant_filters,
        )
        if spec.in_stock:
            variant_stmt = variant_stmt.join(Inventory)
        stmt = stmt.where(exists(variant_stmt))

    count = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    if spec.sort == "price_asc":
        stmt = stmt.order_by(Product.price.asc(), Product.name.asc())
    elif spec.sort == "price_desc":
        stmt = stmt.order_by(Product.price.desc(), Product.name.asc())
    elif spec.sort == "popularity":
        stmt = stmt.order_by(Product.popularity.desc(), Product.created_at.desc())
    else:
        stmt = stmt.order_by(Product.created_at.desc())

    page = max(spec.page, 1)
    page_size = min(max(spec.page_size, 1), 48)
    stmt = _load_options(stmt.offset((page - 1) * page_size).limit(page_size))
    return list(db.scalars(stmt).unique().all()), int(count)


def get_product_by_slug(db: Session, slug: str, include_inactive: bool = False) -> Product | None:
    stmt = _load_options(select(Product).where(Product.slug == slug))
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    return db.scalar(stmt)


def get_product(db: Session, product_id: uuid.UUID, include_inactive: bool = False) -> Product | None:
    stmt = _load_options(select(Product).where(Product.id == product_id))
    if not include_inactive:
        stmt = stmt.where(Product.is_active.is_(True))
    return db.scalar(stmt)


def get_products_by_ids(db: Session, ids: list[uuid.UUID]) -> list[Product]:
    if not ids:
        return []
    products, _ = search_products(
        db, ProductSearch(ids=ids, page_size=len(ids), include_inactive=False)
    )
    order = {product_id: index for index, product_id in enumerate(ids)}
    return sorted(products, key=lambda product: order.get(product.id, 999))
